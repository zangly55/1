"""Stage3 多模态证据核验：结构化告警卡片、四类交互架构、可插拔 VLM 适配器。

论文第 5 章与表 2 的工程化落地：
  * baseline           单模型直接生成（配合提示与约束解码）——延迟/算力基线
  * cot_selfcheck      单模型 CoT 逐步自检——记录每步思维 Token 与等待时间
  * role_pipeline      观察员 → 合规分析员 → 复核员 三角色流水线——上游文本顺传
  * adversarial_falsifier 独立证伪对抗——辩护者上下文隔离，只找反驳证据

治理边界（本实现强制，不交给模型自由裁量）：
  1. Temporal_Anchor、event_class、evidence_chain 由系统按观测填写；
     模型不得改写时间锚点与事件类别，避免时间戳/类别幻觉。
  2. 规程适用结论（alarm / suppress / escalate）由外部规则引擎给出；
     模型只负责"画面事实与未决事项"的核验与表述。
  3. 模型输出必须通过 JSON Schema 校验；不合格即修复一次，仍失败则回退规则核验，
     并在卡片 uncertainties 里记录"模型输出未通过校验"。
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional

from .card import (CARD_JSON_SCHEMA, new_card_id, sign_card, validate_card)
from .config import Config
from .evidence import build_evidence
from .rules import RuleDecision, RuleEngine
from .types import Candidate, FrameFeature, Stage2Result
from .util import clamp, get_logger, mean, now_iso, read_json

LOG = get_logger("cvalarm.stage3")

CONFIRM = "confirm"
DISMISS = "dismiss"
UNCERTAIN = "uncertain"

PERSON_ASPECT_REF = 2.6


class VLMEndpointError(RuntimeError):
    """VLM 端点不可用或返回不可解析内容。"""


# --------------------------------------------------------------------------- 外部授权


@dataclass
class AuthorizationBook:
    """外部非视觉记录（作业许可等）。必须与画面事实分开核验。"""

    path: str = ""
    permits: list[dict] = field(default_factory=list)
    available: bool = True
    complete: bool = True  # constructors may explicitly represent a complete test fixture
    updated_at: str = ""
    error: str = ""
    data_kind: str = ""

    @classmethod
    def load(cls, path: str) -> "AuthorizationBook":
        if not path or not os.path.exists(path):
            return cls(path=path, available=False, error="授权记录文件不存在")
        data = read_json(path, default=None)
        if data is None:
            return cls(path=path, available=False, error="授权记录不是合法 JSON")
        return cls(
            path=path,
            permits=list(data.get("permits", [])),
            available=True,
            complete=bool(data.get("complete", False)),
            data_kind=str(data.get("data_kind", "")),
            updated_at=str(data.get("updated_at", "")),
        )

    def lookup(self, camera_id: str, roi_id: str, t0: float, t1: float,
               event_class: str) -> dict:
        """返回授权覆盖情况：覆盖率、命中的许可与责任人。"""
        if not self.available:
            return {"authorized": False, "coverage": 0.0, "permit_id": None,
                    "reason": "外部授权系统不可达，无法核验规程适用性"}
        span = max(1e-6, t1 - t0)
        best: Optional[dict] = None
        best_cov = 0.0
        for permit in self.permits:
            if str(permit.get("camera_id", "")) not in (camera_id, "*"):
                continue
            if str(permit.get("roi_id", "")) not in (roi_id, "*"):
                continue
            scope = permit.get("scope", ["*"])
            if "*" not in scope and event_class not in scope:
                continue
            p0 = float(permit.get("start", 0.0))
            p1 = float(permit.get("end", 0.0))
            overlap = max(0.0, min(t1, p1) - max(t0, p0))
            cov = overlap / span
            if cov > best_cov:
                best_cov = cov
                best = permit
        authorized = best_cov >= 0.9
        return {
            "authorized": authorized,
            "coverage": round(best_cov, 4),
            "permit_id": (best or {}).get("permit_id"),
            "holder": (best or {}).get("holder", ""),
            "kind": (best or {}).get("kind", ""),
            "reason": "" if authorized else (
                "未查到覆盖该时段的作业许可" if best_cov <= 0.0 else
                f"作业许可仅覆盖 {best_cov:.0%} 的滞留时段，超出部分仍按违规处理"),
        }


# --------------------------------------------------------------------------- 结果


@dataclass
class VerificationResult:
    decision: str
    card: dict
    action: str
    mode: str
    tokens: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)
    fallback_used: bool = False

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "action": self.action,
            "mode": self.mode,
            "tokens": self.tokens,
            "fallback_used": self.fallback_used,
            "card": self.card,
            "details": self.details,
        }


# --------------------------------------------------------------------------- 上下文


def build_context(candidate: Candidate, stage2: Stage2Result,
                  features: list[FrameFeature], auth: AuthorizationBook,
                  extra: Optional[dict] = None,
                  validity_cfg: Optional[dict] = None) -> dict:
    """汇总规则引擎所需的全部字段（字段缺失会被规则求值器显式记录）。"""
    t0, t1 = stage2.interval or candidate.window
    window_features = [f for f in features if t0 <= f.ts <= t1] or features
    aspect = mean([f.mean_person_aspect for f in window_features if f.mean_person_aspect > 0]) \
        if window_features else 0.0
    # 置信度与运动能量优先取状态机记录的"该目标"数值：
    # 帧级 max_score 会把同帧内其它目标的高分算进来，导致伪目标被高估。
    snapshot = candidate.snapshot or {}
    det_score = (float(snapshot["mean_det_score"]) if snapshot.get("mean_det_score") is not None
                 else (mean([f.max_score for f in window_features]) if window_features else 0.0))
    motion = (float(snapshot["motion_energy"]) if snapshot.get("motion_energy") is not None
              else (mean([f.motion for f in window_features]) if window_features else 0.0))
    validity = stage2.validity or {}
    vcfg = validity_cfg or {}
    min_snr = float(vcfg.get("min_snr", 12.0))
    max_drop = float(vcfg.get("max_dropped_ratio", 0.15))
    max_occ = float(vcfg.get("max_occlusion_ratio", 0.7))
    occluded = float(validity.get("occluded_ratio", 0.0))
    occlusion_explained = bool(validity.get("occlusion_explained"))
    visibility_ok = (
        float(validity.get("mean_snr", 99.0)) >= min_snr
        and float(validity.get("dropped_ratio", 0.0)) <= max_drop
        and (occluded <= max_occ or occlusion_explained)
    )
    auth_info = auth.lookup(candidate.camera_id, candidate.roi_id,
                            candidate.t_enter, candidate.t_trigger, candidate.event_class)
    continuity = candidate.continuity or {}
    ctx = {
        "camera_id": candidate.camera_id,
        "roi_id": candidate.roi_id,
        "track_id": candidate.track_id,
        "event_class": candidate.event_class,
        "dwell_seconds": float(candidate.accum_s),
        "dwell_threshold_s": float(candidate.dwell_threshold_s),
        "in_roi": True,
        "visibility_ok": bool(visibility_ok),
        "mean_det_score": round(det_score, 4),
        "motion_energy": round(motion, 4),
        "mean_aspect": round(aspect, 3),
        "continuity_verified": bool(continuity.get("continuous_verified", True)),
        "suspension_gap_s": round(sum(g.get("delta_s", 0.0) for g in continuity.get("gaps", [])), 3),
        "authorized": bool(auth_info["authorized"]),
        "authorization_coverage": auth_info["coverage"],
        "permit_id": auth_info["permit_id"],
        "external_records_available": auth.available,
        "authorization_known": auth.available and (auth.complete or bool(auth_info["authorized"])),
        "recent_duplicate_count": 0,
    }
    if extra:
        ctx.update(extra)
    return ctx


# --------------------------------------------------------------------------- 卡片组装


def _keyframes(features: list[FrameFeature], interval: tuple[float, float],
               limit: int = 3) -> list[int]:
    if not features:
        return []
    start, end = interval
    picks: list[FrameFeature] = []
    for target in (start, (start + end) / 2.0, end):
        best = min(features, key=lambda f: abs(f.ts - target))
        picks.append(best)
    seen: set[int] = set()
    out: list[int] = []
    for f in picks:
        if f.frame_idx not in seen:
            seen.add(f.frame_idx)
            out.append(f.frame_idx)
    return out[:limit]


def compose_card(candidate: Candidate, stage2: Stage2Result, features: list[FrameFeature],
                 context: dict, decision: RuleDecision, confidence: float,
                 narrator: Optional[dict] = None, cfg=None,
                 scene: Optional[dict] = None,
                 provenance: Optional[dict] = None) -> dict:
    """组装卡片。时间锚点、事件类别、证据链全部由系统写入。"""
    interval = stage2.interval or candidate.window
    frames = [f for f in features if interval[0] <= f.ts <= interval[1]] or features
    keyframes = _keyframes(frames, interval)
    continuity = candidate.continuity or {}
    gaps = continuity.get("gaps", [])
    aspect = float(context.get("mean_aspect", 0.0) or 0.0)
    det_score = float(context.get("mean_det_score", 0.0))
    uncertainties: list[str] = []

    facts: list[dict] = [
        {
            "fact": f"目标（track {candidate.track_id}）落脚锚点位于防区 {candidate.roi_id} 多边形内",
            "frame": keyframes[0] if keyframes else 0,
            "source": "detector+tracker+roi",
        },
        {
            "fact": (f"累计在场 {candidate.accum_s:.1f} 秒，"
                     f"达到 {candidate.dwell_threshold_s:.0f} 秒阈值"),
            "frame": keyframes[-1] if keyframes else 0,
            "source": "fsm.dwell_timer",
        },
    ]
    if gaps:
        gap_desc = "、".join(
            f"[{g['t_lost']:.1f}s→{g['t_resume']:.1f}s] 中断 {g['delta_s']:.1f}s" for g in gaps)
        facts.append({
            "fact": f"期间发生观测中断 {len(gaps)} 次：{gap_desc}（策略 {continuity.get('policy')}）",
            "frame": keyframes[0] if keyframes else 0,
            "source": "fsm.occlusion_state5",
        })
        uncertainties.append(
            f"累计时长由 {len(gaps)} 段观测间隔拼接而成，跨未知间隔的累加不能证明严格连续滞留")
    if aspect and abs(aspect - PERSON_ASPECT_REF) / PERSON_ASPECT_REF > 0.35:
        facts.append({
            "fact": f"目标包围框高宽比 {aspect:.2f}，与人员典型形态（约 {PERSON_ASPECT_REF}）差异明显",
            "frame": keyframes[-1] if keyframes else 0,
            "source": "stage2.size_consistency",
        })
        uncertainties.append("目标形态异常，可能存在静止物体/反光被误识别为人员")
    facts.append({
        "fact": (f"证据区间内检测置信度均值 {det_score:.2f}，"
                 f"信噪比 {float(context.get('mean_snr', 0.0) or stage2.validity.get('mean_snr', 0)):.1f}，"
                 f"遮挡比例 {float(stage2.validity.get('occluded_ratio', 0.0)):.0%}"),
        "frame": keyframes[-1] if keyframes else 0,
        "source": "stage2.validity",
    })

    if context.get("authorized"):
        uncertainties.append(
            f"外部记录：许可 {context.get('permit_id')}（{context.get('_holder', '')}）"
            f"覆盖 {float(context.get('authorization_coverage', 0.0)):.0%} 的滞留时段，"
            f"视觉事实成立但不构成违规")
    elif not context.get("external_records_available"):
        uncertainties.append("外部授权系统不可达，规程适用性未能核验")
    else:
        uncertainties.append(f"未查到覆盖该时段的作业许可：{context.get('_auth_reason', '')}".strip("："))
    if not context.get("visibility_ok", True):
        uncertainties.append("可见性不足（低照度/遮挡），无法辨认胸卡、工装或作业标识")
    if narrator and narrator.get("uncertainties"):
        for item in narrator["uncertainties"]:
            if item not in uncertainties:
                uncertainties.append(item)

    basis_text = decision.description or "按规则集判定"
    if not context.get("continuity_verified", True):
        basis_text += "；结论为累计在场，不作为连续滞留认定"
    if narrator and narrator.get("basis"):
        basis_text = f"{basis_text}；模型核验：{narrator['basis']}"

    card = {
        "card_id": new_card_id(candidate.candidate_id),
        "alarm_id": candidate.candidate_id,
        "camera_id": candidate.camera_id,
        "event_class": candidate.event_class,
        "Temporal_Anchor": {
            "start": round(float(interval[0]), 3),
            "end": round(float(interval[1]), 3),
            "keyframes": keyframes,
            "dwell_seconds": round(float(candidate.accum_s), 3),
            "t_enter": round(float(candidate.t_enter), 3),
            "t_trigger": round(float(candidate.t_trigger), 3),
        },
        "Physical_Fact_Evidence": facts,
        "Normative_Inference_Uncertainty": {
            "norm_ref": decision.norm_ref or "（未匹配规程，按默认策略转人工）",
            "basis": basis_text,
            "uncertainties": [u for u in uncertainties if u],
        },
        "confidence": round(clamp(confidence, 0.01, 0.99), 3),
        "decision": _decision_of(decision.action),
        "evidence_chain": {
            "candidate_id": candidate.candidate_id,
            "roi_id": candidate.roi_id,
            "track_id": candidate.track_id,
            "t_enter": round(float(candidate.t_enter), 3),
            "t_trigger": round(float(candidate.t_trigger), 3),
            "accum_s": round(float(candidate.accum_s), 3),
            "stage2": {
                "decision": stage2.decision,
                "interval": [round(float(interval[0]), 3), round(float(interval[1]), 3)],
                "score": stage2.raw_score,
                "tau_confirm": stage2.tau_confirm,
                "tau_reject": stage2.tau_reject,
                "calibration_ok": stage2.calibration_ok,
                "validity": stage2.validity,
            },
            "continuity": continuity,
            "flags": list(candidate.flags),
            "rule": decision.to_dict(),
            "external_records": {
                "available": bool(context.get("external_records_available")),
                "permit_id": context.get("permit_id"),
                "coverage": context.get("authorization_coverage", 0.0),
            },
        },
        "rule_version": "",
        "created_at": now_iso(),
    }
    # 证据回放：片段 + 必要前后文 + 关键帧（重绘示意图）+ 媒体入口
    if candidate.event_class.startswith("UNAUTHORIZED_") and not context.get("authorization_known", False):
        card["decision"] = "uncertain"
        card["Normative_Inference_Uncertainty"]["uncertainties"].append(
            "授权状态未知：外部记录不可用或覆盖不完整，只确认可见事实")
    if cfg is not None:
        try:
            rois = (scene or {}).get(candidate.camera_id, []) or []
            card["evidence"] = build_evidence(cfg, candidate, interval, rois)
        except Exception as exc:  # 证据构造失败不能阻断告警
            LOG.warning("证据回放构造失败（%s）：%s", candidate.candidate_id, exc)
            card["evidence"] = {"enabled": False, "reason": str(exc)}
    # 溯源：本卡片由哪条链路生成、数据来自哪里，禁止把回放结果说成现场推理
    if provenance:
        card["provenance"] = dict(provenance)
        card["provenance"]["generated_at"] = card["created_at"]
    errors = validate_card(card)
    if errors:
        LOG.warning("卡片结构自检未通过（%s）：%s", candidate.candidate_id, "; ".join(errors))
    return card


def _decision_of(action: str) -> str:
    return {"alarm": CONFIRM, "suppress": DISMISS}.get(action, UNCERTAIN)


def _confidence_of(candidate: Candidate, stage2: Stage2Result, context: dict,
                   decision: RuleDecision) -> float:
    visibility = 1.0 if context.get("visibility_ok", True) else 0.35
    continuity = 1.0 if context.get("continuity_verified", True) else 0.75
    det = clamp(float(context.get("mean_det_score", 0.0)), 0.0, 1.0)
    base = 0.45 * clamp(stage2.raw_score, 0.0, 1.0) + 0.25 * det + 0.15 * visibility + 0.15 * continuity
    aspect = float(context.get("mean_aspect", 0.0) or 0.0)
    if aspect and abs(aspect - PERSON_ASPECT_REF) / PERSON_ASPECT_REF > 0.35:
        base -= 0.18
    if decision.action == "suppress":
        base = clamp(0.5 + 0.5 * float(context.get("authorization_coverage", 0.0)), 0.0, 0.99)
    if decision.action == "alarm" and not context.get("continuity_verified", True):
        base = min(base, 0.7)
    return clamp(base, 0.05, 0.97)


# --------------------------------------------------------------------------- 规则核验（离线参考）


def make_provenance(base: Optional[dict], verifier_label: str, mode: str) -> dict:
    """溯源信息：区分"离线回放验证/现场推理"与"规则基线/模型端点"。"""
    prov = dict(base or {})
    prov.setdefault("pipeline", "cvalarm")
    prov["verifier"] = verifier_label
    prov["verifier_mode"] = mode
    return prov


class RuleBasedVerifier:
    """离线参考核验器：不依赖任何模型权重，用于自测、回归与等预算基线。"""

    mode = "rule_based"

    def __init__(self, cfg: Config, engine: RuleEngine, auth: AuthorizationBook,
                 scene: Optional[dict] = None,
                 provenance: Optional[dict] = None) -> None:
        self.cfg = cfg
        self.engine = engine
        self.auth = auth
        self.scene = scene or {}
        self.provenance = provenance or {}
        self.event_classes = list(cfg.get("stage3.event_classes", []))

    def verify(self, candidate: Candidate, stage2: Stage2Result,
               features: list[FrameFeature]) -> VerificationResult:
        t0 = time.perf_counter()
        context = build_context(candidate, stage2, features, self.auth,
                                validity_cfg=self.cfg.get("stage2.validity", {}))
        auth_info = self.auth.lookup(candidate.camera_id, candidate.roi_id,
                                    candidate.t_enter, candidate.t_trigger,
                                    candidate.event_class)
        context["_holder"] = auth_info.get("holder", "")
        context["_auth_reason"] = auth_info.get("reason", "")
        decision = self.engine.evaluate(candidate.event_class, context)
        confidence = _confidence_of(candidate, stage2, context, decision)
        card = compose_card(candidate, stage2, features, context, decision, confidence,
                            cfg=self.cfg, scene=self.scene,
                            provenance=make_provenance(self.provenance,
                                                       "rule_based_reference", self.mode))
        card = sign_card(card) if self.cfg.get("deployment.privacy.sign_cards", True) else card
        errors = validate_card(card, self.event_classes)
        return VerificationResult(
            decision=card["decision"],
            card=card,
            action={"confirm":"alarm", "dismiss":"suppress", "uncertain":"escalate"}[card["decision"]],
            mode=self.mode,
            tokens={"input": 0, "output": 0, "total": 0},
            details={
                "context": _public_context(context),
                "card_errors": errors,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "rule": decision.to_dict(),
            },
        )


def _public_context(context: dict) -> dict:
    return {k: v for k, v in context.items() if not k.startswith("_")}


# --------------------------------------------------------------------------- VLM 适配


Transport = Callable[[list[dict], dict], tuple[str, dict]]


def _default_transport(cfg: Config) -> Transport:
    vlm = cfg.section("stage3").get("vlm", {}) or {}
    endpoint = str(vlm.get("endpoint", "") or "")
    model = str(vlm.get("model", "") or "")
    timeout = float(vlm.get("timeout_s", 30))
    key_env = str(vlm.get("api_key_env", "CVALARM_VLM_API_KEY"))
    temperature = float(vlm.get("temperature", 0.0))

    def post(messages: list[dict], schema: dict) -> tuple[str, dict]:
        if not endpoint:
            raise VLMEndpointError(
                "未配置 stage3.vlm.endpoint：请设置 OpenAI 兼容的 /chat/completions 端点，"
                "或保持 stage3.verifier=rule_based 使用离线参考核验器")
        api_key = os.environ.get(key_env, "")
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": int(cfg.get("stage3.max_tokens", 512)),
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "alarm_card", "strict": True, "schema": schema},
            },
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=data, method="POST",
            headers={"Content-Type": "application/json",
                     **({"Authorization": f"Bearer {api_key}"} if api_key else {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise VLMEndpointError(f"VLM 调用失败：{exc}") from exc
        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise VLMEndpointError(f"VLM 响应结构异常：{payload}") from exc
        usage = payload.get("usage", {}) or {}
        if not isinstance(text, str) or not isinstance(usage, dict):
            raise VLMEndpointError("VLM content 必须是文本，usage 必须是对象")
        return text, {
            "input": int(usage.get("prompt_tokens", 0)),
            "output": int(usage.get("completion_tokens", 0)),
            "total": int(usage.get("total_tokens", 0)),
        }

    return post


def extract_json(text: str) -> dict:
    """从模型输出中抽出第一个 JSON 对象（容忍 ```json 围栏与前后废话）。"""
    if not isinstance(text, str) or not text:
        raise VLMEndpointError("模型返回空内容或非文本内容")
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```")[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    while start >= 0:
        depth = 0
        for idx in range(start, len(stripped)):
            ch = stripped[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(stripped[start:idx + 1])
                    except json.JSONDecodeError:
                        break
        start = stripped.find("{", start + 1)
    raise VLMEndpointError("模型输出中找不到合法 JSON 对象")


class LLMVerifier:
    """四类交互架构的统一实现（等预算对比的载体）。"""

    def __init__(self, cfg: Config, engine: RuleEngine, auth: AuthorizationBook,
                 mode: str = "baseline", transport: Optional[Transport] = None,
                 scene: Optional[dict] = None,
                 provenance: Optional[dict] = None) -> None:
        self.cfg = cfg
        self.engine = engine
        self.auth = auth
        self.mode = mode if mode in ("baseline", "cot_selfcheck", "role_pipeline",
                                     "adversarial_falsifier") else "baseline"
        self.transport = transport or _default_transport(cfg)
        self.scene = scene or {}
        self.provenance = provenance or {}
        self.event_classes = list(cfg.get("stage3.event_classes", []))
        self.budget = int(cfg.get("stage3.token_budget", 2600))
        from .visual import visual_frames
        self.frame_provider = lambda candidate, stage2: visual_frames(cfg, candidate, stage2)
        self._active_frames = []

    # ------------------------------------------------------------------ 提示词
    def _evidence_brief(self, candidate: Candidate, stage2: Stage2Result,
                        context: dict) -> str:
        gaps = (candidate.continuity or {}).get("gaps", [])
        lines = [
            f"摄像头 {candidate.camera_id}，防区 {candidate.roi_id}，轨迹 {candidate.track_id}",
            f"系统测得：累计在场 {candidate.accum_s:.1f}s（阈值 {candidate.dwell_threshold_s:.0f}s），"
            f"t_enter={candidate.t_enter:.1f}s，t_trigger={candidate.t_trigger:.1f}s",
            f"定位区间 [{stage2.interval[0]:.1f}, {stage2.interval[1]:.1f}]s，"
            f"区间均分 {stage2.raw_score:.3f}（τ_confirm={stage2.tau_confirm:.3f}）",
            f"证据可用性：信噪比 {stage2.validity.get('mean_snr', 0):.1f}，"
            f"丢帧比例 {stage2.validity.get('dropped_ratio', 0):.1%}，"
            f"遮挡比例 {stage2.validity.get('occluded_ratio', 0):.1%}",
            f"检测置信度均值 {context.get('mean_det_score', 0):.2f}，"
            f"运动能量 {context.get('motion_energy', 0):.3f}，"
            f"人员框高宽比 {context.get('mean_aspect', 0):.2f}",
        ]
        if gaps:
            lines.append("观测中断：" + "；".join(
                f"{g['delta_s']:.1f}s@{g['t_lost']:.1f}s" for g in gaps))
        if context.get("authorized"):
            lines.append(f"外部记录：许可 {context.get('permit_id')} 覆盖 "
                         f"{context.get('authorization_coverage', 0):.0%} 时段")
        else:
            lines.append(f"外部记录：{context.get('_auth_reason', '未查到许可')}")
        return "\n".join(lines)

    def _system_prompt(self) -> str:
        return (
            "你是视频监控异常告警的证据核验员。只依据给定观测做判断，"
            "严禁虚构画面内容或时间戳。输出必须是一个 JSON 对象，"
            "字段为 card_id、alarm_id、camera_id、event_class、Temporal_Anchor、"
            "Physical_Fact_Evidence、Normative_Inference_Uncertainty、confidence、decision。"
            "Temporal_Anchor 必须使用给定区间，write 事实时区分「画面可见事实」与「规程推断」。"
        )

    # ------------------------------------------------------------------ 各架构
    def verify(self, candidate: Candidate, stage2: Stage2Result,
               features: list[FrameFeature]) -> VerificationResult:
        t0 = time.perf_counter()
        context = build_context(candidate, stage2, features, self.auth,
                                validity_cfg=self.cfg.get("stage2.validity", {}))
        auth_info = self.auth.lookup(candidate.camera_id, candidate.roi_id,
                                    candidate.t_enter, candidate.t_trigger,
                                    candidate.event_class)
        context["_holder"] = auth_info.get("holder", "")
        context["_auth_reason"] = auth_info.get("reason", "")
        decision = self.engine.evaluate(candidate.event_class, context)
        brief = self._evidence_brief(candidate, stage2, context)

        tokens = {"input": 0, "output": 0, "total": 0}
        narrator: dict = {}
        fallback = False
        self._request_tokens = dict(tokens)
        self._request_count = 0
        self._active_frames = []
        try:
            self._active_frames = self.frame_provider(candidate, stage2)
            if not self._active_frames:
                raise ValueError("没有真实视觉证据")
            if self.mode == "cot_selfcheck":
                narrator, used = self._run_cot(brief)
            elif self.mode == "role_pipeline":
                narrator, used = self._run_roles(brief)
            elif self.mode == "adversarial_falsifier":
                narrator, used = self._run_adversarial(brief)
            else:
                narrator, used = self._run_baseline(brief)
            if narrator.get("camera_id") != candidate.camera_id or narrator.get("event_class") != candidate.event_class:
                raise ValueError("模型输出的机位或事件类别与候选不一致")
            frame_ids = {f["frame_idx"] for f in self._active_frames}
            references = list(narrator["Temporal_Anchor"].get("keyframes", []))
            references.extend(f.get("frame") for f in narrator.get("Physical_Fact_Evidence", []))
            if any(not isinstance(f, int) or f not in frame_ids for f in references):
                raise ValueError("模型引用了未提供的视觉证据帧")
            anchor = narrator["Temporal_Anchor"]
            if not candidate.window[0] <= anchor["start"] <= anchor["end"] <= candidate.t_trigger:
                raise ValueError("模型时间锚点超出已到达证据窗口")
        except (VLMEndpointError, ValueError, OSError, KeyError, TypeError) as exc:
            LOG.warning("VLM 核验失败（%s），保留规则证据并转人工：%s", self.mode, exc)
            fallback = True
            narrator = {
                "uncertainties": [f"模型核验失败，保留规则证据并转人工（{exc}）"],
                "basis": "",
            }

        tokens = dict(self._request_tokens)
        confidence = _confidence_of(candidate, stage2, context, decision)
        if narrator.get("confidence") is not None:
            try:
                model_conf = float(narrator["confidence"])
                confidence = clamp(0.6 * confidence + 0.4 * model_conf, 0.05, 0.97)
            except (TypeError, ValueError):
                pass
        card = compose_card(candidate, stage2, features, context, decision, confidence,
                            narrator=narrator, cfg=self.cfg, scene=self.scene,
                            provenance=make_provenance(
                                self.provenance, f"vlm_endpoint:{self.mode}", self.mode))
        card["model_input_frames"] = [{k:v for k,v in f.items() if k != "url"}
                                      for f in self._active_frames]
        if fallback:
            card["decision"] = "uncertain"
            card["model_status"] = "failed"
        else:
            card["model_result"] = narrator
            model_decision = narrator.get("decision", "uncertain")
            rule_decision = card["decision"]
            card["decision"] = model_decision if model_decision == rule_decision else "uncertain"
            card["model_status"] = "completed"
            card["Physical_Fact_Evidence"].extend(narrator.get("Physical_Fact_Evidence", []))
            model_norm = narrator.get("Normative_Inference_Uncertainty", {})
            norms = card["Normative_Inference_Uncertainty"]
            norms["uncertainties"].extend(model_norm.get("uncertainties", []))
            norms["basis"] += "；模型依据：" + str(model_norm.get("basis", ""))
            if model_decision != rule_decision:
                norms["uncertainties"].append(
                    f"模型与规则冲突：模型={model_decision}，规则={rule_decision}，转人工")
        card["verifier"] = {"mode": self.mode, "tokens": tokens, "fallback": fallback,
                            "http_attempts":self._request_count}
        card = sign_card(card) if self.cfg.get("deployment.privacy.sign_cards", True) else card
        return VerificationResult(
            decision=card["decision"],
            card=card,
            action={"confirm":"alarm", "dismiss":"suppress", "uncertain":"escalate"}[card["decision"]],
            mode=self.mode,
            tokens=tokens,
            fallback_used=fallback,
            details={
                "context": _public_context(context),
                "rule": decision.to_dict(),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "budget": self.budget,
                "card_errors": validate_card(card, self.event_classes),
            },
        )

    def _run_baseline(self, brief: str) -> tuple[dict, dict]:
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": brief + "\n\n请给出结构化卡片。"},
        ]
        return self._call_and_parse(messages)

    def _run_cot(self, brief: str) -> tuple[dict, dict]:
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": (
                brief + "\n\n请先逐步自检：(1) 时间锚点是否与观测一致；(2) 画面事实是否都有帧号依据；"
                "(3) 是否存在把规程推断写成画面事实的情况；(4) 未决事项是否列全。"
                "自检完再输出 JSON 卡片。")},
        ]
        return self._call_and_parse(messages)

    def _run_roles(self, brief: str) -> tuple[dict, dict]:
        tokens = {"input": 0, "output": 0, "total": 0}
        observer_msgs = [
            {"role": "system", "content": "你是观察员。只描述画面可直接支持的事实，不写规程判断。"},
            {"role": "user", "content": brief + "\n\n列出画面事实清单，每条附帧号。"},
        ]
        observer_text, used = self._post(observer_msgs)
        tokens = _accum(tokens, used)
        compliance_msgs = [
            {"role": "system", "content": "你是合规分析员。依据给定规程判断适用性，并指出未决事项。"},
            {"role": "user", "content": brief + f"\n\n观察员事实清单：\n{observer_text}"},
        ]
        compliance_text, used = self._post(compliance_msgs)
        tokens = _accum(tokens, used)
        final_msgs = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": (
                brief + f"\n\n观察员事实：\n{observer_text}\n\n合规分析：\n{compliance_text}\n\n"
                "复核并按 schema 输出卡片 JSON。")},
        ]
        narrator, used = self._call_and_parse(final_msgs)
        return narrator, _accum(tokens, used)

    def _run_adversarial(self, brief: str) -> tuple[dict, dict]:
        """独立证伪：辩护者不读取主审的指控文本，只找反驳线索。"""
        tokens = {"input": 0, "output": 0, "total": 0}
        defender_msgs = [
            {"role": "system", "content": (
                "你是独立证伪者。你的任务不是认同告警，而是寻找能反驳异常判断的画面线索，"
                "例如临时访客吊牌、例行维修标志、保洁作业特征。上下文与主审隔离，"
                "只依据给定观测，不要臆测主审结论。")},
            {"role": "user", "content": brief + "\n\n请列出可能反驳「违规滞留」的线索，"
                                                 "并说明每条线索的证据强度（强/中/弱）。"},
        ]
        defense_text, used = self._post(defender_msgs)
        tokens = _accum(tokens, used)
        judge_msgs = [
            {"role": "system", "content": self._system_prompt() + (
                " 现在你是主审：必须同时考虑指控证据与反驳证据；"
                "若反驳线索指向明确画面，把 decision 设为 uncertain 并列入未决事项。")},
            {"role": "user", "content": (
                brief + f"\n\n独立证伪者的反驳线索：\n{defense_text}\n\n"
                "综合双方证据，按 schema 输出卡片 JSON。")},
        ]
        narrator, used = self._call_and_parse(judge_msgs)
        narrator.setdefault("uncertainties", [])
        if defense_text and "反驳" in defense_text:
            narrator["uncertainties"].append("存在反驳线索，已列入人工复核依据")
        return narrator, _accum(tokens, used)

    # ------------------------------------------------------------------ 调用
    def _post(self, messages: list[dict]) -> tuple[str, dict]:
        messages = [dict(m) for m in messages]
        for message in messages:
            if message.get("role") == "user":
                message["content"] = [{"type":"text", "text":str(message["content"])}]
                for frame in self._active_frames:
                    message["content"].extend([
                        {"type":"text", "text":f"frame={frame['frame_idx']}, t={frame['ts']:.3f}s"},
                        {"type":"image_url", "image_url":{"url":frame["url"]}}])
                break
        self._request_count += 1
        text, usage = self.transport(messages, CARD_JSON_SCHEMA)
        if not isinstance(usage, dict):
            raise VLMEndpointError("模型用量必须是对象")
        self._request_tokens = _accum(self._request_tokens, usage)
        return text, usage

    def _call_and_parse(self, messages: list[dict]) -> tuple[dict, dict]:
        text, usage = self._post(messages)
        try:
            parsed = extract_json(text)
            errors = validate_card(parsed, self.event_classes)
            if errors:
                raise ValueError("; ".join(errors))
            return parsed, usage
        except (VLMEndpointError, ValueError) as exc:
            repair = messages + [
                {"role": "assistant", "content": text[:2000]},
                {"role": "user", "content": (
                    f"上面的输出未通过 JSON Schema 校验：{exc}。"
                    "请只输出符合 schema 的 JSON，不要任何解释。")},
            ]
            text2, usage2 = self._post(repair)
            parsed = extract_json(text2)
            errors = validate_card(parsed, self.event_classes)
            if errors:
                raise ValueError("修复后仍不合法：" + "; ".join(errors))
            return parsed, _accum(usage, usage2)


