"""静态 HTML 报告生成：把一次运行的全部产物渲染成可离线打开的页面。"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from .config import Config
from .cost import PipelineStats, compare_topologies
from .feedback import AuditStore, FeedbackStore
from .rules import RuleRegistry
from .util import get_logger, now_iso, read_json, read_jsonl, write_json
from .webpage import build_payload, render_page

LOG = get_logger("cvalarm.report")


def _load_run(run_dir: str) -> dict:
    def _j(name: str, default: Any = None) -> Any:
        return read_json(os.path.join(run_dir, name), default=default if default is not None else {})

    meta = _j("run_meta.json")
    metrics = _j("metrics.json")
    cost = _j("cost.json")
    reliability = _j("reliability.json")
    audit = _j("audit.json")
    histogram = _j("frame_histogram.json")
    summary = _j("run_summary.json")
    alarms = list(read_jsonl(os.path.join(run_dir, "alarms.jsonl")))
    events = metrics.get("events_detail") or []
    return {
        "meta": meta, "metrics": metrics, "cost": cost, "reliability": reliability,
        "audit": audit, "histogram": histogram, "summary": summary,
        "alarms": alarms, "events": events,
    }


def build_page_data(run_dir: str, cfg: Config, state_dir: Optional[str] = None) -> dict:
    run = _load_run(run_dir)
    snapshot = run["meta"].get("effective_config")
    if snapshot:
        cfg = Config(snapshot, base_dir=cfg.base_dir)
    state = state_dir or cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
    registry = RuleRegistry(cfg, state)
    try:
        ruleset = registry.active()
        rules = run["meta"].get("ruleset_snapshot") or ruleset.to_dict()
    except Exception as exc:  # 规则文件缺失时页面仍应可用
        LOG.warning("读取规则集失败：%s", exc)
        rules = run["meta"].get("ruleset_snapshot") or {}
    ledger = registry.ledger(limit=30)
    stats = run["summary"].get("stats") or {}
    topologies = []
    if stats:
        try:
            ps = PipelineStats(**{k: stats[k] for k in PipelineStats().__dict__ if k in stats})
            topologies = compare_topologies(ps, cfg.cost, cameras=len(
                run["meta"].get("camera_hours", {}) or {}) or 1)
        except Exception as exc:  # pragma: no cover - 兼容旧产物
            LOG.warning("拓扑对比计算失败：%s", exc)
    try:
        feedback_summary = FeedbackStore(cfg, state).summary(run["meta"].get("run_id", ""))
        feedback_entries = [x for x in FeedbackStore(cfg, state).entries()
                            if x.get("run_id") == run["meta"].get("run_id")]
        audit_summary = AuditStore(cfg, state).summary()
    except Exception:
        feedback_summary, audit_summary = {}, {}
        feedback_entries = []
    return build_payload(
        meta=run["meta"], metrics=run["metrics"], cost=run["cost"],
        reliability=run["reliability"], audit=run["audit"], alarms=run["alarms"],
        events=run["events"], histogram=run["histogram"], rules=rules, ledger=ledger,
        topologies=topologies,
        feedback={"operator": feedback_summary, "audit_store": audit_summary,
                  "entries":feedback_entries, "reason_codes":cfg.get("feedback.reason_codes", [])},
        generated_at=now_iso(),
    )


def write_report(run_dir: str, cfg: Config, out_path: Optional[str] = None,
                 state_dir: Optional[str] = None,
                 title: str = "持续视频监控异常告警 · 工程评测报告") -> str:
    payload = build_page_data(run_dir, cfg, state_dir)
    out_path = out_path or os.path.join(run_dir, "report.html")
    html = render_page(payload, title=title, live=False)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    # 同时落一份可直接给前端/BI 消费的 JSON
    data_path = os.path.join(run_dir, "report_data.json")
    write_json(data_path, payload)
    LOG.info("报告已生成：%s", out_path)
    return out_path


def headline(run_dir: str) -> dict:
    """终端摘要（CLI 用）。"""
    metrics = read_json(os.path.join(run_dir, "metrics.json"), default={}) or {}
    cost = read_json(os.path.join(run_dir, "cost.json"), default={}) or {}
    meta = read_json(os.path.join(run_dir, "run_meta.json"), default={}) or {}
    return {
        "frames": meta.get("frames"),
        "camera_hours": metrics.get("camera_hours"),
        "evaluable_video_hours": metrics.get("evaluable_video_hours"),
        "events": metrics.get("events"),
        "event_recall": metrics.get("event_recall"),
        "event_recall_incl_deferred": metrics.get("event_recall_incl_deferred"),
        "false_alarms_per_camera_hour": metrics.get("false_alarms_per_camera_hour"),
        "frame_roc_auc": metrics.get("frame_roc_auc"),
        "tta_p50": (metrics.get("tta") or {}).get("p50"),
        "tta_p90": (metrics.get("tta") or {}).get("p90"),
        "tta_event_start_p50": (metrics.get("tta_event_start") or {}).get("p50"),
        "threshold_delay_p50": (metrics.get("threshold_delay") or {}).get("p50"),
        "loc_start_mae": (metrics.get("localization") or {}).get("start_mae_s"),
        "loc_miou": (metrics.get("localization") or {}).get("miou_mean"),
        "loc_samples": (metrics.get("localization") or {}).get("n"),
        "deferred": metrics.get("deferred_alarms"),
        "suppressed": metrics.get("suppressed_alarms"),
        "system_error": (metrics.get("triage_counts") or {}).get("SYSTEM_ERROR"),
        "protocol": (metrics.get("protocol") or {}).get("mode"),
        "peak_memory_mb": (meta.get("resources") or {}).get("peak_memory_mb"),
        "cost_per_camera_hour": (cost.get("components_money_per_camera_hour") or {}).get("total"),
        "topology": cost.get("topology"),
        "ruleset": (meta.get("ruleset") or {}).get("version_label"),
    }


def print_headline(run_dir: str, stream=None) -> str:
    h = headline(run_dir)
    lines = [
        "=" * 66,
        "运行摘要",
        "=" * 66,
        f"  帧数                 : {h['frames']}",
        f"  可评价时长           : {h['evaluable_video_hours']} 机位·小时"
        f"（协议：{h['protocol']}）",
        f"  事件数               : {h['events']}",
        f"  事件召回(确证)       : {h['event_recall']}",
        f"  事件召回(含转人工)   : {h['event_recall_incl_deferred']}",
        f"  FA/CH                : {h['false_alarms_per_camera_hour']}",
        f"  帧级 ROC-AUC         : {h['frame_roc_auc']}",
        f"  告警时延 p50/p90     : {h['tta_p50']} / {h['tta_p90']} s（阈值满足→告警）",
        f"  事件起点→告警 p50    : {h['tta_event_start_p50']} s"
        f"（其中规程等待 {h['threshold_delay_p50']} s）",
        f"  定位起点误差/mIoU    : {h['loc_start_mae']} s / {h['loc_miou']}（n={h['loc_samples']}）",
        f"  转人工/抑制/采集中断 : {h['deferred']} / {h['suppressed']} / {h['system_error']}",
        f"  成本/机位·小时       : {h['cost_per_camera_hour']}（{h['topology']}）",
        f"  峰值内存             : {h['peak_memory_mb']} MB",
        f"  规则集版本           : {h['ruleset']}",
        "=" * 66,
    ]
    text = "\n".join(lines)
    if stream is not None:
        stream.write(text + "\n")
    return text


def dump_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
