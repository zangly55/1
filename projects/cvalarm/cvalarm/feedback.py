"""Stage4 人工反馈闭环与抽样审计。

论文第 6 章的三个工程要点：
  1. 处置界面的三级判断（Confirm / Dismiss / Uncertain）必须落成结构化反馈；
  2. Confirm 与 Dismiss 都有"告警已显示"这一前提，因此反馈天然带有选择偏差；
     评估必须另行抽检未告警时段与被拒候选，且尽量对标注者隐藏模型判断；
  3. 误报片段与驳回理由经离线反思转成候选规则，但候选规则不得热加载。
"""
from __future__ import annotations

import os
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from .config import Config
from .util import append_jsonl, get_logger, now_iso, read_jsonl, safe_div, wilson_interval

LOG = get_logger("cvalarm.feedback")

VERDICTS = ("confirm", "dismiss", "uncertain")
_WRITE_LOCK = threading.RLock()


@dataclass
class FeedbackEntry:
    alarm_id: str
    verdict: str
    camera_id: str = ""
    event_class: str = ""
    rule_version: str = ""
    reason_code: str = ""
    note: str = ""
    operator: str = "unknown"
    ts_display: float = 0.0
    created_at: str = field(default_factory=now_iso)
    run_id: str = ""

    def to_dict(self) -> dict:
        return {
            "alarm_id": self.alarm_id,
            "verdict": self.verdict,
            "camera_id": self.camera_id,
            "event_class": self.event_class,
            "rule_version": self.rule_version,
            "reason_code": self.reason_code,
            "note": self.note,
            "operator": self.operator,
            "ts_display": round(self.ts_display, 3),
            "created_at": self.created_at,
            "run_id": self.run_id,
        }


