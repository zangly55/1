"""结构化预警卡片：固定字段、结构校验、证据链、签名。

论文 5.2 节要求卡片对值班人员"可迅速查到依据"、对软件"字段稳定可解析"，
因此字段固定为四项核心内容：

    1. Event_Class                     预设安防枚举表中的事件名称
    2. Temporal_Anchor                 绝对起止时间戳 [t_start, t_end] 及关键帧编号
    3. Physical_Fact_Evidence          画面直接支持的动作事实（不得混入规程推断）
    4. Normative_Inference_Uncertainty 所用规程、判断依据与未决事项

格式合法只说明结构符合约定，事实正确性仍需另作核查（论文原话）。
签名只证明"签名之后的内容未被改动"，不证明签名前画面真实（论文 7.3 节）。
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

from .util import canonical_json, get_logger, now_iso, sha256_hex

LOG = get_logger("cvalarm.card")

REQUIRED_FIELDS = (
    "card_id",
    "alarm_id",
    "camera_id",
    "event_class",
    "Temporal_Anchor",
    "Physical_Fact_Evidence",
    "Normative_Inference_Uncertainty",
    "decision",
)

DECISIONS = ("confirm", "dismiss", "uncertain")

_WARNED_INSECURE = False

#: JSON Schema（用于 OpenAI 兼容接口的约束解码）
CARD_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": list(REQUIRED_FIELDS),
    "properties": {
        "card_id": {"type": "string"},
        "alarm_id": {"type": "string"},
        "camera_id": {"type": "string"},
        "event_class": {"type": "string"},
        "Temporal_Anchor": {
            "type": "object",
            "additionalProperties": False,
            "required": ["start", "end", "keyframes"],
            "properties": {
                "start": {"type": "number"},
                "end": {"type": "number"},
                "keyframes": {"type": "array", "items": {"type": "integer"}},
                "dwell_seconds": {"type": "number"},
            },
        },
        "Physical_Fact_Evidence": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["fact", "frame", "source"],
                "properties": {
                    "fact": {"type": "string"},
                    "frame": {"type": "integer"},
                    "source": {"type": "string"},
                },
            },
        },
        "Normative_Inference_Uncertainty": {
            "type": "object",
            "additionalProperties": False,
            "required": ["norm_ref", "basis", "uncertainties"],
            "properties": {
                "norm_ref": {"type": "string"},
                "basis": {"type": "string"},
                "uncertainties": {"type": "array", "items": {"type": "string"}},
            },
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "decision": {"type": "string", "enum": list(DECISIONS)},
    },
}


def new_card_id(alarm_id: str) -> str:
    return f"CARD-{sha256_hex(alarm_id + now_iso())[:10].upper()}"


def validate_card(card: dict, event_classes: Optional[list[str]] = None) -> list[str]:
    """结构校验。返回错误列表（空表示结构合法）。"""
    errors: list[str] = []
    if not isinstance(card, dict):
        return ["卡片不是 JSON 对象"]
    for field_name in REQUIRED_FIELDS:
        if field_name not in card:
            errors.append(f"缺少必填字段 {field_name}")
    event_class = card.get("event_class")
    if event_class is not None and event_classes and event_class not in event_classes:
        errors.append(f"event_class 不在预设枚举表内：{event_class}")
    if card.get("decision") not in DECISIONS:
        errors.append(f"decision 非法：{card.get('decision')}")

    anchor = card.get("Temporal_Anchor")
    if isinstance(anchor, dict):
        for key in ("start", "end"):
            if not isinstance(anchor.get(key), (int, float)):
                errors.append(f"Temporal_Anchor.{key} 必须是数值")
        if isinstance(anchor.get("start"), (int, float)) and isinstance(anchor.get("end"), (int, float)):
            if anchor["end"] < anchor["start"]:
                errors.append("Temporal_Anchor.end 不能早于 start")
        if not isinstance(anchor.get("keyframes"), list):
            errors.append("Temporal_Anchor.keyframes 必须是数组")
    elif anchor is not None:
        errors.append("Temporal_Anchor 必须是对象")

    facts = card.get("Physical_Fact_Evidence")
    if isinstance(facts, list):
        if not facts:
            errors.append("Physical_Fact_Evidence 至少需要一条画面事实")
        for i, fact in enumerate(facts):
            if not isinstance(fact, dict):
                errors.append(f"Physical_Fact_Evidence[{i}] 必须是对象")
                continue
            for key in ("fact", "frame", "source"):
                if key not in fact:
                    errors.append(f"Physical_Fact_Evidence[{i}] 缺少 {key}")
            if "fact" in fact and not str(fact.get("fact", "")).strip():
                errors.append(f"Physical_Fact_Evidence[{i}].fact 不能为空")
    elif facts is not None:
        errors.append("Physical_Fact_Evidence 必须是数组")

    norm = card.get("Normative_Inference_Uncertainty")
    if isinstance(norm, dict):
        for key in ("norm_ref", "basis", "uncertainties"):
            if key not in norm:
                errors.append(f"Normative_Inference_Uncertainty 缺少 {key}")
        if isinstance(norm.get("uncertainties"), list):
            for i, item in enumerate(norm["uncertainties"]):
                if not isinstance(item, str):
                    errors.append(f"uncertainties[{i}] 必须是字符串")
        elif norm.get("uncertainties") is not None:
            errors.append("uncertainties 必须是数组")
    elif norm is not None:
        errors.append("Normative_Inference_Uncertainty 必须是对象")

    conf = card.get("confidence")
    if conf is not None and not (isinstance(conf, (int, float)) and 0.0 <= float(conf) <= 1.0):
        errors.append("confidence 必须在 [0,1] 内")

    evidence = card.get("evidence")
    if isinstance(evidence, dict) and evidence.get("enabled"):
        clip = evidence.get("clip") or {}
        for key in ("start", "end"):
            if not isinstance(clip.get(key), (int, float)):
                errors.append(f"evidence.clip.{key} 必须是数值")
        if isinstance(clip.get("start"), (int, float)) and isinstance(clip.get("end"), (int, float)):
            if clip["end"] < clip["start"]:
                errors.append("evidence.clip.end 不能早于 start")
        keyframes = evidence.get("keyframes")
        if not isinstance(keyframes, list) or not keyframes:
            errors.append("evidence.keyframes 至少需要一帧")
        else:
            for i, kf in enumerate(keyframes):
                if not isinstance(kf, dict) or not isinstance(kf.get("ts"), (int, float)):
                    errors.append(f"evidence.keyframes[{i}] 缺少数值 ts")
        media = evidence.get("media")
        if media is not None and not isinstance(media, dict):
            errors.append("evidence.media 必须是对象")
    elif evidence is not None and not isinstance(evidence, dict):
        errors.append("evidence 必须是对象")

    provenance = card.get("provenance")
    if provenance is not None:
        if not isinstance(provenance, dict):
            errors.append("provenance 必须是对象")
        elif not provenance.get("verifier"):
            errors.append("provenance.verifier 不能为空（必须标明由哪条链路生成）")
    return errors


# --------------------------------------------------------------------------- 签名


def _signing_key(explicit: Optional[str] = None) -> tuple[str, bool]:
    key = explicit
    if not key:
        env_name = os.environ.get("CVALARM_SIGNING_KEY_ENV") or "CVALARM_SIGNING_KEY"
        key = os.environ.get(env_name)
    if not key:
        return ("dev-insecure-signing-key", True)
    return (key, False)


def sign_card(card: dict, key: Optional[str] = None) -> dict:
    """对卡片做 HMAC-SHA256 签名；返回带 signature 的新卡片。"""
    global _WARNED_INSECURE
    secret, insecure = _signing_key(key)
    if insecure and not _WARNED_INSECURE:
        LOG.warning("未设置 CVALARM_SIGNING_KEY，使用开发用固定密钥；生产环境必须配置")
        _WARNED_INSECURE = True
    payload = {k: v for k, v in card.items() if k != "signature"}
    digest = hmac.new(secret.encode("utf-8"), canonical_json(payload).encode("utf-8"),
                      hashlib.sha256).hexdigest()
    signed = dict(card)
    signed["signature"] = f"hmac-sha256:{digest}"
    return signed


def verify_card_signature(card: dict, key: Optional[str] = None) -> bool:
    signature = card.get("signature")
    if not signature or not str(signature).startswith("hmac-sha256:"):
        return False
    expected = sign_card({k: v for k, v in card.items() if k != "signature"}, key)["signature"]
    return hmac.compare_digest(signature, expected)


# --------------------------------------------------------------------------- 评估辅助


def card_claim_span(card: dict) -> tuple[float, float]:
    anchor = card.get("Temporal_Anchor", {})
    return (float(anchor.get("start", 0.0)), float(anchor.get("end", 0.0)))


def card_is_continuous_claim(card: dict) -> bool:
    """卡片是否作出了"连续滞留"的强主张（用于检查是否需要连续轨迹证据）。"""
    basis = str(card.get("Normative_Inference_Uncertainty", {}).get("basis", ""))
    return "连续" in basis


def evidence_summary(card: dict) -> dict:
    facts = card.get("Physical_Fact_Evidence", [])
    norm = card.get("Normative_Inference_Uncertainty", {})
    return {
        "facts": len(facts),
        "uncertainties": len(norm.get("uncertainties", [])),
        "norm_ref": norm.get("norm_ref", ""),
        "decision": card.get("decision"),
        "confidence": card.get("confidence"),
    }


def card_to_markdown(card: dict) -> str:
    anchor = card.get("Temporal_Anchor", {})
    norm = card.get("Normative_Inference_Uncertainty", {})
    lines = [
        f"### 告警卡片 {card.get('card_id', '')}",
        f"- 摄像头：`{card.get('camera_id', '')}`　事件类别：`{card.get('event_class', '')}`",
        f"- 决策：**{card.get('decision', '')}**　置信度：{card.get('confidence', 0):.2f}",
        f"- 时间锚点：[{anchor.get('start', 0):.3f}, {anchor.get('end', 0):.3f}] s，"
        f"关键帧 {anchor.get('keyframes', [])}",
        "",
        "**画面事实（物理证据）**",
    ]
    for fact in card.get("Physical_Fact_Evidence", []):
        lines.append(f"- {fact.get('fact', '')}（frame {fact.get('frame', '-')}，"
                     f"{fact.get('source', '')}）")
    lines += [
        "",
        "**规程推断与未决事项**",
        f"- 依据：{norm.get('norm_ref', '')}",
        f"- 说明：{norm.get('basis', '')}",
    ]
    for item in norm.get("uncertainties", []):
        lines.append(f"- 未决：{item}")
    evidence = card.get("evidence") or {}
    if evidence.get("enabled"):
        clip = evidence.get("clip", {}) or {}
        lines += [
            "",
            "**证据回放**",
            f"- 片段：[{clip.get('start', 0):.1f}, {clip.get('end', 0):.1f}] s"
            f"（前卷 {clip.get('pre_roll_s', 0):.1f}s / 后卷 {clip.get('post_roll_s', 0):.1f}s）",
            f"- 关键帧 {len(evidence.get('keyframes', []))} 个；"
            f"回放模式 {evidence.get('replay_mode', '')}",
            f"- 清单：{evidence.get('manifest', '')}",
        ]
    provenance = card.get("provenance") or {}
    if provenance:
        lines.append(f"\n溯源：{provenance.get('verifier', '')} · "
                     f"{provenance.get('data_source', '')} · "
                     f"{provenance.get('claim', '')}")
    if card.get("signature"):
        lines.append(f"\n签名：`{card['signature']}`")
    return "\n".join(lines)
