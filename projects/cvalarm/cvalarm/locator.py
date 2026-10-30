"""Stage2 时间定位与无事件拒识。

两条彼此独立的职责（论文第 4 章）：
  1) 定位：从 30~60 秒粗窗口里解出证据区间 [t_start, t_end]。
     本模块用"非自回归区间打分 + Kadane 动态规划"复现 VideoJev 式解码：
     各候选区间得分一次算出，最佳连续区间由 O(K) 的 Kadane 解码得到，
     不做逐 Token 自回归生成。
  2) 存在性：Kadane 默认返回**非空**区间，无事件窗口里它仍会挑一个最高分片段，
     因此定位之后必须外挂事件存在性校验，并按"没发生 / 看不清 / 采集中断"
     三向分流（论文 4.2、4.3 节）。

打分头是可替换的：生产环境把 `HeuristicScorer` 换成 VideoJev 的轻量时序打分头
（或通过 ExternalSeriesScorer 灌入外部分数），其余分流逻辑不变。
"""
from __future__ import annotations

import math
import os
import json
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Optional, Protocol

from .config import Config
from .types import Candidate, FrameFeature, Stage2Result
from .util import clamp, content_hash, get_logger, mean, now_iso, read_json, write_json

LOG = get_logger("cvalarm.stage2")

EVENT = "EVENT"
NO_EVENT = "NO_EVENT"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
SYSTEM_ERROR = "SYSTEM_ERROR"


@dataclass
class Bin:
    t0: float
    t1: float
    occupancy: float = 0.0
    dwell_progress: float = 0.0
    motion: float = 0.0
    det_score: float = 0.0
    size_consistency: float = 0.0
    score: float = 0.0
    ok: bool = True
    snr: float = 99.0
    frames: int = 0

    def to_dict(self) -> dict:
        return {
            "t0": round(self.t0, 3),
            "t1": round(self.t1, 3),
            "score": round(self.score, 4),
            "occupancy": round(self.occupancy, 4),
            "dwell_progress": round(self.dwell_progress, 4),
            "motion": round(self.motion, 4),
            "det_score": round(self.det_score, 4),
            "size_consistency": round(self.size_consistency, 4),
            "ok": self.ok,
            "snr": round(self.snr, 2),
            "frames": self.frames,
        }


class IntervalScorer(Protocol):
    """时序打分头接口：返回每个 bin 的匹配概率（越大越可能包含目标事件）。"""

    name: str

    def score(self, candidate: Candidate, bins: list[Bin]) -> list[float]: ...


class HeuristicScorer:
    """离线参考打分头：把可解释证据（占用、停留进度、运动、检测分、形态）线性合成。

    生产替换点：用一个 VideoJev 风格的轻量打分头替换本类即可，
    输入是同一批 bin 特征，输出是每个 bin 的匹配概率。
    """

    name = "heuristic-reference"

    def __init__(self, weights: dict) -> None:
        self.w = {
            "roi_occupancy": float(weights.get("roi_occupancy", 0.34)),
            "dwell_progress": float(weights.get("dwell_progress", 0.24)),
            "motion": float(weights.get("motion", 0.14)),
            "det_score": float(weights.get("det_score", 0.16)),
            "size_consistency": float(weights.get("size_consistency", 0.12)),
        }
        total = sum(self.w.values()) or 1.0
        self.w = {k: v / total for k, v in self.w.items()}

    def score(self, candidate: Candidate, bins: list[Bin]) -> list[float]:
        out: list[float] = []
        threshold = max(1e-6, candidate.dwell_threshold_s)
        is_audit = "audit_sample" in (candidate.flags or [])
        for b in bins:
            # 抽样窗口没有轨迹锚点，停留进度不可观测，按 0 计（不虚构滞留证据）
            dwell_progress = 0.0 if is_audit else clamp(
                (b.t1 - candidate.t_enter) / threshold, 0.0, 1.0)
            val = (
                self.w["roi_occupancy"] * clamp(b.occupancy, 0.0, 1.0)
                + self.w["dwell_progress"] * dwell_progress
                + self.w["motion"] * clamp(b.motion / 0.5, 0.0, 1.0)
                + self.w["det_score"] * clamp(b.det_score, 0.0, 1.0)
                + self.w["size_consistency"] * clamp(b.size_consistency, 0.0, 1.0)
            )
            out.append(clamp(val, 0.0, 1.0))
        return out


