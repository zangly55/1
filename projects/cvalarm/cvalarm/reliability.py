"""串联系统的条件召回率与漏报归因。

论文 3.4 节的公式：

    p_total = p(E1 ∩ E2 ∩ E3 | Event)
            = p1 × p2|1 × p3|1,2

其中 p1 是前筛保留率、p2|1 是定位保留率、p3|1,2 是复核确证率。
必须沿事件在各级的保留情况计算——过滤比例本身不能代替可靠性。
"""
from __future__ import annotations

from typing import Sequence

from .types import AlarmRecord, Candidate, GtEvent, Stage2Result
from .metrics import match_alarms
from .util import safe_div, wilson_interval


def conditional_recall(events: Sequence[GtEvent], candidates: Sequence[Candidate],
                       stage2_by_candidate: dict[str, Stage2Result],
                       alarms: Sequence[AlarmRecord], cfg: dict | None = None) -> dict:
    """按事件统计各级保留情况，给出条件概率乘积与瓶颈归因。"""
    confirmed = [a for a in alarms if a.status == "confirmed"]
    stage3_matches = match_alarms(events, confirmed, cfg or {})["matched"]
    by_alarm = {a.alarm_id:a for a in confirmed}
    # Reserve surviving paths first, then allocate earlier-stage candidates once.
    stage3 = {eid:by_alarm[aid].candidate_id for aid,eid,_ in stage3_matches}
    def earlier_matches(seed, eligible):
        found = dict(seed)
        used = set(seed.values())
        proxies = [
            AlarmRecord(c.candidate_id,c.candidate_id,c.camera_id,c.track_id,
                        c.roi_id,c.event_class,c.t_trigger,c.t_trigger,c.t_trigger,
                        "confirmed","EVENT",
                        interval=({"start":stage2_by_candidate[c.candidate_id].interval[0],
                                   "end":stage2_by_candidate[c.candidate_id].interval[1]}
                                  if c.candidate_id in stage2_by_candidate and
                                  stage2_by_candidate[c.candidate_id].interval else None))
            for c in eligible if c.candidate_id not in used]
        matched = match_alarms([e for e in events if e.event_id not in found], proxies, cfg or {})["matched"]
        found.update({eid:aid for aid,eid,_ in matched})
        return found
    stage2 = earlier_matches(stage3,[c for c in candidates
                                    if c.candidate_id in stage2_by_candidate
                                    and stage2_by_candidate[c.candidate_id].decision == "EVENT"])
    stage1 = earlier_matches(stage2,candidates)
    per_event: list[dict] = []
    n = len(events)
    p1_num = p2_num = p3_num = 0

    for ev in events:
        kept1 = ev.event_id in stage1
        kept2 = ev.event_id in stage2
        kept3 = ev.event_id in stage3
        p1_num += int(kept1)
        p2_num += int(kept2 and kept1)
        p3_num += int(kept3)
        per_event.append({
            "event_id": ev.event_id,
            "camera_id": ev.camera_id,
            "stage1_candidates": int(kept1),
            "stage2_event": int(kept2),
            "stage3_displayed": int(kept3),
            "kept_stage1": kept1,
            "kept_stage2": kept2 and kept1,
            "kept_stage3": kept3,
            "lost_at": _lost_at(kept1, kept2, kept3),
        })

    p1 = safe_div(p1_num, n) if n else None
    p2_given_1 = safe_div(p2_num, p1_num) if p1_num else None
    p3_given_12 = safe_div(p3_num, p2_num) if p2_num else None
    product = (p1 or 0.0) * (p2_given_1 or 0.0) * (p3_given_12 or 0.0)
    actual = safe_div(p3_num, n) if n else None

    factors = {"p1_prefilter": p1, "p2_given_1_localizer": p2_given_1,
               "p3_given_12_verifier": p3_given_12}
    bottleneck = None
    known = {k: v for k, v in factors.items() if v is not None}
    if known:
        bottleneck = min(known, key=lambda k: known[k])

    ci = wilson_interval(p3_num, n) if n else (0.0, 1.0)
    return {
        "events": n,
        "p1_prefilter": p1,
        "p2_given_1_localizer": p2_given_1,
        "p3_given_12_verifier": p3_given_12,
        "p_total_independent_estimate": round(product, 4) if n else None,
        "conditional_chain_product": round(product, 4) if n else None,
        "end_to_end_recall_observed": round(actual, 4) if actual is not None else None,
        "end_to_end_recall_ci95": [round(ci[0], 4), round(ci[1], 4)],
        "bottleneck": bottleneck,
        "per_event": per_event,
        "note": ("同一批事件的一对一保留路径；条件概率乘积遵循链式法则，不需要独立性假设。"
                 "仅确证计入末级召回。旧字段 independent_estimate 为兼容别名。"),
    }


def _lost_at(kept1: bool, kept2: bool, kept3: bool) -> str:
    if kept3:
        return "none"
    if not kept1:
        return "stage1_prefilter"
    if not kept2:
        return "stage2_localizer"
    return "stage3_verifier"


def _overlaps(a0: float, a1: float, b0: float, b1: float, pad: float = 20.0) -> bool:
    return max(a0, b0 - pad) <= min(a1, b1 + pad)
