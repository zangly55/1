"""Stage1 有限状态机（FSM）：用可审计的时间元数据承担"在场计时"。

论文 3.2 节的六个状态在本模块一一对应：

    State0 OUTSIDE            区外常态（本实现按需创建，创建时即进入 ENTERING）
    State1 ENTERING           进入防抖：连续 K 帧位于 ROI 才确认进入；
                              t_enter 取**首帧越界的原始时刻**，防抖等待计入在场时长
    State2 STAYING            在场累加：仍可见且位于区内；或中断未超过 L 帧且卡尔曼预测框仍在 ROI
    State3 TRIGGERED          候选触发：累计在场 >= T_threshold，发出候选信号并抽取历史片段
    State4 EXITED             正常离开：连续 N_exit 帧稳定移出 ROI，归档并复位
    State5 MISSING            长时间失踪挂起：冻结已确认时长、记 t_lost、开 T_hit 观察窗；
                             重现且完成身份关联后按策略扣除失踪间隔

关键工程取舍：
  1. 观测失败（丢帧/解码失败）绝不等同于"离开"，也绝不等同于"事件不存在"。
  2. 累计在场时长按物理时长逐帧累加，天然支持"分母不连续"的流；
     三种植入策略（precise/strict/loose）在重现时刻一次性结清失踪间隔。
  3. 跨未知间隔累加无法证明"严格连续滞留"，因此候选会带上 continuity 元数据，
     由 Stage3 在卡片里把结论降级为"累计在场（含 X 秒观测中断）"。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .geometry import Point, point_distance
from .tracker import cosine_similarity
from .types import FsmArchive, FsmEvent, Roi, TrackObs
from .util import clamp, get_logger

LOG = get_logger("cvalarm.fsm")

# 状态常量
OUTSIDE = "OUTSIDE"
ENTERING = "ENTERING"
STAYING = "STAYING"
TRIGGERED = "TRIGGERED"
MISSING = "MISSING"
EXITED = "EXITED"
LOST = "LOST"

ACTIVE_STATES = (STAYING, TRIGGERED)
TERMINAL_STATES = (EXITED, LOST)


@dataclass
class FsmConfig:
    debounce_frames: int = 5
    occlusion_tolerance_frames: int = 12
    dwell_threshold_s: float = 45.0
    exit_frames: int = 6
    missing_window_s: float = 120.0
    reid_policy: str = "precise"
    reid_sim_threshold: float = 0.6
    max_speed_norm_per_s: float = 0.35
    reid_max_speed_slack: float = 0.12
    history_window_s: float = 60.0
    out_of_roi_policy: str = "pause"   # pause：观测在区外时暂停累计；accumulate：继续累计
    anchor_mode: str = "bottom_center"

    @classmethod
    def from_config(cls, cfg: dict, anchor_mode: str = "bottom_center") -> "FsmConfig":
        return cls(
            debounce_frames=int(cfg.get("debounce_frames", 5)),
            occlusion_tolerance_frames=int(cfg.get("occlusion_tolerance_frames", 12)),
            dwell_threshold_s=float(cfg.get("dwell_threshold_s", 45.0)),
            exit_frames=int(cfg.get("exit_frames", 6)),
            missing_window_s=float(cfg.get("missing_window_s", 120.0)),
            reid_policy=str(cfg.get("reid_policy", "precise")),
            reid_sim_threshold=float(cfg.get("reid_sim_threshold", 0.6)),
            max_speed_norm_per_s=float(cfg.get("max_speed_norm_per_s", 0.35)),
            reid_max_speed_slack=float(cfg.get("reid_max_speed_slack", 0.12)),
            history_window_s=float(cfg.get("history_window_s", 60.0)),
            out_of_roi_policy=str(cfg.get("out_of_roi_policy", "pause")),
            anchor_mode=anchor_mode,
        )


class DwellFSM:
    """单条轨迹 × 单个 ROI 的在场面状态机。"""

    def __init__(self, camera_id: str, roi: Roi, track_id: int, cfg: FsmConfig,
                 event_class: Optional[str] = None, generation: int = 1) -> None:
        self.camera_id = camera_id
        self.roi = roi
        self.track_id = track_id
        self.cfg = cfg
        self.event_class = event_class or roi.event_class
        self.generation = generation

        self.state = OUTSIDE
        self.accum = 0.0                 # 已确认累计在场时长（秒）
        self.t_enter: Optional[float] = None
        self._first_inside_ts: Optional[float] = None
        self._last_count_ts: Optional[float] = None
        self.in_streak = 0
        self.out_streak = 0
        self.miss_count = 0
        self.sys_error_frames = 0
        self.bad_quality_frames = 0

        # 悬挂 (State5)
        self.t_lost: Optional[float] = None
        self.window_end: Optional[float] = None
        self.frozen_accum = 0.0

        # 候选
        self.emitted = False
        self.trigger_ts: Optional[float] = None
        self.trigger_accum: Optional[float] = None

        # 轨迹快照
        self.last_seen_ts: Optional[float] = None
        self.last_anchor: Optional[Point] = None
        self.last_bbox: Optional[tuple] = None
        self.history: list[tuple[float, Point]] = []
        # 逐帧包围框历史：证据回放的关键帧重绘需要它（锚点不足以画出目标）
        self.history_boxes: list[tuple[float, tuple]] = []
        self.score_ema: Optional[float] = None
        self.appearance: Optional[list[float]] = None
        self.ever_suspended = False
        self.gaps: list[dict] = []
        self.terminal = False
        self.archive: Optional[FsmArchive] = None
        self.entered_ts: Optional[float] = None
        self.obs_count = 0

    # ------------------------------------------------------------------ 属性
    @property
    def active(self) -> bool:
        return self.state in ACTIVE_STATES

    def accum_now(self, ts: float) -> float:
        """当前累计在场时长：active 时把本帧已在内的时长算上。"""
        return self.accum

    def _advance(self, ts: float) -> None:
        """按物理时长累加在场时间（仅在判定"仍在场"的帧调用）。"""
        if self._last_count_ts is None:
            self._last_count_ts = ts
            return
        dt = ts - self._last_count_ts
        if dt > 0:
            self.accum += dt
        self._last_count_ts = ts

    # ------------------------------------------------------------------ 主入口
    def update(self, obs: TrackObs) -> list[FsmEvent]:
        if self.terminal:
            return []
        self.obs_count += 1
        evs: list[FsmEvent] = []

        if self.state == OUTSIDE:
            if obs.seen and obs.frame_ok and self.roi.contains(obs.anchor):
                self._remember(obs)
                self.state = ENTERING
                self.in_streak = 1
                self._first_inside_ts = obs.ts
            return evs

        if self.state == ENTERING:
            return self._step_entering(obs, evs)

        if self.state in ACTIVE_STATES:
            return self._step_active(obs, evs)

        if self.state == MISSING:
            return self._step_missing(obs, evs)

        return evs
    # ------------------------------------------------------------------ State1
    def _step_entering(self, obs: TrackObs, evs: list[FsmEvent]) -> list[FsmEvent]:
        if not obs.frame_ok:
            self.sys_error_frames += 1
            return evs  # 观测失败既不算离开，也不推进防抖
        if obs.seen and self.roi.contains(obs.anchor):
            self._remember(obs)
            self.in_streak += 1
            if self.in_streak >= self.cfg.debounce_frames:
                assert self._first_inside_ts is not None
                self.t_enter = self._first_inside_ts
                self.entered_ts = obs.ts
                self.state = STAYING
                # 防抖等待计入在场时长（论文 3.2 节明确要求）
                self.accum = max(0.0, obs.ts - self.t_enter)
                self._last_count_ts = obs.ts
                evs.append(self._event("entered", obs.ts, {
                    "t_enter": self.t_enter,
                    "debounce_frames": self.in_streak,
                    "debounce_wait_s": self.accum,
                }))
                evs.extend(self._maybe_trigger(obs))
            return evs
        if obs.seen:
            # 越界后立即离开：防抖失败，复位
            self.state = OUTSIDE
            self.in_streak = 0
            self._first_inside_ts = None
        return evs

    # ------------------------------------------------------------------ State2/3
    def _step_active(self, obs: TrackObs, evs: list[FsmEvent]) -> list[FsmEvent]:
        if not obs.frame_ok:
            self.sys_error_frames += 1
            return self._absent(obs, evs)
        if not obs.seen:
            return self._absent(obs, evs)

        self.miss_count = 0
        inside = self.roi.contains(obs.anchor)
        self._remember(obs)
        if inside:
            self.out_streak = 0
            self._advance(obs.ts)
            evs.extend(self._maybe_trigger(obs))
            return evs

        # 观测到目标在区外：连续 N_exit 帧才确认离开
        self.out_streak += 1
        if self.cfg.out_of_roi_policy == "accumulate":
            self._advance(obs.ts)
            evs.extend(self._maybe_trigger(obs))
        else:
            # 暂停累计：只推进计数基准，不增加在场时长
            if self._last_count_ts is not None:
                self._last_count_ts = obs.ts
        if self.out_streak >= self.cfg.exit_frames:
            self._finish("EXITED", obs.ts, {
                "out_streak": self.out_streak,
                "accum_s": round(self.accum, 3),
                "t_enter": self.t_enter,
            }, evs)
        return evs

    def _absent(self, obs: TrackObs, evs: list[FsmEvent]) -> list[FsmEvent]:
        """观测中断：先按卡尔曼预测判断是否仍可视为在场，超过 L 帧转悬挂。"""
        self.miss_count += 1
        self.out_streak = 0
        pred_in = self.roi.contains(obs.pred_anchor)
        tol = self.cfg.occlusion_tolerance_frames

        if self.miss_count <= tol:
            if pred_in:
                self._advance(obs.ts)  # 短时遮挡，预测仍在 ROI：连续累计
                evs.extend(self._maybe_trigger(obs))
            else:
                if self._last_count_ts is not None:
                    self._last_count_ts = obs.ts
            return evs

        # 超过容忍帧数 -> State5
        self.state = MISSING
        self.frozen_accum = self.accum
        self.t_lost = self.last_seen_ts if self.last_seen_ts is not None else obs.ts
        self.window_end = self.t_lost + self.cfg.missing_window_s
        self.ever_suspended = True
        self._last_count_ts = None
        evs.append(self._event("suspended", obs.ts, {
            "t_lost": self.t_lost,
            "frozen_accum_s": round(self.frozen_accum, 3),
            "window_s": self.cfg.missing_window_s,
            "pred_in_roi": pred_in,
            "reason": "occlusion" if obs.frame_ok else "observation_failure",
        }))
        return evs

    # ------------------------------------------------------------------ State5
    def _step_missing(self, obs: TrackObs, evs: list[FsmEvent]) -> list[FsmEvent]:
        window_end = self.window_end or obs.ts
        if not obs.frame_ok:
            if obs.ts > window_end:
                self._finish("LOST_WINDOW_EXPIRED", obs.ts, {
                    "t_lost": self.t_lost,
                    "frozen_accum_s": round(self.frozen_accum, 3),
                    "reason": "observation_failure_window_expired",
                }, evs)
            return evs

        if not obs.seen:
            if obs.ts > window_end:
                self._finish("LOST_WINDOW_EXPIRED", obs.ts, {
                    "t_lost": self.t_lost,
                    "frozen_accum_s": round(self.frozen_accum, 3),
                    "reason": "not_reappeared_within_window",
                }, evs)
            return evs

        if self.roi.contains(obs.anchor):
            # 身份关联必须使用"重现之前"的外观记录，因此这里不能在比较前 _remember
            reid_ok, sim, smooth = self._identity_ok(obs)
            if not reid_ok:
                self._finish("LOST_IDENTITY", obs.ts, {
                    "t_lost": self.t_lost,
                    "appearance_sim": round(sim, 3),
                    "motion_smooth": smooth,
                    "reason": "identity_not_associated",
                }, evs)
                return evs

            t_resume = obs.ts
            self._remember(obs)
            delta = max(0.0, t_resume - (self.t_lost or t_resume))
            policy = self.cfg.reid_policy
            if policy == "strict":
                self.accum = 0.0
            elif policy == "loose":
                self.accum = self.frozen_accum + delta
            else:  # precise：扣除失踪间隔，分段累计
                self.accum = self.frozen_accum
            self._last_count_ts = t_resume
            self.miss_count = 0
            self.out_streak = 0
            self.state = TRIGGERED if self.emitted else STAYING
            self.gaps.append({
                "t_lost": round(self.t_lost or 0.0, 3),
                "t_resume": round(t_resume, 3),
                "delta_s": round(delta, 3),
                "policy": policy,
                "appearance_sim": round(sim, 3),
                "motion_smooth": smooth,
            })
            evs.append(self._event("resumed", t_resume, {
                "t_lost": self.t_lost,
                "delta_missing_s": round(delta, 3),
                "policy": policy,
                "accum_s": round(self.accum, 3),
                "appearance_sim": round(sim, 3),
                "motion_smooth": smooth,
            }))
            self.t_lost = None
            self.window_end = None
            evs.extend(self._maybe_trigger(obs))
            return evs

        # 重现但已在区外：按稳定离开处理，否则继续悬挂等待
        self._remember(obs)
        self.out_streak += 1
        if self.out_streak >= self.cfg.exit_frames:
            self._finish("EXITED", obs.ts, {
                "t_lost": self.t_lost,
                "frozen_accum_s": round(self.frozen_accum, 3),
                "reason": "reappeared_outside_roi",
            }, evs)
        elif obs.ts > window_end:
            self._finish("LOST_WINDOW_EXPIRED", obs.ts, {
                "t_lost": self.t_lost,
                "frozen_accum_s": round(self.frozen_accum, 3),
                "reason": "outside_roi_window_expired",
            }, evs)
        return evs

    # ------------------------------------------------------------------ 触发/归档
    def _maybe_trigger(self, obs: TrackObs) -> list[FsmEvent]:
        if self.emitted or self.t_enter is None:
            return []
        if self.accum + 1e-9 < self.cfg.dwell_threshold_s:
            return []
        self.emitted = True
        self.state = TRIGGERED
        self.trigger_ts = obs.ts
        self.trigger_accum = self.accum
        if not self.history:
            self._remember(obs)
        payload = self.snapshot()
        return [self._event("candidate", obs.ts, payload)]

    def snapshot(self) -> dict:
        """轨迹状态快照：交给 Stage2/Stage3 的时空先验。"""
        speeds: list[float] = []
        for i in range(1, len(self.history)):
            t0, a0 = self.history[i - 1]
            t1, a1 = self.history[i]
            dt = t1 - t0
            if dt > 0:
                speeds.append(point_distance(a0, a1) / dt)
        motion_energy = sum(speeds) / len(speeds) if speeds else 0.0
        return {
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "roi_id": self.roi.roi_id,
            "event_class": self.event_class,
            "t_enter": round(self.t_enter, 3) if self.t_enter is not None else None,
            "t_trigger": round(self.trigger_ts, 3) if self.trigger_ts is not None else None,
            "accum_s": round(self.accum, 3),
            "dwell_threshold_s": self.cfg.dwell_threshold_s,
            "in_roi": True,
            "continuity": {
                "suspended": self.ever_suspended,
                "gaps": list(self.gaps),
                "policy": self.cfg.reid_policy,
                "continuous_verified": not self.ever_suspended,
            },
            "motion_energy": round(clamp(motion_energy, 0.0, 5.0), 4),
            "mean_det_score": round(self.score_ema or 0.0, 4),
            "sys_error_frames": self.sys_error_frames,
            "bad_quality_frames": self.bad_quality_frames,
            "frames_since_enter": round((self.trigger_ts or 0.0) - (self.t_enter or 0.0), 3),
            "last_bbox": list(self.last_bbox) if self.last_bbox else None,
            "last_anchor": list(self.last_anchor) if self.last_anchor else None,
            "history": [[round(t, 3), [round(p[0], 4), round(p[1], 4)]] for t, p in self.history],
            "history_boxes": [[round(t, 3), round(b[0], 4), round(b[1], 4),
                               round(b[2], 4), round(b[3], 4)] for t, b in self.history_boxes],
            "generation": self.generation,
        }

    def _finish(self, outcome: str, ts: float, detail: dict, evs: list[FsmEvent]) -> None:
        self.state = EXITED if outcome == "EXITED" else LOST
        self.terminal = True
        self.archive = FsmArchive(
            camera_id=self.camera_id,
            track_id=self.track_id,
            roi_id=self.roi.roi_id,
            outcome=outcome,
            ts=ts,
            accum_s=round(self.accum, 3),
            t_enter=self.t_enter or 0.0,
            detail=detail,
        )
        evs.append(self._event("exit" if outcome == "EXITED" else "lost", ts, {
            "outcome": outcome,
            "accum_s": round(self.accum, 3),
            "t_enter": self.t_enter,
            "detail": detail,
        }))

    # ------------------------------------------------------------------ 内部
    def _identity_ok(self, obs: TrackObs) -> tuple[bool, float, bool]:
        """身份关联：外观相似优先；无外观嵌入时退化为运动平滑性。

        工程取舍：仅凭运动平滑会让静止物体（如被误检的货叉）顶替悬挂中的人员，
        因此当两侧都有外观嵌入时，要求外观至少弱匹配。
        """
        sim = cosine_similarity(self.appearance, obs.appearance)
        appearance_ok = sim >= self.cfg.reid_sim_threshold
        dt = max(0.0, obs.ts - (self.t_lost or obs.ts))
        max_dist = self.cfg.max_speed_norm_per_s * dt + self.cfg.reid_max_speed_slack
        ref = self.last_anchor or obs.anchor
        dist = point_distance(ref, obs.anchor)
        smooth_ok = dist <= max_dist
        if self.appearance and obs.appearance:
            return (appearance_ok and (smooth_ok or sim >= 0.8)), sim, smooth_ok
        return (smooth_ok, sim, smooth_ok)

    def _remember(self, obs: TrackObs) -> None:
        self.last_seen_ts = obs.ts
        self.last_anchor = obs.anchor
        self.last_bbox = obs.bbox
        if obs.det_score > 0:
            self.score_ema = obs.det_score if self.score_ema is None \
                else 0.8 * self.score_ema + 0.2 * obs.det_score
        if obs.appearance:
            self.appearance = list(obs.appearance)
        self.history.append((obs.ts, obs.anchor))
        if len(self.history) > 600:
            del self.history[: len(self.history) - 600]
        self.history_boxes.append((obs.ts, tuple(obs.bbox)))
        if len(self.history_boxes) > 600:
            del self.history_boxes[: len(self.history_boxes) - 600]

    def _event(self, kind: str, ts: float, payload: dict) -> FsmEvent:
        return FsmEvent(
            kind=kind,
            camera_id=self.camera_id,
            track_id=self.track_id,
            roi_id=self.roi.roi_id,
            ts=ts,
            payload=payload,
        )

    # ------------------------------------------------------------------ 诊断
    def debug_state(self) -> dict:
        return {
            "state": self.state,
            "accum": round(self.accum, 3),
            "t_enter": self.t_enter,
            "miss_count": self.miss_count,
            "out_streak": self.out_streak,
            "in_streak": self.in_streak,
            "emitted": self.emitted,
            "suspended": self.ever_suspended,
        }