class ExternalSeriesScorer:
    """外部打分序列适配器：从 JSON 载入 {camera_id: [[ts, prob], ...]}。

    用途：把真实 VideoJev / 其它时序打分模型的输出灌进来，做等口径对比与回归。
    """

    name = "external-series"

    def __init__(self, path: str) -> None:
        data = read_json(path, default=None)
        if not isinstance(data, dict) or not data:
            raise ValueError("外部定位分数文件缺失、为空或格式无效")
        self.series: dict[str, list[tuple[float, float]]] = {}
        for cam, points in data.items():
            self.series[cam] = sorted((float(t), float(p)) for t, p in points)

    def score(self, candidate: Candidate, bins: list[Bin]) -> list[float]:
        points = self.series.get(candidate.camera_id) or []
        if not points:
            raise ValueError(f"外部定位分数缺少机位 {candidate.camera_id}")
        out: list[float] = []
        times = [p[0] for p in points]
        vals = [p[1] for p in points]
        for b in bins:
            t = (b.t0 + b.t1) / 2.0
            idx = _nearest(times, t)
            out.append(clamp(vals[idx], 0.0, 1.0))
        return out


class HttpScorer:
    """Project-defined scoring contract; the external service owns VideoJev inference."""
    name = "http-temporal-scorer"

    def __init__(self, cfg):
        self.cfg = cfg
        self.endpoint = str(cfg.get("stage2.scorer.endpoint", ""))
        if not self.endpoint:
            raise ValueError("HTTP 定位器缺少 endpoint")

    def score(self, candidate, bins):
        from .visual import visual_frames
        from types import SimpleNamespace
        frames = visual_frames(self.cfg, candidate, SimpleNamespace(interval=candidate.window))
        query = self.cfg.get("stage2.scorer.queries", {}).get(candidate.event_class, candidate.event_class)
        body = {"schema_version":1, "candidate_id":candidate.candidate_id, "query":query,
                "camera_id":candidate.camera_id, "window":list(candidate.window),
                "available_until":candidate.t_trigger, "frames":frames,
                "bins":[{"start":b.t0,"end":b.t1} for b in bins]}
        headers = {"Content-Type":"application/json"}
        key = os.environ.get(str(self.cfg.get("stage2.scorer.api_key_env", "CVALARM_LOCALIZER_API_KEY")), "")
        if key:
            headers["Authorization"] = "Bearer " + key
        request = urllib.request.Request(self.endpoint, json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=float(self.cfg.get("stage2.scorer.timeout_s",30))) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("定位服务响应必须是 JSON 对象")
        scores = data.get("scores")
        if not isinstance(scores,list) or len(scores) != len(bins):
            raise ValueError("定位服务必须为每个请求 bin 返回一个分数")
        scores = [float(s) for s in scores]
        if any(not math.isfinite(s) or not 0 <= s <= 1 for s in scores):
            raise ValueError("定位服务分数必须是有限的 [0,1] 数值")
        return scores


def _nearest(sorted_times: list[float], t: float) -> int:
    lo, hi = 0, len(sorted_times) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_times[mid] < t:
            lo = mid + 1
        else:
            hi = mid
    if lo > 0 and abs(sorted_times[lo - 1] - t) <= abs(sorted_times[lo] - t):
        return lo - 1
    return lo


# --------------------------------------------------------------------------- 解码


def kadane(adjusted: Iterable[float]) -> tuple[int, int, float]:
    """最大子段和（非空区间）。返回 (start_idx, end_idx, best_sum)。

    论文 4.2 节：由于区间必须非空，无事件窗口仍会返回一个"相对最高分"片段，
    这正是需要外挂存在性校验的原因。
    """
    best = -math.inf
    best_start = best_end = 0
    cur = 0.0
    cur_start = 0
    for i, value in enumerate(adjusted):
        if cur <= 0.0:
            cur = value
            cur_start = i
        else:
            cur += value
        if cur > best:
            best = cur
            best_start = cur_start
            best_end = i
    if not math.isfinite(best):
        return (0, 0, 0.0)
    return (best_start, best_end, best)


