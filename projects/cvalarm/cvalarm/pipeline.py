"""四阶段流水线编排：因果、可审计、可复现。

    FrameSource → Stage1(前筛/跟踪/FSM) → Stage2(定位/拒识) → Stage3(核验/卡片)
                ↘ 旁路抽样审计 ↗                                   ↘ Stage4(反馈/规则) ↗

工程约束（贯穿整个编排）：
  * 因果性：任何阶段只读取 ts <= 当前的观测；候选窗口一律向左取历史，
    不等待"片段闭合"——等待闭合本身就是论文指出的离线接口迁移代价。
  * 观测失败与事件不存在严格区分：丢帧/解码失败进入 system_error 与重检队列，
    不计入"正常"，也不冒充"告警"。
  * 一次运行内所有计量（GPU 秒、Token、候选时长、人工分钟）都是实测累计值，
    直接喂给成本模型，不使用预设比例。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from . import __version__
from .card import sign_card
from .config import Config
from .cost import PipelineStats, compute, estimate_egress_bytes
from .locator import EVENT, INSUFFICIENT, NO_EVENT, SYSTEM_ERROR, Localizer, load_calibration
from .metrics import evaluate, no_event_rejection
from .reliability import conditional_recall
from .rules import RuleEngine, RuleRegistry, RuleSet
from .stage1 import PrefilterEngine
from .types import (AlarmRecord, Candidate, Frame, FrameFeature, GtEvent, Roi, Stage2Result)
from .util import (Rng, content_hash, ensure_dir, get_logger, jitter, now_iso,
                   round_floats, write_json, write_jsonl)
from .verifier import AuthorizationBook, VerifierEngine

LOG = get_logger("cvalarm.pipeline")

#: 首版范围与暂缓项（对应工程方向里"首版做成什么"和"暂缓什么"）
CAPABILITIES: dict = {
    "single_camera_pipeline": {"status": "implemented", "note": "首版范围：单镜头完整链路"},
    "two_event_classes": {"status": "implemented",
                         "note": "人员进入指定区域 / 区域内停留超时（v1 场景）"},
    "evidence_replay": {"status": "implemented",
                        "note": "卡片附片段、前后文、关键帧示意图；配媒体后可按 Range 回放"},
    "no_event_branch": {"status": "implemented",
                        "note": "无事件/证据不足/采集中断三向分流，不把没看见写成没发生"},
    "human_review_loop": {"status": "implemented",
                          "note": "确认/驳回/暂不判断 + 理由码 + 抽样审计"},
    "rule_regression_gate": {"status": "implemented",
                             "note": "静态校验 + 回归门禁 + 原子发布/回滚"},
    "multi_camera": {"status": "supported_but_out_of_v1_scope",
                     "note": "演示场景含 2 机位；首版按单机位组织"},
    "multi_agent": {"status": "implemented_but_deferred_in_v1",
                    "note": "四类交互架构已实现，首版默认单模型基线 + 规则对照"},
    "live_stream_ingest": {"status": "deferred",
                           "note": "当前为离线回放验证，不冒充生产实时接流"},
    "automatic_rule_evolution": {"status": "deferred",
                                 "note": "规则候选由人工审核发布，不做自动演化"},
}


@dataclass
class RunResult:
    run_dir: str = ""
    meta: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    cost: dict = field(default_factory=dict)
    reliability: dict = field(default_factory=dict)
    audit: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    alarms: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    frame_histogram: dict = field(default_factory=dict)
    audit_samples: list[dict] = field(default_factory=list)
    wall_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "run_dir": self.run_dir,
            "meta": self.meta,
            "metrics": self.metrics,
            "cost": self.cost,
            "reliability": self.reliability,
            "audit": self.audit,
            "stats": self.stats,
            "alarms": self.alarms,
            "events": self.events,
            "frame_histogram": self.frame_histogram,
            "wall_seconds": round(self.wall_seconds, 3),
        }


class Pipeline:
    def __init__(self, cfg: Config, source: Any, ruleset: Optional[RuleSet] = None,
                 verifier: Optional[VerifierEngine] = None,
                 localizer: Optional[Localizer] = None,
                 persist: bool = True, out_dir: Optional[str] = None,
                 state_dir: Optional[str] = None) -> None:
        self.cfg = cfg
        self.run_id = uuid.uuid4().hex
        self.started_at = now_iso()
        cfg.validate()
        self.source = source
        from .reproducibility import calibration_context
        cfg.set("runtime.calibration_context", calibration_context(cfg, source))
        self.persist = persist
        self.out_dir = out_dir or cfg.resolve(str(cfg.get("runtime.out_dir", "runs/demo")))
        self.state_dir = state_dir or cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
        self.ruleset = ruleset or RuleRegistry(cfg, self.state_dir).active()
        self.rule_engine = RuleEngine(self.ruleset)
        auth_path = cfg.resolve(str(cfg.get("stage3.authorization_file", "")))
        self.auth = AuthorizationBook.load(auth_path)
        if self.auth.data_kind == "synthetic-demo-only" and self._source_kind() not in ("synthetic", "test"):
            self.auth.available = False
            self.auth.complete = False
            self.auth.error = "演示授权记录不能用于真实回放"
        self.localizer = localizer or Localizer(cfg, calibration=load_calibration(cfg))

        self.engines: dict[str, PrefilterEngine] = {}
        self.rois: dict[str, list[Roi]] = {}
        for roi in getattr(source, "rois", []):
            self.rois.setdefault(roi.camera_id, []).append(roi)
        if not self.rois:
            raise ValueError(
                "数据源没有任何 ROI 定义：请配置摄像头与多边形防区（config/cameras*.json）")
        # 证据回放需要 ROI 多边形（卡片里重绘示意图）
        self.scene: dict[str, list[dict]] = {
            cam: [r.to_dict() for r in rois] for cam, rois in self.rois.items()}
        self.provenance = {
            "run_id": self.run_id,
            "pipeline": f"cvalarm/{__version__}",
            "data_source": self._source_kind(),
            "replay_mode": "offline_replay",
            "claim": "离线回放验证结果，不是现场实时接流指标",
        }
        self.verifier = verifier or VerifierEngine(
            cfg, self.rule_engine, self.auth, scene=self.scene,
            provenance=self.provenance)

        self.alarms: list[AlarmRecord] = []
        self.candidates: list[Candidate] = []
        self.stage2_results: dict[str, Stage2Result] = {}
        self.fsm_audit: list[dict] = []
        self.audit_samples: list[dict] = []
        self.frame_scores: list[tuple[int, float]] = []
        self.camera_hours: dict[str, float] = {}
        self.negative_scores: list[float] = []
        self._alarm_seq = 0
        self._rng = Rng(int(cfg.get("runtime.seed", 7))).stream("latency")
        self._camera_last_ts: dict[str, float] = {}
        self._observation_intervals: dict[str, list[list[float]]] = {}
        self._audit_skipped = 0
        self.protocol = cfg.get("protocol", {}) or {}
        self._holdout = str(self.protocol.get("mode", "none")) == "holdout"

    def _source_kind(self) -> str:
        try:
            return str((self.source.describe() or {}).get("kind", "unknown"))
        except Exception:
            return "unknown"

    # ------------------------------------------------------------------ 隔离协议
    def _split_ranges(self, split: str) -> list[tuple[float, float]]:
        block = self.protocol.get(split, {}) or {}
        return [(float(r[0]), float(r[1])) for r in block.get("time_ranges", [])]

    def _in_split(self, camera_id: str, ts: float, split: str,
                  strict_end: bool = False) -> bool:
        """判断某机位某时刻是否属于 dev/test 段。未启用 holdout 时恒为真。"""
        if not self._holdout:
            return True
        block = self.protocol.get(split, {}) or {}
        cameras = block.get("cameras", [])
        if cameras and camera_id not in cameras:
            return False
        ranges = self._split_ranges(split)
        if not ranges:
            return True
        for r0, r1 in ranges:
            if r0 <= ts < r1:
                return True
        return False

    def _event_in_test(self, ev: GtEvent) -> bool:
        if not self._in_split(ev.camera_id, ev.start, "test"):
            return False
        ranges = self._split_ranges("test")
        if not ranges:
            return True
        return any(r0 <= ev.start and ev.end <= r1 for r0, r1 in ranges)

    def _apply_protocol(self, events: list[GtEvent], alarms: list[AlarmRecord],
                        camera_hours: dict[str, float]) -> tuple[list, list, dict, dict]:
        info = {
            "mode": str(self.protocol.get("mode", "none")),
            "dev": self.protocol.get("dev", {}),
            "test": self.protocol.get("test", {}),
            "audit_windows_skipped": self._audit_skipped,
            "note": str(self.protocol.get("note", "")),
        }
        if not self._holdout:
            info["applied"] = False
            return events, alarms, camera_hours, info
        test_events = [e for e in events if self._event_in_test(e)]
        test_alarms = [a for a in alarms if self._in_split(a.camera_id, a.t_trigger, "test")]
        # 分母只按测试段有效时长累加
        test_hours: dict[str, float] = {}
        for cam, stream_hours in camera_hours.items():
            block = self.protocol.get("test", {}) or {}
            cameras = block.get("cameras", [])
            if cameras and cam not in cameras:
                test_hours[cam] = 0.0
                continue
            ranges = self._split_ranges("test")
            observed = self._observation_intervals.get(cam, [])
            total = sum(max(0.0, min(b, r1) - max(a, r0))
                        for a,b in observed for r0,r1 in ranges) if ranges else sum(b-a for a,b in observed)
            test_hours[cam] = total / 3600.0
        test_hours = {k: v for k, v in test_hours.items() if v > 0}
        info["applied"] = True
        info["events_total"] = len(events)
        info["events_in_test"] = len(test_events)
        info["alarms_total"] = len(alarms)
        info["alarms_in_test"] = len(test_alarms)
        return test_events, test_alarms, test_hours, info

    # ------------------------------------------------------------------ 主流程
    def run(self) -> RunResult:
        t_start = time.perf_counter()
        ensure_dir(self.out_dir) if self.persist else None
        frames = 0
        next_frame_start = time.perf_counter()
        for frame in self.source.iter_frames():
            self._frame_started = next_frame_start
            frames += 1
            camera_id = frame.camera_id
            engine = self.engines.get(camera_id)
            if engine is None:
                engine = self._new_engine(camera_id)
            result = engine.process(frame)
            self._camera_last_ts[camera_id] = frame.ts
            info = next((c for c in getattr(self.source, "cameras", []) if c.camera_id == camera_id), None)
            step = 1.0 / max(0.001, float(getattr(info, "fps", 2.0)))
            if frame.ok:
                spans = self._observation_intervals.setdefault(camera_id, [])
                if spans and frame.ts <= spans[-1][1] + 1e-6:
                    spans[-1][1] = max(spans[-1][1], frame.ts + step)
                else:
                    spans.append([frame.ts, frame.ts + step])
            feature = result.feature
            if (feature is not None and frame.gt_label is not None
                    and self._in_split(camera_id, frame.ts, "test")):
                self.frame_scores.append((int(frame.gt_label), float(feature.max_score)))
            for req in result.audit_requests:
                self._handle_audit(camera_id, req.window, feature)
            for cand in result.candidates:
                self._handle_candidate(cand, frame)
            if result.archives or result.events:
                for item in result.archives:
                    self.fsm_audit.append(item)
                for ev in result.events:
                    if ev.kind in ("entered", "candidate", "suspended", "resumed",
                                   "rebound", "exit", "lost"):
                        self.fsm_audit.append({
                            "kind": ev.kind, "camera_id": ev.camera_id,
                            "track_id": ev.track_id, "roi_id": ev.roi_id,
                            "ts": round(ev.ts, 3), "payload": ev.payload,
                        })
            next_frame_start = time.perf_counter()
        wall = time.perf_counter() - t_start

        # 相机有效观测小时（逐路累加；断流/末尾不足整小时的按实际计）
        for camera_id, last_ts in self._camera_last_ts.items():
            info = next((c for c in getattr(self.source, "cameras", [])
                         if c.camera_id == camera_id), None)
            hours = sum(b-a for a,b in self._observation_intervals.get(camera_id, [])) / 3600.0
            self.camera_hours[camera_id] = hours

        events: list[GtEvent] = list(getattr(self.source, "gt_events", []) or [])
        events_eval, alarms_eval, hours_eval, protocol_info = self._apply_protocol(
            events, self.alarms, self.camera_hours)
        metrics = evaluate(events_eval, alarms_eval, hours_eval,
                           self.frame_scores, self.cfg.metrics,
                           extra=self._decision_counts())
        metrics["ground_truth_available"] = bool(getattr(self.source, "ground_truth_available", True))
        if not metrics["ground_truth_available"]:
            for key in ("event_recall", "event_recall_incl_deferred", "event_tp_confirmed",
                        "event_tp_displayed", "event_missed", "precision", "false_alarms",
                        "false_alarms_raw", "false_alarms_per_camera_hour"):
                metrics[key] = None
            for row in metrics["per_camera"]:
                for key in ("tp", "false_alarms", "fa_per_camera_hour"):
                    row[key] = None
            metrics["sample_size_warning"] = "未提供事件标注，事件召回与误报不可评价。"
        metrics["triage_counts"] = {key:sum(a.triage == key for a in alarms_eval)
                                    for key in (EVENT, NO_EVENT, INSUFFICIENT, SYSTEM_ERROR)}
        metrics["candidate_count"] = sum(self._in_split(c.camera_id,c.t_trigger,"test") for c in self.candidates)
        metrics["stage3_calls"] = sum(a.card is not None for a in alarms_eval)
        metrics["protocol"] = protocol_info
        metrics["no_event_rejection"] = no_event_rejection(
            [{"decision": s["decision"], "silent": s["decision"] == NO_EVENT}
             for s in self.audit_samples if s.get("event_in_window") is False])
        metrics["no_event_rejection"]["scope"] = "development_audit" if self._holdout else "labelled_audit"
        metrics["audit"] = {
            "samples": len(self.audit_samples),
            "sampling": self.cfg.get("feedback.audit_windows_per_camera_hour"),
            "windows": [s for s in self.audit_samples if s.get("decision") != EVENT][:200],
        }
        metrics["reliability"] = conditional_recall(
            events_eval, self.candidates, self.stage2_results, alarms_eval, self.cfg.metrics)
        metrics["difficult_cases"] = self._difficult_cases()
        metrics["difficult_cases"]["scope"] = "whole_run"
        metrics["provenance"] = self.provenance
        metrics["evaluable_video_hours"] = round(sum(hours_eval.values()), 4)
        stats = self._pipeline_stats(frames)
        cost = compute(stats, self.cfg.cost, cameras=len(self.camera_hours))
        cost["measurement_kind"] = "estimate"
        cost["scope"] = "whole_run"
        histogram = self._score_histogram()
        resources = self._resources(frames, wall)
        models = self._models()

        meta = self._meta(frames, wall)
        meta["resources"] = resources
        meta["models"] = models
        meta["protocol"] = protocol_info
        meta["capabilities"] = CAPABILITIES
        result = RunResult(
            run_dir=self.out_dir, meta=meta, metrics=metrics, cost=cost,
            reliability=metrics["reliability"], audit=metrics["audit"],
            stats=stats.to_dict(), alarms=[a.to_dict() for a in self.alarms],
            events=[e.to_dict() for e in events], frame_histogram=histogram,
            audit_samples=list(self.audit_samples),
            wall_seconds=wall,
        )
        if self.persist:
            self._persist(result)
        return result

    # ------------------------------------------------------------------ 引擎
    def _new_engine(self, camera_id: str) -> PrefilterEngine:
        info = next((c for c in getattr(self.source, "cameras", [])
                     if c.camera_id == camera_id), None)
        if info is None:
            from .types import CameraInfo

            info = CameraInfo(camera_id=camera_id)
        engine = PrefilterEngine(self.cfg, info, self.rois.get(camera_id, []))
        self.engines[camera_id] = engine
        return engine

    # ------------------------------------------------------------------ 候选
    def _handle_candidate(self, candidate: Candidate, frame: Frame) -> None:
        self.candidates.append(candidate)
        engine = self.engines[candidate.camera_id]
        features = engine.buffer.window(candidate.window[0], candidate.window[1])
        stage2 = self.localizer.run(candidate, features)
        self.stage2_results[candidate.candidate_id] = stage2
        self._alarm_seq += 1
        alarm_id = f"{self.run_id}-A{self._alarm_seq:05d}"
        # 条件成立时刻：触发帧的累计在场刚好越过阈值的那个物理时刻。
        # 直接写 t_enter + threshold 在"跨遮挡分段累计"的情形下会算早几十秒，
        # 把真实时延掩盖成"负时延"。
        overshoot = max(0.0, float(candidate.accum_s) - float(candidate.dwell_threshold_s))
        t_satisfy = candidate.t_trigger - overshoot

        card = None
        used_stage3 = stage2.decision in (EVENT, INSUFFICIENT)
        tokens = {"input": 0, "output": 0, "total": 0}
        action = ""
        if used_stage3:
            verification = self.verifier.verify(candidate, stage2, features)
            card = verification.card
            tokens = verification.tokens
            action = verification.action
            if stage2.decision != EVENT:
                # 证据不足时不得得出确证结论：一律降级为"存疑转人工"
                card["decision"] = "uncertain"
                norms = card.setdefault("Normative_Inference_Uncertainty", {})
                uncertainties = norms.setdefault("uncertainties", [])
                for reason in stage2.reasons:
                    if reason not in uncertainties:
                        uncertainties.append(reason)
                card["Normative_Inference_Uncertainty"] = norms
            card["alarm_id"] = alarm_id
            card["run_id"] = self.run_id
            card["rule_version"] = self.ruleset.version_label
            # 卡片在 Stage3 就地签名，之后编排层又改写了 alarm_id / decision / 未决事项，
            # 必须在这里重签，否则交付的签名对不上内容（且会掩盖真实篡改）。
            if card and bool(self.cfg.get("deployment.privacy.sign_cards", True)):
                card = sign_card(card)

        status, reason = self._status_of(stage2, card)
        latency = self._latency(used_stage3, tokens)
        if self._source_kind() not in ("synthetic", "test"):
            latency = {"total_ms":round((time.perf_counter()-self._frame_started)*1000, 3),
                       "measurement_kind":"measured_processing", "scope":"source_decode_to_card_ready",
                       "display_acknowledged":False, "window_close_wait_ms":0.0}
        t_display = candidate.t_trigger + latency["total_ms"] / 1000.0

        record = AlarmRecord(
            alarm_id=alarm_id,
            candidate_id=candidate.candidate_id,
            camera_id=candidate.camera_id,
            track_id=candidate.track_id,
            roi_id=candidate.roi_id,
            event_class=candidate.event_class,
            t_satisfy=round(t_satisfy, 3),
            t_trigger=round(candidate.t_trigger, 3),
            t_display=round(t_display, 3),
            status=status,
            triage=stage2.decision,
            interval=({"start": round(stage2.interval[0], 3),
                       "end": round(stage2.interval[1], 3)} if stage2.interval else None),
            card=card,
            latency=latency,
            suppression_reason=reason,
            rule_version=self.ruleset.version_label,
        )
        self.alarms.append(record)
        if not self.persist:
            return

    def _status_of(self, stage2: Stage2Result, card: Optional[dict]) -> tuple[str, str]:
        if stage2.decision == NO_EVENT:
            return ("suppressed", "无事件：证据分低于已标定的拒识阈值，静默抑制")
        if stage2.decision == SYSTEM_ERROR:
            return ("system_error", "；".join(stage2.reasons) or "采集或定位异常；不判定为正常")
        if stage2.decision == INSUFFICIENT:
            return ("deferred", "证据不足/未决，交人工复核")
        decision = (card or {}).get("decision", "uncertain")
        if decision == "confirm":
            return ("confirmed", "")
        if decision == "dismiss":
            norm = (card or {}).get("Normative_Inference_Uncertainty", {})
            return ("suppressed", f"规程适用性判定为非违规：{norm.get('basis', '')}")
        return ("deferred", "核验存疑，交人工复核")

    # ------------------------------------------------------------------ 旁路审计
    def _handle_audit(self, camera_id: str, window: tuple[float, float],
                      feature: Optional[FrameFeature]) -> None:
        engine = self.engines.get(camera_id)
        if engine is None:
            return
        # 隔离协议：标定与漏检估计只能用开发段样本，绝不能拿测试段来定阈值
        if self._holdout and not (
                self._in_split(camera_id, window[0], "dev")
                and any(a <= window[0] and window[1] < b for a,b in self._split_ranges("dev"))):
            self._audit_skipped += 1
            return
        roi_list = self.rois.get(camera_id) or []
        if not roi_list:
            return
        features = engine.buffer.window(window[0], window[1])
        if not features:
            return
        pseudo = Candidate(
            candidate_id=f"{camera_id}-AUDIT-{len(self.audit_samples):05d}",
            camera_id=camera_id,
            track_id=-1,
            roi_id=roi_list[0].roi_id,
            event_class=roi_list[0].event_class,
            # 抽样窗口没有状态机锚点：停留进度项按"无目标"处理，
            # 不能虚构一个已滞留满阈值的候选，否则标定阈值会被系统性抬高。
            t_enter=window[1],
            t_trigger=window[1],
            accum_s=1.0,
            dwell_threshold_s=float(roi_list[0].dwell_threshold_s
                                    or self.cfg.get("fsm.dwell_threshold_s", 45.0)),
            continuity={"suspended": False, "gaps": [], "policy": "audit",
                        "continuous_verified": True},
            snapshot={},
            window=window,
            flags=["audit_sample"],
        )
        stage2 = self.localizer.run(pseudo, features)
        self.stage2_results[pseudo.candidate_id] = stage2
        if stage2.decision == EVENT:
            self.negative_scores.append(stage2.raw_score)
        events = list(getattr(self.source, "gt_events", []) or [])
        event_in_window = any(
            e.camera_id == camera_id and e.start <= window[1] and e.end >= window[0]
            for e in events)
        if not getattr(self.source, "ground_truth_available", True):
            event_in_window = None
        self.audit_samples.append({
            "camera_id": camera_id,
            "window_start": round(window[0], 3),
            "window_end": round(window[1], 3),
            "decision": stage2.decision,
            "score": stage2.raw_score,
            "valid_for_calibration": (stage2.decision != SYSTEM_ERROR and stage2.validity.get("valid", False)
                                      and stage2.validity.get("mean_snr", 0) >= float(self.cfg.get("stage2.validity.min_snr",12))),
            "event_in_window": event_in_window,
            "active_fsm": False,
            "split": "dev" if self._holdout else "all",
        })

    # ------------------------------------------------------------------ 困难样本
    def _roi_threshold(self, camera_id: str, roi_id: str) -> float:
        for roi in self.rois.get(camera_id, []):
            if roi.roi_id == roi_id:
                return float(roi.dwell_threshold_s or
                             self.cfg.get("fsm.dwell_threshold_s", 45.0))
        return float(self.cfg.get("fsm.dwell_threshold_s", 45.0))

    def _difficult_cases(self) -> dict:
        """把"正常与困难输入"分类列出来：短暂停留、遮挡、授权作业、看不清、采集中断。

        数据来源是状态机审计轨迹与告警记录本身，不额外造数。
        """
        short_stay: list[dict] = []
        incomplete: list[dict] = []
        opened: dict[tuple, dict] = {}
        for item in self.fsm_audit:
            kind = item.get("kind")
            key = (item.get("camera_id"), item.get("track_id"), item.get("roi_id"))
            if kind == "entered":
                opened[key] = {
                    "camera_id": key[0], "track_id": key[1], "roi_id": key[2],
                    "t_enter": item.get("payload", {}).get("t_enter", item.get("ts")),
                    "suspended": False, "candidate": False,
                }
            elif key in opened:
                if kind == "suspended":
                    opened[key]["suspended"] = True
                elif kind == "resumed":
                    opened[key]["suspended"] = False
                elif kind == "candidate":
                    opened[key]["candidate"] = True
                elif kind in ("exit", "lost"):
                    rec = opened.pop(key)
                    payload = item.get("payload", {}) or {}
                    accum = float(payload.get("accum_s", 0.0) or 0.0)
                    detail = payload.get("detail", {}) or {}
                    thr = self._roi_threshold(rec["camera_id"], rec["roi_id"])
                    if accum >= thr and kind == "lost":
                        # 累计已够长却没有被确认离开：这才是"证据不完整"，不能冒充连续停留
                        incomplete.append({
                            "camera_id": rec["camera_id"], "roi_id": rec["roi_id"],
                            "t_enter": round(float(rec["t_enter"] or 0.0), 3),
                            "t_end": round(float(item.get("ts", 0.0)), 3),
                            "accum_s": round(accum, 3),
                            "threshold_s": thr,
                            "outcome": detail.get("outcome", "LOST"),
                            "reason": detail.get("reason", "身份未关联/超观察窗"),
                            "note": "跟踪中断，按证据不完整归档，不冒充连续停留",
                        })
                    elif not rec["candidate"] and accum >= 3.0:
                        # 短于阈值的在场（无论目标最后离开还是丢失）都属"未打扰用户"的正常输入
                        short_stay.append({
                            "camera_id": rec["camera_id"], "roi_id": rec["roi_id"],
                            "t_enter": round(float(rec["t_enter"] or 0.0), 3),
                            "t_exit": round(float(item.get("ts", 0.0)), 3),
                            "accum_s": round(accum, 3),
                            "threshold_s": thr,
                            "outcome": detail.get("outcome", "EXITED"),
                            "occlusion_gap": rec["suspended"],
                            "reason": "低于滞留阈值" if accum < thr else "阈值边界（含容差）未触发",
                            "note": "正常视频里的短暂停留，未打扰用户",
                        })

        def alarms_with(status: str) -> list[dict]:
            out = []
            for a in self.alarms:
                if a.status != status:
                    continue
                card = a.card or {}
                out.append({
                    "alarm_id": a.alarm_id, "camera_id": a.camera_id,
                    "roi_id": a.roi_id, "event_class": a.event_class,
                    "t_trigger": a.t_trigger,
                    "reason": a.suppression_reason or
                    (card.get("Normative_Inference_Uncertainty", {}) or {}).get("basis", ""),
                })
            return out

        no_event = [s for s in self.audit_samples
                    if s.get("decision") == NO_EVENT and not s.get("event_in_window")]
        return {
            "short_stay": short_stay[:30],
            "evidence_incomplete": incomplete[:30],
            "authorized_suppressed": alarms_with("suppressed")[:30],
            "insufficient_evidence": alarms_with("deferred")[:30],
            "system_error": alarms_with("system_error")[:30],
            "no_event_windows": {
                "count": len(no_event),
                "samples": [{"camera_id": s["camera_id"],
                             "window": [s["window_start"], s["window_end"]]}
                            for s in no_event[:10]],
            },
            "counts": {
                "short_stay": len(short_stay),
                "evidence_incomplete": len(incomplete),
                "authorized_suppressed": len(alarms_with("suppressed")),
                "insufficient_evidence": len(alarms_with("deferred")),
                "system_error": len(alarms_with("system_error")),
                "no_event_windows": len(no_event),
            },
            "note": ("这张表对应正常与困难输入：短暂停留与无事件窗口说明不打扰用户，"
                     "遮挡与证据不完整说明不把连续停留冒充出来，"
                     "授权抑制与转人工说明两类非告警出口都留痕。"),
        }

    # ------------------------------------------------------------------ 时延
    def _latency(self, used_stage3: bool, tokens: dict) -> dict:
        lat = self.cfg.section("latency")
        j = float(lat.get("jitter_rel", 0.15))
        rng = self._rng
        comps = {
            "sampling_ms": jitter(rng, float(lat.get("sampling_ms", 40.0)), j),
            "transmission_ms": jitter(rng, float(lat.get("transmission_ms", 60.0)), j),
            "tracking_ms": jitter(rng, float(lat.get("tracking_ms", 12.0)), j),
            "stage2_ms": jitter(rng, float(lat.get("stage2_ms", 180.0)), j),
        }
        if used_stage3:
            comps["stage3_prefill_ms"] = jitter(rng, float(lat.get("stage3_prefill_ms", 240.0)), j)
            comps["stage3_decode_ms"] = jitter(rng, float(lat.get("stage3_decode_ms", 420.0)), j)
            comps["network_ms"] = jitter(rng, float(lat.get("network_ms", 60.0)), j)
            comps["render_ms"] = jitter(rng, float(lat.get("render_ms", 90.0)), j)
        else:
            comps["render_ms"] = jitter(rng, float(lat.get("render_ms", 40.0)), j)
        total = sum(comps.values())
        comps = {k: round(v, 2) for k, v in comps.items()}
        comps["total_ms"] = round(total, 2)
        comps["window_close_wait_ms"] = 0.0
        comps["bidirectional_reference_ms"] = round(
            total + float(self.cfg.get("latency.naive_clip_wait_s", 5000.0)), 2)
        comps["mode"] = "causal_left_window" if used_stage3 else "causal_prefilter_only"
        comps["measurement_kind"] = "simulation"
        comps["display_acknowledged"] = False
        return comps

    # ------------------------------------------------------------------ 计量
    def _pipeline_stats(self, frames: int) -> PipelineStats:
        stage1_ms = sum(e.gpu_ms for e in self.engines.values())
        dropped = sum(e.dropped_frames for e in self.engines.values())
        candidate_s = sum(e.candidate_video_s for e in self.engines.values())
        total_s = sum(h * 3600.0 for h in self.camera_hours.values())
        stage3_input_s = 0.0
        tokens_in = tokens_out = 0
        for alarm in self.alarms:
            if alarm.card is None:
                continue
            anchor = alarm.card.get("Temporal_Anchor", {})
            span = max(0.0, float(anchor.get("end", 0.0)) - float(anchor.get("start", 0.0)))
            stage3_input_s += span
            verifier_meta = alarm.card.get("verifier") or {}
            tokens = verifier_meta.get("tokens") or {}
            tokens_in += int(tokens.get("input", 0))
            tokens_out += int(tokens.get("output", 0))
        st3 = self.cfg.get("cost.stage", {}) or {}
        if tokens_in == 0 and tokens_out == 0:
            # 离线规则核验器不产生 Token；按配置的等价 Token 预算折算，保持口径可比
            frames_in = int(stage3_input_s * float(self.cfg.get("cameras.default_fps", 2.0)))
            tokens_in = frames_in * int(st3.get("stage3_input_tokens_per_frame", 520))
            tokens_out = len([a for a in self.alarms if a.card]) * \
                int(st3.get("stage3_output_tokens", 420))
        # 人工成本只算"人真的要看"的卡片；抽样审计是自动复算，不计人工工时
        human_minutes = (len([a for a in self.alarms if a.status in ("confirmed", "deferred")])
                         * float(self.cfg.get("cost.feedback.human_minutes_per_alarm", 2.5)))
        stats = PipelineStats(
            camera_hours=sum(self.camera_hours.values()),
            total_video_seconds=total_s,
            frames=frames,
            dropped_frames=dropped,
            stage1_gpu_ms=round(stage1_ms, 3),
            candidates=len(self.candidates),
            candidate_video_seconds=round(candidate_s, 3),
            stage2_gpu_ms=round(self.localizer.gpu_ms, 3),
            stage2_processed_seconds=round(self.localizer.processed_s, 3),
            stage3_input_seconds=round(stage3_input_s, 3),
            stage3_tokens_in=tokens_in,
            stage3_tokens_out=tokens_out,
            stage3_gpu_ms=round(self.verifier.gpu_ms, 3),
            stage3_calls=self.verifier.calls,
            displayed_alarms=len([a for a in self.alarms
                                  if a.status in ("confirmed", "deferred")]),
            deferred_alarms=len([a for a in self.alarms if a.status == "deferred"]),
            human_review_minutes=round(human_minutes, 2),
            egress_bytes=estimate_egress_bytes(
                PipelineStats(candidate_video_seconds=candidate_s), self.cfg.cost),
        )
        return stats

    def _decision_counts(self) -> dict:
        counts = {EVENT: 0, NO_EVENT: 0, INSUFFICIENT: 0, SYSTEM_ERROR: 0}
        for alarm in self.alarms:
            counts[alarm.triage] = counts.get(alarm.triage, 0) + 1
        return {
            "triage_counts": counts,
            "candidate_count": len(self.candidates),
            "stage3_calls": self.verifier.calls,
            "verifier_mode": self.verifier.mode,
        }

    def _score_histogram(self) -> dict:
        if not self.frame_scores:
            return {}
        buckets = [0.0] * 10
        pos = [0.0] * 10
        for label, score in self.frame_scores:
            idx = min(9, max(0, int(score * 10)))
            buckets[idx] += 1
            if label:
                pos[idx] += 1
        return {"bins": [round(i / 10.0, 1) for i in range(10)],
                "counts": [int(b) for b in buckets],
                "positives": [int(p) for p in pos]}

    # ------------------------------------------------------------------ 资源与模型
    def _resources(self, frames: int, wall: float) -> dict:
        """可用资源记录：完整耗时、峰值内存、实际调用量。

        峰值显存只在你真的跑了 GPU 模型时才有意义：参考实现是 CPU-only，
        因此这里如实写 not_measured，并允许用 cost.stage.peak_vram_gb 登记实测值。
        """
        configured_vram = self.cfg.get("cost.stage.peak_vram_gb")
        tokens = {"input": 0, "output": 0}
        for alarm in self.alarms:
            v = ((alarm.card or {}).get("verifier") or {}).get("tokens") or {}
            tokens["input"] += int(v.get("input", 0))
            tokens["output"] += int(v.get("output", 0))
        stage2_calls = sum(int(v) for v in (self.localizer.decisions or {}).values())
        return {
            "wall_seconds": round(wall, 3),
            "frames": frames,
            "throughput_fps": round(frames / wall, 1) if wall > 0 else None,
            "peak_memory_mb": _peak_memory_mb(),
            "gpu": {
                "used": False if self._source_kind() in ("synthetic", "test") else None,
                "status": "cpu_only_reference" if self._source_kind() in ("synthetic", "test") else "not_measured",
                "measured_peak_vram_gb": float(configured_vram) if configured_vram else None,
                "note": ("参考实现不加载模型权重，故无显存占用；"
                         "接入真实模型后用 cost.stage.peak_vram_gb 登记实测峰值。"),
            },
            "actual_calls": {
                "stage1_frames": frames,
                "stage2_localizer": stage2_calls,
                "stage3_verifier": self.verifier.calls,
                "audit_windows": len(self.audit_samples),
            },
            "tokens": tokens,
            "human_review_minutes": round(
                len([a for a in self.alarms if a.status in ("confirmed", "deferred")])
                * float(self.cfg.get("cost.feedback.human_minutes_per_alarm", 2.5)), 2),
            "human_review_measurement_kind": "estimate",
            "scope": "whole_run",
            "note": "人工复核劳动单独列出，不并入计算成本。",
        }

    def _models(self) -> dict:
        """模型清单：跑的是哪个版本、什么量化、哪条链路，便于复现与排错。"""
        models = json.loads(json.dumps(self.cfg.get("models", {}) or {}, ensure_ascii=False))
        for key in ("detector", "localizer", "verifier", "vlm"):
            models.setdefault(key, {})
        models["detector"]["provider"] = self._source_kind()
        models["localizer"]["id"] = str(getattr(self.localizer.scorer, "name",
                                                models["localizer"].get("id", "")))
        kind = str(self.cfg.get("stage3.verifier", "rule_based"))
        models["verifier"]["mode"] = self.verifier.mode
        if kind == "vlm":
            models["vlm"]["id"] = str(self.cfg.get("stage3.vlm.model") or "vlm-endpoint")
            models["vlm"]["endpoint"] = str(self.cfg.get("stage3.vlm.endpoint") or "")
            models["vlm"]["provider"] = "openai-compatible"
            models["verifier"]["id"] = f"vlm:{models['vlm']['id']}"
            models["verifier"]["provider"] = "openai-compatible"
        else:
            models["verifier"]["id"] = "rule-based-reference"
            models["verifier"]["provider"] = "builtin"
        return models

    # ------------------------------------------------------------------ 元数据/落盘
    def _meta(self, frames: int, wall: float) -> dict:
        from .reproducibility import environment_info, input_files
        return {
            "environment": environment_info(),
            "input_files": input_files(self.cfg, self.source),
            "run_id": self.run_id,
            "started_at": self.started_at,
            "effective_config": self.cfg.as_dict(),
            "ruleset_snapshot": self.ruleset.to_dict(),
            "latency_measurement_kind": "simulation" if self._source_kind() in ("synthetic", "test") else "measured_processing",
            "cvalarm_version": __version__,
            "frames": frames,
            "wall_seconds": round(wall, 3),
            "processing_fps": round(frames / wall, 1) if wall > 0 else None,
            "config_digest": content_hash(self.cfg.as_dict()),
            "config_summary": json.loads(self.cfg.describe()),
            "ruleset": {
                "ruleset_id": self.ruleset.ruleset_id,
                "version_label": self.ruleset.version_label,
                "digest": self.ruleset.digest,
                "rule_count": len(self.ruleset.rules),
            },
            "source": self.source.describe() if hasattr(self.source, "describe") else {},
            "calibration": self.localizer.cal.to_dict(),
            "camera_hours": {k: round(v, 4) for k, v in self.camera_hours.items()},
            "verifier_mode": self.verifier.mode,
            "seed": int(self.cfg.get("runtime.seed", 7)),
            "provenance": self.provenance,
            "notes": [
                "本运行使用可替换的合成检测层（或外部回放数据），不评测检测器本身。",
                "TTA 有两种口径：事件起点→告警、阈值满足→告警，两者差值即规程等待。",
                "定位边界误差只统计已命中且真值提供 evidence_span 的事件，与存在性分开。",
                "system_error 窗口不判定为正常，单独计数并入重检队列。",
                "本报告为离线回放验证结果，不是现场实时接流指标。",
            ],
        }

    def _persist(self, result: RunResult) -> None:
        out = ensure_dir(self.out_dir)
        write_json(os.path.join(out, "run_meta.json"), result.meta)
        write_json(os.path.join(out, "metrics.json"), round_floats(result.metrics))
        write_json(os.path.join(out, "cost.json"), round_floats(result.cost))
        write_json(os.path.join(out, "reliability.json"), round_floats(result.reliability))
        write_json(os.path.join(out, "audit.json"), round_floats(result.audit))
        write_json(os.path.join(out, "frame_histogram.json"), result.frame_histogram)
        write_json(os.path.join(out, "resources.json"), result.meta.get("resources", {}))
        write_json(os.path.join(out, "models.json"), result.meta.get("models", {}))
        write_json(os.path.join(out, "difficult_cases.json"),
                   result.metrics.get("difficult_cases", {}))
        write_json(os.path.join(out, "run_summary.json"), {
            "alarm_counts": _status_counts(self.alarms),
            "stats": result.stats,
            "wall_seconds": round(result.wall_seconds, 3),
            "metrics_headline": {
                "event_recall": result.metrics.get("event_recall"),
                "event_recall_incl_deferred": result.metrics.get("event_recall_incl_deferred"),
                "false_alarms_per_camera_hour":
                    result.metrics.get("false_alarms_per_camera_hour"),
                "frame_roc_auc": result.metrics.get("frame_roc_auc"),
                "tta_p50": (result.metrics.get("tta") or {}).get("p50"),
                "tta_event_start_p50": (result.metrics.get("tta_event_start") or {}).get("p50"),
                "localization_start_mae_s":
                    (result.metrics.get("localization") or {}).get("start_mae_s"),
                "localization_miou":
                    (result.metrics.get("localization") or {}).get("miou_mean"),
                "evaluable_video_hours": result.metrics.get("evaluable_video_hours"),
                "cost_per_camera_hour": result.cost["components_money_per_camera_hour"]["total"],
            },
            "resources": result.meta.get("resources", {}),
            "models": result.meta.get("models", {}),
            "protocol": result.meta.get("protocol", {}),
        })
        write_jsonl(os.path.join(out, "candidates.jsonl"), [c.to_dict() for c in self.candidates])
        write_jsonl(os.path.join(out, "stage2.jsonl"), [
            {"candidate_id": cid, **res.to_dict()} for cid, res in self.stage2_results.items()])
        write_jsonl(os.path.join(out, "alarms.jsonl"), [a.to_dict() for a in self.alarms])
        write_jsonl(os.path.join(out, "fsm_audit.jsonl"), self.fsm_audit)
        write_jsonl(os.path.join(out, "audit_samples.jsonl"), self.audit_samples)
        LOG.info("运行产物已写入 %s（%d 告警 / %d 候选 / %d 帧）",
                 out, len(self.alarms), len(self.candidates), result.meta.get("frames", 0))


def _peak_memory_mb() -> Optional[float]:
    """进程峰值内存（MB）。Windows 用 psapi，POSIX 用 getrusage；失败返回 None。"""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.cast(ctypes.windll.kernel32.GetCurrentProcess(),
                                 wintypes.HANDLE)
            for lib, fn_name in (("kernel32", "K32GetProcessMemoryInfo"),
                                 ("psapi", "GetProcessMemoryInfo")):
                try:
                    func = getattr(getattr(ctypes.windll, lib), fn_name)
                except AttributeError:
                    continue
                func.argtypes = [wintypes.HANDLE,
                                 ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                                 wintypes.DWORD]
                func.restype = wintypes.BOOL
                if func(handle, ctypes.byref(counters), counters.cb):
                    return round(counters.PeakWorkingSetSize / (1024.0 * 1024.0), 1)
            return None
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux 单位 KB，macOS 单位字节
        divisor = 1024.0 if os.uname().sysname != "Darwin" else 1024.0 * 1024.0
        return round(usage / divisor, 1)
    except Exception:
        return None


def _status_counts(alarms: list[AlarmRecord]) -> dict:
    counts: dict[str, int] = {}
    for alarm in alarms:
        counts[alarm.status] = counts.get(alarm.status, 0) + 1
    return counts


# --------------------------------------------------------------------------- 便捷入口


def run_pipeline(cfg: Config, source: Any = None, out_dir: Optional[str] = None,
                 ruleset: Optional[RuleSet] = None, persist: bool = True,
                 verifier: Optional[VerifierEngine] = None,
                 localizer: Optional[Localizer] = None) -> RunResult:
    if source is None:
        from .source import load_source

        source = load_source("demo", hours=float(cfg.get("runtime.demo_hours", 3.0)))
    pipeline = Pipeline(cfg, source, ruleset=ruleset, verifier=verifier,
                        localizer=localizer, persist=persist, out_dir=out_dir)
    return pipeline.run()


def calibrate_from_run(run_dir: str, cfg: Config, min_negatives: int = 20) -> dict:
    """从一次运行的审计样本中取硬负例分数，生成拒识标定产物。"""
    from .locator import calibrate, save_calibration

    samples = []
    path = os.path.join(run_dir, "audit_samples.jsonl")
    if os.path.exists(path):
        from .util import read_jsonl

        samples = list(read_jsonl(path))
    scores = [float(s.get("score", 0.0)) for s in samples
              if s.get("event_in_window") is False and s.get("valid_for_calibration") is True]
    cal = calibrate(scores, min_negatives=min_negatives,
                    confirm_gap=float(cfg.get("stage2.calibration.confirm_gap", 0.18)))
    from .util import read_json
    meta = read_json(os.path.join(run_dir, "run_meta.json"), default={}) or {}
    cal.context = meta.get("effective_config", {}).get("runtime", {}).get("calibration_context", "")
    save_calibration(cfg, cal)
    return cal.to_dict()


def regression_metrics(cfg: Config, ruleset: RuleSet, hours: float = 1.2) -> dict:
    """在固定回归集上重放，返回门禁所需指标（不落盘）。"""
    from .source import build_regression

    source = build_regression(hours=hours)
    result = run_pipeline(cfg, source, ruleset=ruleset, persist=False)
    m = result.metrics
    display = m.get("displayed_alarms", 0) or 0
    deferred = m.get("deferred_alarms", 0) or 0
    return {
        "event_recall": float(m.get("event_recall", 0.0)),
        "event_recall_incl_deferred": float(m.get("event_recall_incl_deferred", 0.0)),
        "false_alarms_per_camera_hour": float(m.get("false_alarms_per_camera_hour", 0.0)),
        "events": int(m.get("events", 0)),
        "fa": int(m.get("false_alarms", 0)),
        "camera_hours": float(m.get("camera_hours", 0.0)),
        "deferred_rate": round(deferred / display, 4) if display else 0.0,
        "displayed_alarms": display,
        "system_error_windows": int(m.get("triage_counts", {}).get(SYSTEM_ERROR, 0))
        if isinstance(m.get("triage_counts"), dict) else 0,
    }