def _accum(a: dict, b: dict) -> dict:
    return {k: int(a.get(k, 0)) + int(b.get(k, 0)) for k in ("input", "output", "total")}


# --------------------------------------------------------------------------- 门面


class VerifierEngine:
    """Stage3 门面：按配置选择核验器，统一输出 VerificationResult。"""

    def __init__(self, cfg: Config, engine: RuleEngine, auth: AuthorizationBook,
                 transport: Optional[Transport] = None,
                 scene: Optional[dict] = None,
                 provenance: Optional[dict] = None) -> None:
        self.cfg = cfg
        self.rules = engine
        self.auth = auth
        self.scene = scene or {}
        self.provenance = provenance or {}
        kind = str(cfg.get("stage3.verifier", "rule_based"))
        mode = str(cfg.get("stage3.mode", "baseline"))
        self.kind = kind
        if kind == "vlm":
            self.impl = LLMVerifier(cfg, engine, auth, mode=mode, transport=transport,
                                    scene=self.scene, provenance=self.provenance)
        else:
            self.impl = RuleBasedVerifier(cfg, engine, auth, scene=self.scene,
                                          provenance=self.provenance)
        self.gpu_ms = 0.0
        self.calls = 0
        self.decisions: dict[str, int] = {CONFIRM: 0, DISMISS: 0, UNCERTAIN: 0}

    @property
    def mode(self) -> str:
        return getattr(self.impl, "mode", self.kind)

    def verify(self, candidate: Candidate, stage2: Stage2Result,
               features: list[FrameFeature]) -> VerificationResult:
        self.calls += 1
        result = self.impl.verify(candidate, stage2, features)
        # 依据配置把 Stage3 的 GPU 时间折算进成本模型
        per_s = float(self.cfg.get("cost.stage.stage3_gpu_ms_per_input_s", 900.0))
        span = max(0.0, (stage2.interval[1] - stage2.interval[0]) if stage2.interval else 0.0)
        self.gpu_ms += per_s * max(1.0, span)
        self.decisions[result.decision] = self.decisions.get(result.decision, 0) + 1
        return result