# --------------------------------------------------------------------------- 标定


@dataclass
class Calibration:
    """低分拒识的标定产物：同场景硬负样本上的分数分布。"""

    version: str = "uncalibrated"
    tau_reject: float = 0.25
    tau_confirm: float = 0.55
    hard_negative_windows: int = 0
    hard_negative_q995: float = 0.0
    created_at: str = ""
    context: str = ""

    @property
    def is_ok(self) -> bool:
        return self.hard_negative_windows > 0 and self.version != "uncalibrated"

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "tau_reject": round(self.tau_reject, 4),
            "tau_confirm": round(self.tau_confirm, 4),
            "hard_negative_windows": self.hard_negative_windows,
            "hard_negative_q995": round(self.hard_negative_q995, 4),
            "created_at": self.created_at,
            "is_ok": self.is_ok,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Calibration":
        return cls(
            version=str(data.get("version", "uncalibrated")),
            tau_reject=float(data.get("tau_reject", 0.25)),
            tau_confirm=float(data.get("tau_confirm", 0.55)),
            hard_negative_windows=int(data.get("hard_negative_windows", 0)),
            hard_negative_q995=float(data.get("hard_negative_q995", 0.0)),
            created_at=str(data.get("created_at", "")),
            context=str(data.get("context", "")),
        )


def calibrate(negative_scores: Iterable[float], min_negatives: int,
              confirm_gap: float = 0.18) -> Calibration:
    """用同场景硬负样本的分位数确定拒识阈值。

    论文 4.3 节强调：低分拒识只有在"画面清晰有效 + 机制已在同场景硬负例上校准"
    时才能支撑"确认无事件"的结论；因此标定产物必须记录负例数量与版本。
    """
    scores = sorted(float(s) for s in negative_scores)
    if len(scores) < max(1, min_negatives):
        return Calibration(
            version="uncalibrated",
            tau_reject=0.25,
            tau_confirm=0.55,
            hard_negative_windows=len(scores),
            hard_negative_q995=_quantile(scores, 0.995) if scores else 0.0,
            created_at=now_iso(),
        )
    q = _quantile(scores, 0.995)
    tau_reject = clamp(q * 1.05 + 0.02, 0.05, 0.9)
    tau_confirm = clamp(tau_reject + confirm_gap, tau_reject + 0.02, 0.99)
    version = content_hash({"q": round(q, 6), "n": len(scores), "tau": round(tau_reject, 6)})
    return Calibration(
        version=f"cal-{version}",
        tau_reject=tau_reject,
        tau_confirm=tau_confirm,
        hard_negative_windows=len(scores),
        hard_negative_q995=q,
        created_at=now_iso(),
    )


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = clamp(q, 0.0, 1.0) * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _calibration_path(cfg: Config) -> str:
    """标定产物路径：跟随 runtime.state_dir（与规则、反馈保持同一状态根）。"""
    artifact = str(cfg.get("stage2.calibration.artifact", "state/calibration.json"))
    if os.path.isabs(artifact):
        return artifact
    state_dir = cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
    rel = artifact[len("state/"):] if artifact.startswith("state/") else artifact
    return os.path.join(state_dir, rel)


def load_calibration(cfg: Config) -> Calibration:
    path = _calibration_path(cfg)
    data = read_json(path, default=None)
    if not data:
        return Calibration()
    cal = Calibration.from_dict(data)
    expected = cfg.get("runtime.calibration_context", "")
    if expected and cal.context != expected:
        cal.version = "uncalibrated"
        cal.tau_reject = float(cfg.get("stage2.tau_reject", 0.25))
        cal.tau_confirm = float(cfg.get("stage2.tau_confirm", 0.55))
    need = int(cfg.get("stage2.calibration.require_hard_negatives", 20))
    if cal.hard_negative_windows < need:
        LOG.debug("标定负例不足（%d < %d），低分拒识降级为人工复核",
                  cal.hard_negative_windows, need)
        cal.version = "uncalibrated"
        cal.tau_reject = float(cfg.get("stage2.tau_reject", 0.25))
        cal.tau_confirm = float(cfg.get("stage2.tau_confirm", 0.55))
    return cal