class FeedbackStore:
    def __init__(self, cfg: Config, state_dir: Optional[str] = None) -> None:
        self.cfg = cfg
        self.state_dir = state_dir or cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
        path = str(cfg.get("feedback.path", "state/feedback.jsonl"))
        self.path = self._join(path)
        self.reason_codes = list(cfg.get("feedback.reason_codes", []))

    def _join(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        rel = path[len("state/"):] if path.startswith("state/") else os.path.basename(path)
        return os.path.join(self.state_dir, rel)

    def add(self, entry: FeedbackEntry) -> dict:
        if not entry.alarm_id:
            raise ValueError("反馈必须关联告警")
        if entry.verdict not in VERDICTS:
            raise ValueError(f"非法反馈结论：{entry.verdict}")
        if entry.verdict == "dismiss" and not entry.reason_code:
            raise ValueError("驳回必须给出理由代码（论文 6.1 节：要求选择或填写误报理由）")
        if entry.reason_code and self.reason_codes and entry.reason_code not in self.reason_codes:
            raise ValueError(f"未知驳回理由代码：{entry.reason_code}")
        record = entry.to_dict()
        with _WRITE_LOCK:
            for previous in reversed(self.entries()):
                if previous.get("alarm_id") == entry.alarm_id and previous.get("run_id", "") == entry.run_id:
                    if all(previous.get(k) == v for k,v in record.items() if k != "created_at"):
                        return previous
                    break
            append_jsonl(self.path, [record])
        return record

    def entries(self) -> list[dict]:
        return list(read_jsonl(self.path))

    def summary(self, run_id: str | None = None) -> dict:
        items = [x for x in self.entries() if run_id is None or x.get("run_id") == run_id]
        verdict_counts = Counter(i.get("verdict") for i in items)
        reasons = Counter(i.get("reason_code") for i in items if i.get("verdict") == "dismiss")
        by_camera = Counter(i.get("camera_id") for i in items)
        total = len(items)
        dismissed = verdict_counts.get("dismiss", 0)
        return {
            "total": total,
            "confirm": verdict_counts.get("confirm", 0),
            "dismiss": dismissed,
            "uncertain": verdict_counts.get("uncertain", 0),
            "dismiss_rate": round(safe_div(dismissed, total), 4) if total else None,
            "reason_codes": dict(reasons),
            "by_camera": dict(by_camera),
            "selection_bias_note": (
                "以上统计只覆盖已显示的告警，存在选择偏差："
                "被前筛或定位静默丢弃的真实事件不会出现在这里。"
                "降低驳回率不等于系统变好，须结合抽样审计估计漏检。"),
            "usable_for_reflection": {k: v for k, v in reasons.items()},
        }

    def reason_counts(self) -> dict:
        return dict(Counter(i.get("reason_code") for i in self.entries()
                            if i.get("verdict") == "dismiss" and i.get("reason_code")))


class AuditStore:
    """抽样审计记录：未告警时段与被拒候选的盲检样本。"""

    def __init__(self, cfg: Config, state_dir: Optional[str] = None) -> None:
        self.cfg = cfg
        self.state_dir = state_dir or cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
        path = str(cfg.get("feedback.audit_path", "state/audit_samples.jsonl"))
        self.path = os.path.join(self.state_dir, os.path.basename(path))

    def add(self, samples: Iterable[dict]) -> int:
        rows = []
        for sample in samples:
            row = dict(sample)
            row.setdefault("created_at", now_iso())
            row.setdefault("blind", bool(self.cfg.get("feedback.blind_audit", True)))
            rows.append(row)
        return append_jsonl(self.path, rows)

    def entries(self) -> list[dict]:
        return list(read_jsonl(self.path))

    def summary(self) -> dict:
        items = self.entries()
        decisions = Counter(i.get("decision") for i in items)
        return {
            "samples": len(items),
            "by_decision": dict(decisions),
            "blind": bool(self.cfg.get("feedback.blind_audit", True)),
            "windows_per_camera_hour": float(
                self.cfg.get("feedback.audit_windows_per_camera_hour", 2.0)),
        }


def estimate_miss_rate(audit_samples: Sequence[dict], cfg: dict,
                       camera_hours: float = 0.0) -> dict:
    """用抽样审计估计前筛漏检率（并对选择偏差给出置信区间）。

    每个样本是"未告警时段"里的一个窗口；若该窗口与某真事件重叠，
    说明前筛漏掉了它——这类窗口占全部事件相关窗口的比例即为漏检率估计。
    camera_hours 为该组摄像头累计有效观测小时（用于计算审计的时间覆盖率）。
    """
    event_windows = [s for s in audit_samples if s.get("event_in_window")]
    n_event_windows = len(event_windows)
    missed = sum(1 for s in event_windows if s.get("decision") in ("NO_EVENT", "INSUFFICIENT_EVIDENCE"))
    total_seconds = sum(float(s.get("window_end", 0.0)) - float(s.get("window_start", 0.0))
                        for s in audit_samples)
    coverage = 0.0
    if camera_hours and camera_hours > 0:
        coverage = total_seconds / (camera_hours * 3600.0)
    ci = wilson_interval(missed, n_event_windows) if n_event_windows else (0.0, 1.0)
    return {
        "audit_windows": len(audit_samples),
        "event_containing_windows": n_event_windows,
        "missed_by_prefilter": missed,
        "estimated_miss_rate": round(safe_div(missed, n_event_windows), 4)
        if n_event_windows else None,
        "ci95": [round(ci[0], 4), round(ci[1], 4)],
        "time_coverage": round(coverage, 5),
        "blind": bool(cfg.get("feedback.blind_audit", True)),
        "note": ("抽样比例有限，区间宽度反映样本量；不得把点估计当作未来漏检率的保证。"
                 "若审计窗口本身包含事件，必须计入事件级评测而不是只统计驳回率。"),
    }


def load_events_for_audit(path: str) -> list:
    from .types import GtEvent

    data = read_jsonl(path)
    out = []
    for row in data:
        out.append(GtEvent(**row))
    return out
