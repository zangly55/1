"""评测口径：帧级 ROC-AUC、事件级召回、FA/CH、TTA。

论文 2.3 节的核心主张：只用帧级 ROC-AUC 不足以评价告警负担。
本模块同时给出三类指标，并把每个口径的分母、合并规则、容差写进结果里，
使报告读起来不会把"排序成绩"误当成"告警负担"。

匹配口径（必须事先规定，否则结果不可比）：
  * 一次告警的时间锚点取"条件成立时刻" t_trigger，而不是 Stage2 的证据区间。
    原因：证据区间必然落在违规成立之前（因果时序），若要求它与违规区间高重叠，
    真实告警会被系统性判为漏报。
  * 因此区间事件按"t_trigger 落在 [gt.start - pre_tol, gt.end + post_tol]"匹配，
    同时报告告警区间与违规区间的 IoU，供抽查。
  * 一对一匹配：告警按时间排序贪心匹配最近的未占用事件；重复告警单独计数。
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

from .types import AlarmRecord, GtEvent
from .util import clamp, mean, percentile, safe_div, wilson_interval

TP = "TP"
FP = "FP"
MISS = "MISS"


# --------------------------------------------------------------------------- ROC


def roc_auc(labels: Sequence[int], scores: Sequence[float]) -> float:
    """秩和（Mann-Whitney U）法计算 ROC-AUC，正确处理并列分数。

    若样本只有一类，ROC-AUC 无定义——返回 NaN 而不是 0.5 之类的替代值。
    """
    n = len(labels)
    if n != len(scores) or n == 0:
        return float("nan")
    positives = sum(1 for y in labels if y > 0)
    negatives = n - positives
    if positives == 0 or negatives == 0:
        return float("nan")
    order = sorted(range(n), key=lambda i: scores[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    sum_pos_ranks = sum(ranks[i] for i in range(n) if labels[i] > 0)
    u = sum_pos_ranks - positives * (positives + 1) / 2.0
    return u / (positives * negatives)


# --------------------------------------------------------------------------- 事件匹配


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def interval_iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = _overlap(a[0], a[1], b[0], b[1])
    if inter <= 0.0:
        return 0.0
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def match_alarms(events: Sequence[GtEvent], alarms: Sequence[AlarmRecord],
                 cfg: dict) -> dict:
    """一对一匹配。返回匹配结果、逐事件状态、重复告警计数。"""
    match_cfg = cfg.get("event_match", {}) if cfg else {}
    pre_tol = float(match_cfg.get("pre_tolerance_s", 5.0))
    post_tol = float(match_cfg.get("post_tolerance_s", 20.0))
    iou_thresh = float(match_cfg.get("interval_iou", 0.3))
    point_tol = float(match_cfg.get("point_tolerance_s", 10.0))

    displayed = [a for a in alarms if a.status in ("confirmed", "deferred")]
    used_events: set[str] = set()
    per_event: dict[str, dict] = {}
    for ev in events:
        per_event[ev.event_id] = {
            "event_id": ev.event_id,
            "camera_id": ev.camera_id,
            "event_class": ev.event_class,
            "start": round(ev.start, 3),
            "end": round(ev.end, 3),
            "status": MISS,
            "alarm_id": None,
            "alarm_status": None,
            "iou": 0.0,
            "tta": None,
            "tta_event_start": None,
        }

    matched_alarms: list[tuple[AlarmRecord, GtEvent, float]] = []
    duplicates = 0
    duplicate_ids: set[str] = set()
    for alarm in sorted(displayed, key=lambda a: (a.status != "confirmed", a.t_trigger)):
        candidates: list[tuple[float, GtEvent, float]] = []
        for ev in events:
            if (ev.camera_id != alarm.camera_id or ev.event_class != alarm.event_class
                    or ev.roi_id != alarm.roi_id):
                continue
            iou = 0.0
            if alarm.interval:
                iou = interval_iou((alarm.interval.get("start", 0.0), alarm.interval.get("end", 0.0)),
                                   (ev.start, ev.end))
            trigger_ok = (ev.start - pre_tol) <= alarm.t_trigger <= (ev.end + post_tol)
            if ev.kind == "point":
                trigger_ok = abs(alarm.t_trigger - ev.start) <= point_tol
            if trigger_ok or iou >= iou_thresh:
                distance = abs(alarm.t_trigger - clamp(alarm.t_trigger, ev.start, ev.end))
                candidates.append((distance, ev, iou))
        if not candidates:
            continue
        candidates.sort(key=lambda item: item[0])
        available = [item for item in candidates if item[1].event_id not in used_events]
        if not available:
            duplicates += 1  # 同一事件被重复告警：单独记录，仍计入复核负担
            duplicate_ids.add(alarm.alarm_id)
            continue
        _dist, ev, iou = available[0]
        used_events.add(ev.event_id)
        matched_alarms.append((alarm, ev, iou))
        entry = per_event[ev.event_id]
        if entry["status"] == MISS:
            entry.update({
                "status": TP,
                "alarm_id": alarm.alarm_id,
                "alarm_status": alarm.status,
                "iou": round(iou, 4),
                # 两种时延口径同时保留，不能合并：
                #   tta             = 阈值满足（条件成立）→ 卡片显示
                #   tta_event_start = 事件起点（首次可见）→ 卡片显示
                # 超时停留类事件两者的差就是"规程等待"，否则 45 秒阈值会被误读成系统慢。
                "tta": round(alarm.t_display - ev.condition_ts, 3),
                "tta_event_start": round(alarm.t_display - ev.start, 3),
            })

    matched_ids = {a.alarm_id for a, _e, _i in matched_alarms}
    false_alarms = [a for a in displayed
                    if a.alarm_id not in matched_ids and a.alarm_id not in duplicate_ids]
    return {
        "per_event": list(per_event.values()),
        "matched": [(a.alarm_id, ev.event_id, iou) for a, ev, iou in matched_alarms],
        "false_alarms": false_alarms,
        "duplicate_alarms": duplicates,
        "displayed": displayed,
    }


def merge_false_alarms(false_alarms: Sequence[AlarmRecord], merge_gap_s: float) -> list[AlarmRecord]:
    """同一摄像头、同一区域、时间相近的误报合并为一次复核负担。"""
    by_key: dict[tuple[str, str, str], list[AlarmRecord]] = {}
    for alarm in false_alarms:
        by_key.setdefault((alarm.camera_id, alarm.roi_id, alarm.event_class), []).append(alarm)
    merged: list[AlarmRecord] = []
    for items in by_key.values():
        items = sorted(items, key=lambda a: a.t_trigger)
        last_ts = None
        for alarm in items:
            if last_ts is None or alarm.t_trigger - last_ts > merge_gap_s:
                merged.append(alarm)
            last_ts = alarm.t_trigger
    return merged


# --------------------------------------------------------------------------- 汇总


def evaluate(events: Sequence[GtEvent], alarms: Sequence[AlarmRecord],
             camera_hours: dict[str, float], frame_scores: Optional[Sequence[tuple[int, float]]],
             cfg: dict, extra: Optional[dict] = None) -> dict:
    """产出完整评测结果。camera_hours 为逐摄像头有效观测小时（分母逐路累加）。"""
    matching = match_alarms(events, alarms, cfg)
    per_event = matching["per_event"]
    displayed = matching["displayed"]
    matched_ids = {a for a, _e, _i in matching["matched"]}
    confirmed_ids = {a.alarm_id for a in displayed if a.status == "confirmed"}

    total_events = len(events)
    tp_events = sum(1 for e in per_event if e["status"] == TP)
    tp_confirmed = sum(1 for e in per_event
                       if e["status"] == TP and e["alarm_status"] == "confirmed")
    strict_recall = safe_div(tp_confirmed, total_events)
    recall_incl_deferred = safe_div(tp_events, total_events)

    merge_gap = float(cfg.get("fa_merge_gap_s", 300.0) if cfg else 300.0)
    merged_fa = merge_false_alarms(matching["false_alarms"], merge_gap)
    total_camera_hours = sum(camera_hours.values())
    fa_per_ch = safe_div(len(merged_fa), total_camera_hours) if total_camera_hours else None

    precision = safe_div(len(matching["matched"]), len(displayed))

    ttas = [e["tta"] for e in per_event if e["status"] == TP and e["tta"] is not None]
    deadline = float(cfg.get("tta_deadline_s", 30.0) if cfg else 30.0)
    within = [t for t in ttas if 0 <= t <= deadline]
    tta_stats = {
        "n": len(ttas),
        "mean": round(mean(ttas), 3) if ttas else None,
        "p50": round(percentile(ttas, 0.5), 3) if ttas else None,
        "p90": round(percentile(ttas, 0.9), 3) if ttas else None,
        "max": round(max(ttas), 3) if ttas else None,
        "deadline_s": deadline,
        "deadline_recall": round(len(within) / total_events, 4) if total_events else None,
        "detected_on_time_fraction": round(len(within) / len(ttas), 4) if ttas else None,
        "missed_events": total_events - tp_events,
        "negative_latency_events": sum(t < 0 for t in ttas),
        "start": "条件成立（阈值满足）时刻",
    }

    # 第二口径：从事件起点（首次可见）到卡片显示。它包含规程等待，不能与处理截止直接比较。
    tta_ev = [e["tta_event_start"] for e in per_event
              if e["status"] == TP and e["tta_event_start"] is not None]
    tta_event_stats = {
        "n": len(tta_ev),
        "mean": round(mean(tta_ev), 3) if tta_ev else None,
        "p50": round(percentile(tta_ev, 0.5), 3) if tta_ev else None,
        "p90": round(percentile(tta_ev, 0.9), 3) if tta_ev else None,
        "max": round(max(tta_ev), 3) if tta_ev else None,
        "deadline_s": None,
        "deadline_recall": None,
        "start": "事件起点（首次可见）",
        "note": ("含规程等待（阈值延迟），不与处理截止直接比较；"
                 "系统处理时延请看 tta（阈值满足→告警）。"),
    }
    # 阈值延迟：仅对提供了 satisfy_ts 的事件计算，解释两个口径的差值
    delays = [max(0.0, ev.condition_ts - ev.start) for ev in events if ev.satisfy_ts > 0]
    threshold_delay = {
        "n": len(delays),
        "p50": round(percentile(delays, 0.5), 3) if delays else None,
        "max": round(max(delays), 3) if delays else None,
        "note": "超时停留类事件的规程等待（事件起点到条件成立），不是系统处理时延。",
    }

    localization = localization_metrics(matching["matched"], events, alarms, cfg)

    per_camera = []
    for camera_id, hours in sorted(camera_hours.items()):
        cam_events = [e for e in per_event if e["camera_id"] == camera_id]
        cam_alarms = [a for a in displayed if a.camera_id == camera_id]
        cam_fa = [a for a in merged_fa if a.camera_id == camera_id]
        per_camera.append({
            "camera_id": camera_id,
            "valid_hours": round(hours, 4),
            "events": len(cam_events),
            "tp": sum(1 for e in cam_events if e["status"] == TP),
            "displayed_alarms": len(cam_alarms),
            "false_alarms": len(cam_fa),
            "fa_per_camera_hour": round(safe_div(len(cam_fa), hours), 4) if hours else None,
        })

    frame_auc = float("nan")
    if frame_scores:
        labels = [int(x[0]) for x in frame_scores]
        scores = [float(x[1]) for x in frame_scores]
        frame_auc = roc_auc(labels, scores)

    result = {
        "camera_hours": round(total_camera_hours, 4),
        "events": total_events,
        "event_recall": round(strict_recall, 4) if total_events else None,
        "event_recall_incl_deferred": round(recall_incl_deferred, 4) if total_events else None,
        "event_tp_confirmed": tp_confirmed,
        "event_tp_displayed": tp_events,
        "event_missed": total_events - tp_events,
        "displayed_alarms": len(displayed),
        "confirmed_alarms": len(displayed) - len([a for a in displayed if a.status == "deferred"]),
        "deferred_alarms": len([a for a in displayed if a.status == "deferred"]),
        "suppressed_alarms": len([a for a in alarms if a.status == "suppressed"]),
        "precision": round(precision, 4),
        "false_alarms": len(merged_fa),
        "false_alarms_raw": len(matching["false_alarms"]),
        "duplicate_alarms": matching["duplicate_alarms"],
        "fa_merge_gap_s": merge_gap,
        "false_alarms_per_camera_hour": round(fa_per_ch, 4) if fa_per_ch is not None else None,
        "tta": tta_stats,
        "tta_event_start": tta_event_stats,
        "threshold_delay": threshold_delay,
        "localization": localization,
        "frame_roc_auc": None if math.isnan(frame_auc) else round(frame_auc, 4),
        "per_event": per_event,
        "per_camera": per_camera,
        "events_detail": [e.to_dict() for e in events],
        "alarms_detail": [a.to_dict() for a in alarms],
        "matching_rule": {
            "pre_tolerance_s": float(cfg.get("event_match", {}).get("pre_tolerance_s", 5.0)) if cfg else 5.0,
            "post_tolerance_s": float(cfg.get("event_match", {}).get("post_tolerance_s", 20.0)) if cfg else 20.0,
            "interval_iou": float(cfg.get("event_match", {}).get("interval_iou", 0.3)) if cfg else 0.3,
            "one_to_one": True,
            "trigger_based": True,
        },
        "evaluable_video_hours": round(total_camera_hours, 4),
        "sample_size_warning": _sample_warning(total_events, total_camera_hours, cfg),
    }
    if extra:
        result.update(extra)
    return result


def _sample_warning(events: int, camera_hours: float, cfg: dict) -> str:
    """小样本提示：避免"试跑通过"被当成"普遍部署效果"。"""
    need = int(cfg.get("sample_size_warning_below", 20) if cfg else 20)
    if events < need:
        return (f"本结果基于 {events} 个事件 / {camera_hours:.1f} 机位·小时，"
                f"低于建议的 {need} 个事件：只能验证流程，不能据此声称普遍部署效果。")
    return ""


# --------------------------------------------------------------------------- 定位精度


def localization_metrics(matched: Sequence[tuple[str, str, float]],
                         events: Sequence[GtEvent], alarms: Sequence[AlarmRecord],
                         cfg: dict) -> dict:
    """定位边界误差，**与事件存在性判定分开统计**。

    只统计已命中、真值提供 `evidence_span`、且告警带 Stage2 证据区间的事件。
    同时给出两套误差：

      * **raw**：告警证据区间 vs 真值完整证据区间 —— 反映端到端差距；
      * **causal reference**：告警证据区间 vs "可观测参考区间"
        `[max(span0, t_trigger − W), min(span1, t_trigger)]`，
        即只要求它在因果窗口 W 内对齐，反映"在可观测范围内定位准不准"。

    两套都报，是因为长时事件的 raw 误差被窗口上限结构性放大
    （35 分钟滞留不可能用 60 秒窗口完整覆盖），只看 raw 会误判定位能力。
    """
    loc_cfg = (cfg or {}).get("localization", {}) or {}
    tol = float(loc_cfg.get("tolerance_s", 5.0))
    window_s = float((cfg or {}).get("fsm.history_window_s", 60.0))
    by_alarm = {a.alarm_id: a for a in alarms}
    by_event = {e.event_id: e for e in events}

    start_err: list[float] = []
    end_err: list[float] = []
    ref_start_err: list[float] = []
    ref_end_err: list[float] = []
    truncation: list[float] = []
    mious: list[float] = []
    ref_mious: list[float] = []
    coverages: list[float] = []
    precisions: list[float] = []
    misses: list[float] = []
    rows: list[dict] = []
    hit = 0
    ref_hit = 0

    for alarm_id, event_id, iou in matched:
        ev = by_event.get(event_id)
        alarm = by_alarm.get(alarm_id)
        if ev is None or alarm is None or not alarm.interval or not ev.evidence_span:
            continue
        span0, span1 = float(ev.evidence_span[0]), float(ev.evidence_span[1])
        a0 = float(alarm.interval.get("start", 0.0))
        a1 = float(alarm.interval.get("end", 0.0))
        trigger = float(alarm.t_trigger)
        # 可观测参考区间：真值证据区间 ∩ [触发时刻-窗口, 触发时刻]
        ref0 = max(span0, trigger - window_s)
        ref1 = min(span1, trigger)
        if ref1 <= ref0:  # 极端情形（触发早于证据区间）退化为原始区间
            ref0, ref1 = span0, span1
        s_err = a0 - span0
        e_err = a1 - span1
        ref_s_err = a0 - ref0
        ref_e_err = a1 - ref1
        trunc = max(0.0, span1 - a1)
        ref_iou = interval_iou((a0, a1), (ref0, ref1))
        inter = max(0.0, min(a1, ref1) - max(a0, ref0))
        ref_cov = inter / max(1e-9, ref1 - ref0)      # 覆盖了多少应看的证据
        a_len = max(1e-9, a1 - a0)
        ref_prec = inter / a_len                      # 声称的区间里有多少被真值支持
        start_err.append(s_err)
        end_err.append(e_err)
        ref_start_err.append(ref_s_err)
        ref_end_err.append(ref_e_err)
        truncation.append(trunc)
        mious.append(iou)
        ref_mious.append(ref_iou)
        coverages.append(ref_cov)
        precisions.append(ref_prec)
        misses.append(max(0.0, span0 - a0))
        ok = abs(s_err) <= tol and abs(e_err) <= tol
        ok_ref = abs(ref_s_err) <= tol and abs(ref_e_err) <= tol
        hit += int(ok)
        ref_hit += int(ok_ref)
        rows.append({
            "event_id": event_id,
            "alarm_id": alarm_id,
            "evidence_span": [round(span0, 3), round(span1, 3)],
            "causal_reference": [round(ref0, 3), round(ref1, 3)],
            "alarm_interval": [round(a0, 3), round(a1, 3)],
            "start_error_s": round(s_err, 3),
            "end_error_s": round(e_err, 3),
            "end_truncation_s": round(trunc, 3),
            "ref_start_error_s": round(ref_s_err, 3),
            "ref_end_error_s": round(ref_e_err, 3),
            "iou": round(iou, 4),
            "ref_iou": round(ref_iou, 4),
            "within_tolerance": ok,
            "within_tolerance_ref": ok_ref,
        })

    n = len(rows)
    skipped = len(matched) - n
    return {
        "n": n,
        "tolerance_s": tol,
        "window_limit_s": window_s,
        "start_bias_s": round(mean(start_err), 3) if start_err else None,
        "start_mae_s": round(mean([abs(v) for v in start_err]), 3) if start_err else None,
        "end_bias_s": round(mean(end_err), 3) if end_err else None,
        "end_mae_s": round(mean([abs(v) for v in end_err]), 3) if end_err else None,
        "ref_start_bias_s": round(mean(ref_start_err), 3) if ref_start_err else None,
        "ref_start_mae_s": round(mean([abs(v) for v in ref_start_err]), 3)
        if ref_start_err else None,
        "ref_end_bias_s": round(mean(ref_end_err), 3) if ref_end_err else None,
        "ref_end_mae_s": round(mean([abs(v) for v in ref_end_err]), 3)
        if ref_end_err else None,
        "end_truncation_p50_s": round(percentile(truncation, 0.5), 3) if truncation else None,
        "start_miss_max_s": round(max(misses), 3) if misses else None,
        "miou_mean": round(mean(mious), 4) if mious else None,
        "ref_miou_mean": round(mean(ref_mious), 4) if ref_mious else None,
        "ref_coverage_mean": round(mean(coverages), 4) if coverages else None,
        "ref_precision_mean": round(mean(precisions), 4) if precisions else None,
        "coverage_minmax": [round(min(coverages), 4), round(max(coverages), 4)]
        if coverages else None,
        "boundary_hit_rate": round(hit / n, 4) if n else None,
        "ref_boundary_hit_rate": round(ref_hit / n, 4) if n else None,
        "skipped_matched_without_span": skipped,
        "per_event": rows,
        "note": ("只统计已命中且真值提供 evidence_span 的事件；与事件存在性判定分开。"
                 "raw 误差对比完整证据区间，长时事件会被因果窗口上限结构性放大；"
                 "causal reference 误差对比可观测参考区间，反映窗口内定位能力。"),
    }


# --------------------------------------------------------------------------- 拒识率


def no_event_rejection(negatives: Sequence[dict]) -> dict:
    """无事件拒识率：在已确认的"无事件窗口"上，静默抑制的比例。

    negatives 每项形如 {"decision": "NO_EVENT"|"EVENT"|"INSUFFICIENT_EVIDENCE"|"SYSTEM_ERROR",
                        "silent": bool}
    """
    total = len(negatives)
    if total == 0:
        return {"windows": 0, "silent": 0, "rejection_rate": None,
                "ci95": None, "uncertain": 0, "system_error": 0}
    silent = sum(1 for n in negatives if n.get("silent"))
    uncertain = sum(1 for n in negatives if n.get("decision") == "INSUFFICIENT_EVIDENCE")
    sys_err = sum(1 for n in negatives if n.get("decision") == "SYSTEM_ERROR")
    lo, hi = wilson_interval(silent, total)
    return {
        "windows": total,
        "silent": silent,
        "rejection_rate": round(silent / total, 4),
        "ci95": [round(lo, 4), round(hi, 4)],
        "uncertain": uncertain,
        "system_error": sys_err,
        "alarmed": total - silent - uncertain - sys_err,
    }