def save_calibration(cfg: Config, cal: Calibration) -> str:
    if not cal.context:
        cal.context = str(cfg.get("runtime.calibration_context", ""))
    path = _calibration_path(cfg)
    write_json(path, cal.to_dict())
    return path


# --------------------------------------------------------------------------- 主逻辑


class Localizer:
    """Stage2：定位 + 存在性校验 + 三向分流。"""

    def __init__(self, cfg: Config, scorer: Optional[IntervalScorer] = None,
                 calibration: Optional[Calibration] = None) -> None:
        self.cfg = cfg
        self.bin_seconds = float(cfg.get("stage2.bin_seconds", 1.0))
        self.weights = cfg.get("stage2.weights", {}) or {}
        self.validity = cfg.get("stage2.validity", {}) or {}
        self.scorer: IntervalScorer = scorer or load_scorer(cfg) or HeuristicScorer(self.weights)
        self.cal = calibration or load_calibration(cfg)
        self.processed_s = 0.0
        self.gpu_ms = 0.0
        self.decisions: dict[str, int] = {EVENT: 0, NO_EVENT: 0, INSUFFICIENT: 0, SYSTEM_ERROR: 0}

    # ------------------------------------------------------------------ 打分特征
    def build_bins(self, candidate: Candidate, features: list[FrameFeature]) -> list[Bin]:
        t0, t1 = candidate.window
        if t1 <= t0:
            t1 = t0 + self.bin_seconds
        n = max(1, int(math.ceil((t1 - t0) / self.bin_seconds)))
        bins: list[Bin] = []
        roi_id = candidate.roi_id
        for i in range(n):
            b0 = t0 + i * self.bin_seconds
            b1 = min(t1, b0 + self.bin_seconds)
            members = [f for f in features if b0 <= f.ts < b1] or \
                      [f for f in features if b0 <= f.ts <= b1]
            b = Bin(t0=b0, t1=b1, frames=len(members))
            if members:
                b.occupancy = mean([clamp(m.roi_persons.get(roi_id, 0.0), 0.0, 1.0)
                                    for m in members])
                b.motion = mean([m.motion for m in members])
                b.det_score = mean([m.max_score for m in members])
                aspects = [m.mean_person_aspect for m in members if m.mean_person_aspect > 0]
                aspect = mean(aspects) if aspects else 0.0
                b.size_consistency = clamp(1.0 - abs(aspect - 2.6) / 2.6, 0.0, 1.0) if aspect else 0.0
                ok_members = [m for m in members if m.ok]
                b.ok = len(ok_members) / max(1, len(members)) >= 0.5
                snrs = [m.snr for m in ok_members]
                b.snr = mean(snrs) if snrs else 0.0
            else:
                b.ok = False
                b.snr = 0.0
            bins.append(b)
        return bins

    # ------------------------------------------------------------------ 主流程
    def run(self, candidate: Candidate, features: list[FrameFeature]) -> Stage2Result:
        bins = self.build_bins(candidate, features)
        try:
            scores = self.scorer.score(candidate, bins)
            if len(scores) != len(bins) or any(not math.isfinite(float(s)) or not 0 <= float(s) <= 1 for s in scores):
                raise ValueError("定位器必须返回每个 bin 的有效概率")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.decisions[SYSTEM_ERROR] += 1
            reason = f"定位服务失败：{type(exc).__name__}"
            return Stage2Result(SYSTEM_ERROR, None, 0, 0, self.cal.tau_confirm,
                                self.cal.tau_reject, 0,
                                validity={"valid":False, "scorer_error":reason},
                                reasons=[reason], calibration_ok=self.cal.is_ok)
        for b, s in zip(bins, scores):
            b.score = float(s)
        # 抽样审计窗口里没有目标轨迹，"占用率缺失"不是遮挡，不能按证据不足处理
        is_audit = "audit_sample" in (candidate.flags or [])

        window_s = max(1e-6, candidate.window[1] - candidate.window[0])
        self.processed_s += window_s
        per_s = float(self.cfg.get("cost.stage.stage2_gpu_ms_per_candidate_s", 45.0))
        self.gpu_ms += per_s * window_s

        # ---------------------------------------------------------- 1) 有效性
        # 丢帧比例按**帧级**统计（bin 内一半帧可用即算可用，会把 50% 丢帧抹平）
        window_frames = [f for f in features if candidate.window[0] <= f.ts <= candidate.window[1]]
        total_frames = len(window_frames) or 1
        dropped = sum(1 for f in window_frames if not f.ok) / total_frames
        valid_bins = [b for b in bins if b.ok and b.frames > 0]
        mean_snr = mean([b.snr for b in valid_bins]) if valid_bins else 0.0
        # 遮挡只统计"状态机认定目标应在场"之后的 bin：
        # 历史窗口前段本来就不该有目标，算进去会把正常候选误判成看不清。
        present_from = float(candidate.t_enter)
        present_bins = [b for b in bins if b.t1 > present_from] or bins
        occluded_ratio = sum(1 for b in present_bins if b.occupancy <= 0.001) / max(1, len(present_bins))
        stale = all(b.occupancy <= 0.001 for b in present_bins)  # 窗口内从未见过目标
        max_drop = float(self.validity.get("max_dropped_ratio", 0.15))
        min_snr = float(self.validity.get("min_snr", 12.0))
        max_occ = float(self.validity.get("max_occlusion_ratio", 0.7))
        min_valid_bins = int(self.validity.get("min_valid_bins", 3))
        # 状态机已完成身份关联的遮挡间隔不按"看不清"降级：
        # 占用率缺失已被可审计的轨迹元数据解释（论文 3.2 节 State5）。
        occlusion_explained = bool((candidate.continuity or {}).get("gaps"))

        validity = {
            "dropped_ratio": round(dropped, 4),
            "mean_snr": round(mean_snr, 3),
            "occluded_ratio": round(occluded_ratio, 4),
            "occlusion_explained": occlusion_explained,
            "stale": stale,
            "valid_bins": len(valid_bins),
            "window_s": round(window_s, 3),
            "valid": True,
            "reasons": [],
        }
        reasons: list[str] = []
        if dropped > max_drop:
            validity["valid"] = False
            reasons.append(f"丢帧比例 {dropped:.1%} > {max_drop:.0%}（采集中断，非事件不存在）")
        if len(valid_bins) < min_valid_bins:
            validity["valid"] = False
            reasons.append(f"有效 bin 数 {len(valid_bins)} < {min_valid_bins}")
        if mean_snr < min_snr and valid_bins:
            reasons.append(f"信噪比 {mean_snr:.1f} < {min_snr:.1f}（低照度/遮挡）")
        if occluded_ratio > max_occ and not occlusion_explained and not is_audit:
            reasons.append(f"遮挡比例 {occluded_ratio:.1%} > {max_occ:.0%}")
        elif occluded_ratio > max_occ and occlusion_explained:
            reasons.append(
                f"遮挡比例 {occluded_ratio:.1%}，但身份关联已完成（累计时长不含中断间隔）")

        # ---------------------------------------------------------- 2) 非自回归解码
        tau_reject = self.cal.tau_reject
        adjusted = [b.score - tau_reject for b in bins]
        start, end, best_sum = kadane(adjusted)
        interval = (bins[start].t0, bins[end].t1) if bins else (candidate.window[0], candidate.window[1])
        span_scores = [b.score for b in bins[start:end + 1]]
        interval_score = mean(span_scores) if span_scores else 0.0

        # ---------------------------------------------------------- 3) 三向分流
        decision, triage_reasons = self._triage(
            validity, validity["valid"], reasons, interval_score,
            dropped=dropped, max_drop=max_drop, mean_snr=mean_snr, min_snr=min_snr,
            occluded_ratio=occluded_ratio, max_occ=max_occ, is_audit=is_audit,
            stale=stale,
        )
        self.decisions[decision] = self.decisions.get(decision, 0) + 1

        result = Stage2Result(
            decision=decision,
            interval=interval,
            score=round(interval_score - tau_reject, 4),
            raw_score=round(interval_score, 4),
            tau_confirm=self.cal.tau_confirm,
            tau_reject=self.cal.tau_reject,
            margin=round(interval_score - self.cal.tau_confirm, 4),
            bins=[b.to_dict() for b in bins],
            validity=validity,
            reasons=triage_reasons,
            calibration_ok=self.cal.is_ok,
        )
        return result

    def _triage(self, validity: dict, valid: bool, reasons: list[str],
                score: float, dropped: float, max_drop: float,
                mean_snr: float, min_snr: float,
                occluded_ratio: float, max_occ: float,
                is_audit: bool = False, stale: bool = False) -> tuple[str, list[str]]:
        """按"采集中断 → 看不清 → 目标是否在场 → 有/无事件"的优先级分流。

        顺序不可颠倒：把观测失败写成"正常无事"，就是把"没看见"混同于"没发生"。
        """
        notes: list[str] = []
        if dropped > max_drop:
            notes.append("采集中断：丢帧超限，转入系统异常与重检队列")
            return SYSTEM_ERROR, notes + reasons
        if mean_snr < min_snr and validity.get("valid_bins", 0) > 0:
            notes.append("证据不足：信噪比过低，结论不可用，挂起交人工复核")
            return INSUFFICIENT, notes + reasons
        if stale:
            # 窗口内从未观察到目标：候选已过期（目标离开/被完全遮挡且无身份关联）
            if self.cal.is_ok:
                notes.append("无事件：窗口内始终未观察到目标，候选过期，静默抑制")
                return NO_EVENT, notes
            notes.append("未决：窗口内未观察到目标，但拒识机制未标定，转人工")
            return INSUFFICIENT, notes
        if occluded_ratio > max_occ and not is_audit \
                and not validity.get("occlusion_explained", False):
            notes.append("证据不足：遮挡比例过高，无法确认目标是否为同一对象")
            return INSUFFICIENT, notes + reasons
        if not valid:
            notes.append("证据不足：窗口有效性检查未通过")
            return INSUFFICIENT, notes + reasons

        if score >= self.cal.tau_confirm:
            notes.append(f"存在性成立：区间均分 {score:.3f} ≥ τ_confirm {self.cal.tau_confirm:.3f}")
            return EVENT, notes
        if score >= self.cal.tau_reject:
            if self.cal.is_ok:
                notes.append(
                    f"未决：{self.cal.tau_reject:.3f} ≤ 均分 {score:.3f} < "
                    f"τ_confirm {self.cal.tau_confirm:.3f}，挂起观察/交人工")
                return INSUFFICIENT, notes
            notes.append("未决：拒识阈值未完成同场景硬负例标定，低分不足以支撑静默抑制")
            return INSUFFICIENT, notes
        # 低分区：只有在标定充分时才允许"确认无事件"
        if self.cal.is_ok:
            notes.append(f"无事件：均分 {score:.3f} < τ_reject {self.cal.tau_reject:.3f}（已标定）")
            return NO_EVENT, notes
        notes.append("未决：均分低于阈值但拒识机制未标定，按证据不足处理")
        return INSUFFICIENT, notes


def load_scorer(cfg: Config) -> Optional[IntervalScorer]:
    kind = str(cfg.get("stage2.scorer.kind", "heuristic"))
    if kind == "http":
        return HttpScorer(cfg)
    if kind == "external":
        path = cfg.resolve(str(cfg.get("stage2.scorer.path", "")))
        if not path:
            raise ValueError("stage2.scorer.kind=external 时必须提供 stage2.scorer.path")
        return ExternalSeriesScorer(path)
    if kind != "heuristic":
        raise ValueError(f"未知定位器：{kind}")
    return None
