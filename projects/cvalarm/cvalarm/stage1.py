"""Stage1 流式前筛：轻量检测输出 + 跟踪 + ROI + FSM + 历史缓冲。

设计要点（对应论文第 3 章）：
  * 前筛本身必须满足视频流吞吐，否则入口积压会先于后级减负出现；
    因此本模块每帧只做 O(轨迹数 × ROI 数) 的几何判定，不调用任何大模型。
  * 前筛遵循"高召回优先"：只输出**候选**，不做真假判定。
  * 非告警时段按配置抽样进入旁路重检（audit），用于估计前筛召回与选择偏差，
    避免"纯串联系统在前级丢失后再无机会找回事件"。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .config import Config
from .fsm import DwellFSM, FsmConfig
from .geometry import bbox_aspect, get_anchor
from .tracker import ByteTracker, cosine_similarity
from .types import (Candidate, CameraInfo, Frame, FrameFeature, FsmEvent, Roi, TrackObs)
from .util import Rng, clamp, get_logger

LOG = get_logger("cvalarm.stage1")


@dataclass
class AuditRequest:
    """非告警时段的旁路重检请求（用于前筛召回与漏检估计）。"""

    camera_id: str
    window: tuple[float, float]
    reason: str = "periodic_audit"


@dataclass
class Stage1Result:
    candidates: list[Candidate] = field(default_factory=list)
    audit_requests: list[AuditRequest] = field(default_factory=list)
    feature: Optional[FrameFeature] = None
    events: list[FsmEvent] = field(default_factory=list)
    archives: list[dict] = field(default_factory=list)


class FrameBuffer:
    """按时间回看的历史缓冲（Stage2 只允许读取已到达的帧）。"""

    def __init__(self, max_seconds: float = 600.0) -> None:
        self.max_seconds = float(max_seconds)
        self._items: list[FrameFeature] = []

    def push(self, feature: FrameFeature) -> None:
        self._items.append(feature)
        cutoff = feature.ts - self.max_seconds
        if cutoff > 0:
            idx = 0
            while idx < len(self._items) and self._items[idx].ts < cutoff:
                idx += 1
            if idx:
                del self._items[:idx]

    def window(self, t0: float, t1: float) -> list[FrameFeature]:
        return [f for f in self._items if t0 <= f.ts <= t1]

    def __len__(self) -> int:
        return len(self._items)

    @property
    def last_ts(self) -> float:
        return self._items[-1].ts if self._items else 0.0


class PrefilterEngine:
    """单路摄像头的 Stage1 引擎。"""

    def __init__(self, cfg: Config, camera: CameraInfo, rois: Iterable[Roi]) -> None:
        self.cfg = cfg
        self.camera = camera
        self.rois: dict[str, Roi] = {r.roi_id: r for r in rois}
        self.anchor_mode = str(cfg.get("runtime.anchor_mode", "bottom_center"))
        self.tracker = ByteTracker(cfg.tracker, anchor_mode=self.anchor_mode)
        self.fsm_cfg = FsmConfig.from_config(cfg.fsm, anchor_mode=self.anchor_mode)
        self.fsm_cfg.dwell_threshold_s = float(cfg.get("fsm.dwell_threshold_s"))
        # 每个 ROI 可以有自己的滞留阈值（不同区域适用不同规程）
        self._fsm_cfgs: dict[str, FsmConfig] = {}
        for roi_id, roi in self.rois.items():
            per = FsmConfig.from_config(cfg.fsm, anchor_mode=self.anchor_mode)
            per.dwell_threshold_s = float(roi.dwell_threshold_s or
                                          cfg.get("fsm.dwell_threshold_s", 45.0))
            self._fsm_cfgs[roi_id] = per
        self._fsms: dict[tuple[int, str], DwellFSM] = {}
        self._gens: dict[tuple[int, str], int] = {}
        self.buffer = FrameBuffer(max_seconds=float(cfg.get("fsm.history_window_s", 60)) * 3.0)
        self._prev_anchors: dict[int, tuple[float, tuple[float, float]]] = {}
        self._candidate_seq = 0

        # 统计
        self.frames = 0
        self.dropped_frames = 0
        self.candidates = 0
        self.candidate_video_s = 0.0
        self.gpu_ms = 0.0
        self.roi_occupied_frames = 0

        # 旁路重检抽样
        self._rng = Rng(int(cfg.get("runtime.seed", 7))).stream(f"audit:{camera.camera_id}")
        self._audit_per_hour = float(cfg.get("feedback.audit_windows_per_camera_hour", 2.0))
        self._audit_window_s = float(cfg.get("feedback.audit_window_s", 30.0))
        self._next_audit_ts = self._sample_next_audit(0.0)

    # ------------------------------------------------------------------ 主入口
    def process(self, frame: Frame) -> Stage1Result:
        self.frames += 1
        if not frame.ok:
            self.dropped_frames += 1
        stage1_ms = float(self.cfg.get("cost.stage.stage1_gpu_ms_per_frame", 12.0))
        self.gpu_ms += stage1_ms

        update = self.tracker.step(frame)
        obs_map = {o.track_id: o for o in update.obs}
        feature = self._frame_feature(frame, obs_map)
        self.buffer.push(feature)

        events: list[FsmEvent] = []
        result = Stage1Result(feature=feature)

        # 已有 FSM 逐帧推进（含跟踪器已移除轨迹的"僵尸观测"）
        for key, fsm in list(self._fsms.items()):
            track_id, roi_id = key
            obs = obs_map.get(track_id)
            if obs is None:
                obs = self._zombie_obs(frame, fsm)
            if obs is None:
                continue
            evs = fsm.update(obs)
            for ev in evs:
                events.append(ev)
                if ev.kind == "candidate":
                    cand = self._make_candidate(frame, fsm, ev)
                    result.candidates.append(cand)
                    self.candidates += 1
                    self.candidate_video_s += max(0.0, cand.window[1] - cand.window[0])
                elif ev.kind in ("exit", "lost") and fsm.archive is not None:
                    result.archives.append(fsm.archive.to_dict())
            if fsm.terminal:
                if key in self._gens:
                    self._gens[key] = self._gens[key] + 1
                else:
                    self._gens[key] = 2
                del self._fsms[key]

        # 新进入 ROI 的轨迹：优先与"悬挂中的状态机"重绑，否则新建
        for obs in update.obs:
            if not obs.seen or not obs.frame_ok:
                continue
            for roi in self.rois.values():
                key = (obs.track_id, roi.roi_id)
                if key in self._fsms:
                    continue
                if not roi.contains(obs.anchor):
                    continue
                rebound = self._try_rebind(obs, roi)
                if rebound is not None:
                    fsm, old_track_id, sim = rebound
                    events.append(FsmEvent(
                        kind="rebound", camera_id=self.camera.camera_id,
                        track_id=obs.track_id, roi_id=roi.roi_id, ts=obs.ts,
                        payload={"from_track": old_track_id,
                                 "appearance_sim": round(sim, 4)}))
                else:
                    gen = self._gens.get(key, 1)
                    fsm = DwellFSM(self.camera.camera_id, roi, obs.track_id,
                                   self._fsm_cfgs.get(roi.roi_id, self.fsm_cfg),
                                   event_class=roi.event_class, generation=gen)
                    self._fsms[key] = fsm
                evs = fsm.update(obs)
                for ev in evs:
                    events.append(ev)
                    if ev.kind == "candidate":
                        cand = self._make_candidate(frame, fsm, ev)
                        result.candidates.append(cand)
                        self.candidates += 1
                        self.candidate_video_s += max(0.0, cand.window[1] - cand.window[0])
                    elif ev.kind in ("exit", "lost") and fsm.archive is not None:
                        result.archives.append(fsm.archive.to_dict())
                if fsm.terminal and key in self._fsms:
                    del self._fsms[key]

        result.events = events

        # 旁路重检抽样：仅在没有活跃 FSM 的"疑似无事件"时段抽样
        if frame.ts >= self._next_audit_ts and not self._fsms:
            t1 = frame.ts
            t0 = max(0.0, t1 - self._audit_window_s)
            result.audit_requests.append(AuditRequest(self.camera.camera_id, (t0, t1)))
            self._next_audit_ts = self._sample_next_audit(t1)

        if feature.roi_persons:
            self.roi_occupied_frames += 1
        return result

    # ------------------------------------------------------------------ 内部
    def _sample_next_audit(self, now: float) -> float:
        if self._audit_per_hour <= 0:
            return math.inf
        mean_gap = 3600.0 / self._audit_per_hour
        return now + max(self._audit_window_s, self._rng.expovariate(1.0 / mean_gap))

    def _try_rebind(self, obs: TrackObs, roi: Roi):
        """把重新出现的目标与悬挂（State5）中的状态机做身份重绑。

        论文 3.2 节要求"重现时通过外观特征（ReID）或运动平滑性完成身份关联"。
        真实系统里长时遮挡会让跟踪器丢掉原轨迹并分配新 ID，因此身份关联
        必须发生在轨迹层之上，否则跨遮挡的累计在场时长会被错误清零。
        """
        if obs.track_hits < 2:
            return None
        best = None
        best_sim = -1.0
        threshold = float(self.fsm_cfg.reid_sim_threshold)
        for key, fsm in list(self._fsms.items()):
            if fsm.state != "MISSING" or fsm.roi.roi_id != roi.roi_id:
                continue
            if fsm.track_id == obs.track_id:
                continue
            sim = cosine_similarity(fsm.appearance, obs.appearance)
            if fsm.appearance and obs.appearance and sim < threshold:
                continue
            if sim > best_sim:
                best = fsm
                best_sim = sim
        if best is None:
            return None
        old_track_id = best.track_id
        self._fsms.pop((old_track_id, roi.roi_id), None)
        best.track_id = obs.track_id
        self._fsms[(obs.track_id, roi.roi_id)] = best
        return (best, old_track_id, max(0.0, best_sim))

    def _zombie_obs(self, frame: Frame, fsm: DwellFSM) -> Optional[TrackObs]:
        anchor = fsm.last_anchor
        bbox = fsm.last_bbox
        if anchor is None or bbox is None:
            return None
        return TrackObs(
            camera_id=frame.camera_id,
            track_id=fsm.track_id,
            frame_idx=frame.frame_idx,
            ts=frame.ts,
            seen=False,
            anchor=anchor,
            bbox=bbox,
            pred_anchor=anchor,
            pred_bbox=bbox,
            det_score=0.0,
            appearance=fsm.appearance,
            frame_ok=frame.ok,
        )

    def _make_candidate(self, frame: Frame, fsm: DwellFSM, ev: FsmEvent) -> Candidate:
        snapshot = ev.payload
        hist = float(self.cfg.get("fsm.history_window_s", 60.0))
        t0 = max(0.0, ev.ts - hist)
        flags: list[str] = []
        if snapshot.get("sys_error_frames", 0) > 0:
            flags.append("observation_failure")
        if snapshot.get("continuity", {}).get("suspended"):
            flags.append("occlusion_gap")
        window_feats = self.buffer.window(t0, ev.ts)
        if window_feats:
            snr_vals = [f.snr for f in window_feats if f.ok]
            mean_snr = sum(snr_vals) / len(snr_vals) if snr_vals else 0.0
            if mean_snr < float(self.cfg.get("stage2.validity.min_snr", 12.0)):
                flags.append("low_snr")
            dropped = sum(1 for f in window_feats if not f.ok)
            if dropped / max(1, len(window_feats)) > float(
                    self.cfg.get("stage2.validity.max_dropped_ratio", 0.15)):
                flags.append("dropped_frames")
        self._candidate_seq += 1
        candid = Candidate(
            candidate_id=f"{self.camera.camera_id}-C{self._candidate_seq:05d}",
            camera_id=self.camera.camera_id,
            track_id=fsm.track_id,
            roi_id=fsm.roi.roi_id,
            event_class=fsm.event_class,
            t_enter=float(fsm.t_enter or ev.ts),
            t_trigger=ev.ts,
            accum_s=float(snapshot.get("accum_s", fsm.accum)),
            dwell_threshold_s=float(fsm.cfg.dwell_threshold_s),
            continuity=snapshot.get("continuity", {}),
            snapshot=snapshot,
            window=(t0, ev.ts),
            flags=flags,
        )
        return candid

    def _frame_feature(self, frame: Frame, obs_map: dict[int, TrackObs]) -> FrameFeature:
        persons = [d for d in frame.detections if d.cls == "person"]
        roi_persons: dict[str, float] = {}
        for roi in self.rois.values():
            roi_persons[roi.roi_id] = float(sum(
                1 for d in persons if roi.contains(get_anchor(d.bbox, self.anchor_mode))))
        # 帧级异常分只看"落在防区内的目标"：区外正常行人不应抬高异常分，
        # 否则帧级 ROC-AUC 会被大量区外活动抬高而失去诊断意义（形态一致性同理）。
        roi_persons_list = [d for d in persons
                            if any(roi.contains(get_anchor(d.bbox, self.anchor_mode))
                                   for roi in self.rois.values())]
        roi_scores = [d.score for d in roi_persons_list]
        motions: list[float] = []
        for obs in obs_map.values():
            if not obs.seen:
                continue
            prev = self._prev_anchors.get(obs.track_id)
            if prev is not None:
                dt = obs.ts - prev[0]
                if dt > 0:
                    dx = obs.anchor[0] - prev[1][0]
                    dy = obs.anchor[1] - prev[1][1]
                    motions.append(((dx * dx + dy * dy) ** 0.5) / dt)
            self._prev_anchors[obs.track_id] = (obs.ts, obs.anchor)
        return FrameFeature(
            camera_id=frame.camera_id,
            ts=frame.ts,
            ok=frame.ok,
            frame_idx=frame.frame_idx,
            max_score=max(roi_scores, default=0.0),
            person_count=float(len(persons)),
            roi_persons=roi_persons,
            motion=clamp(sum(motions) / len(motions) if motions else 0.0, 0.0, 5.0),
            snr=frame.snr,
            drop_ratio=0.0 if frame.ok else 1.0,
            mean_person_aspect=(
                sum(bbox_aspect(d.bbox) for d in roi_persons_list) / len(roi_persons_list)
                if roi_persons_list else 0.0
            ),
        )

    # ------------------------------------------------------------------ 状态
    def active_state_machines(self) -> int:
        return len(self._fsms)

    def stats(self) -> dict:
        return {
            "camera_id": self.camera.camera_id,
            "frames": self.frames,
            "dropped_frames": self.dropped_frames,
            "candidates": self.candidates,
            "candidate_video_s": round(self.candidate_video_s, 3),
            "gpu_ms": round(self.gpu_ms, 3),
            "roi_occupied_frames": self.roi_occupied_frames,
            "active_fsms": len(self._fsms),
        }
