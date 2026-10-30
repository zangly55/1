"""Stage4 外部非参数规则：DSL、静态校验、版本管理、回归门禁与原子回滚。

论文 6.3、6.4 节的工程要求：
  * 冻结模型权重，只更新外部非参数规则，避免参数更新带来的遗忘；
  * 自然语言反思的输出**不能**未经检查热加载到生产；
  * 候选规则先进隔离待审区，转成 JSON/DSL，做条件约束与格式校验；
  * 上线前必须重放固定版本回归集（已知真事件 + 典型误报），并另用留出集检查泛化；
  * 发布后可追踪版本、原子回滚。

规则语义（本实现的显式约定，避免"想当然"）：
  * action = alarm  : 满足条件即告警
  * action = suppress: 满足条件即抑制（作业许可等外部规则授权的情形）
  * action = escalate: 满足条件即转人工复核（不自动确证、也不静默丢弃）
  * 求值：按 priority 降序取第一条命中；平级时 suppress > escalate > alarm。
    因此"可见性不足转人工"这类安全规则应给最高优先级，"授权抑制"次之，告警最低。
  * 未命中任何规则时按 policy.default_action（默认 escalate）处理。
"""
from __future__ import annotations

import copy
import os
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .util import (append_jsonl, content_hash, ensure_dir, get_logger, now_iso, read_json,
                   read_jsonl, write_json)

LOG = get_logger("cvalarm.rules")

ACTIONS = ("alarm", "suppress", "escalate")
OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    "contains": lambda a, b: b in a,
}


class RuleError(ValueError):
    pass


# --------------------------------------------------------------------------- 条件求值


def _compare(actual: Any, op: str, expected: Any) -> tuple[bool, str]:
    if op not in OPS:
        return (False, f"未知操作符 {op}")
    if actual is None:
        return (False, "字段缺失")
    try:
        return (bool(OPS[op](actual, expected)), "")
    except TypeError as exc:
        return (False, f"类型不匹配：{exc}")


def eval_condition(cond: dict, context: dict) -> tuple[bool, str]:
    field_name = cond.get("field", "")
    op = cond.get("op", "==")
    value = cond.get("value")
    if field_name not in context:
        return (False, f"缺少字段 {field_name}")
    ok, err = _compare(context[field_name], op, value)
    return (ok, err)


def eval_when(when: dict, context: dict) -> tuple[bool, list[str]]:
    """求值 when 子句。返回 (是否命中, 诊断信息)。

    all：全部成立；any：任一成立（空 any 视为不成立）；none：全部不成立。
    空 when {} 或 {"all": []} 视为恒真，用于"默认兜底"规则。
    """
    notes: list[str] = []
    if not when:
        return (True, notes)
    all_conds = when.get("all", [])
    any_conds = when.get("any", [])
    none_conds = when.get("none", [])
    ok_all = True
    for cond in all_conds:
        ok, err = eval_condition(cond, context)
        if err:
            notes.append(err)
        ok_all = ok_all and ok
    ok_any = True
    if any_conds:
        ok_any = False
        for cond in any_conds:
            ok, err = eval_condition(cond, context)
            if err:
                notes.append(err)
            if ok:
                ok_any = True
    ok_none = True
    for cond in none_conds:
        ok, err = eval_condition(cond, context)
        if err:
            notes.append(err)
        ok_none = ok_none and not ok
    return (ok_all and ok_any and ok_none, notes)


# --------------------------------------------------------------------------- 数据结构


@dataclass
class Rule:
    rule_id: str
    event_classes: list[str]
    when: dict
    action: str
    priority: int = 50
    description: str = ""
    severity: str = "medium"
    norm_ref: str = ""
    require_authorization: list[str] = field(default_factory=list)
    cameras: list[str] = field(default_factory=lambda: ["*"])

    def matches(self, event_class: str, context: dict) -> tuple[bool, list[str]]:
        if "*" not in self.event_classes and event_class not in self.event_classes:
            return (False, [])
        cam = context.get("camera_id")
        if self.cameras and "*" not in self.cameras and cam not in self.cameras:
            return (False, [])
        return eval_when(self.when, {**context, "event_class": event_class})

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "event_classes": list(self.event_classes),
            "when": copy.deepcopy(self.when),
            "action": self.action,
            "priority": self.priority,
            "description": self.description,
            "severity": self.severity,
            "norm_ref": self.norm_ref,
            "require_authorization": list(self.require_authorization),
            "cameras": list(self.cameras),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        return cls(
            rule_id=str(data["rule_id"]),
            event_classes=list(data.get("event_classes", ["*"])),
            when=dict(data.get("when", {})),
            action=str(data.get("action", "escalate")),
            priority=int(data.get("priority", 50)),
            description=str(data.get("description", "")),
            severity=str(data.get("severity", "medium")),
            norm_ref=str(data.get("norm_ref", "")),
            require_authorization=list(data.get("require_authorization", [])),
            cameras=list(data.get("cameras", ["*"])),
        )


@dataclass
class RuleSet:
    ruleset_id: str
    version_label: str
    rules: list[Rule]
    policy: dict = field(default_factory=dict)
    description: str = ""
    created_at: str = ""

    @property
    def digest(self) -> str:
        return content_hash(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "ruleset_id": self.ruleset_id,
            "version_label": self.version_label,
            "description": self.description,
            "created_at": self.created_at,
            "policy": copy.deepcopy(self.policy),
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RuleSet":
        return cls(
            ruleset_id=str(data.get("ruleset_id", "ruleset")),
            version_label=str(data.get("version_label", "")),
            description=str(data.get("description", "")),
            created_at=str(data.get("created_at", "")),
            policy=dict(data.get("policy", {})),
            rules=[Rule.from_dict(r) for r in data.get("rules", [])],
        )

    @classmethod
    def load(cls, path: str) -> "RuleSet":
        data = read_json(path, default=None)
        if data is None:
            raise RuleError(f"规则集不存在或不是合法 JSON：{path}")
        return cls.from_dict(data)

    def save(self, path: str) -> str:
        ensure_dir(os.path.dirname(os.path.abspath(path)))
        return write_json(path, self.to_dict())


# --------------------------------------------------------------------------- 校验


@dataclass
class ValidationReport:
    ruleset_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rule_count: int = 0
    coverage: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "ruleset_id": self.ruleset_id,
            "ok": self.ok,
            "rule_count": self.rule_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "coverage": self.coverage,
        }


FIELD_DOMAIN_HINT = {
    "dwell_seconds": "number",
    "motion_energy": "number",
    "mean_det_score": "number",
    "visibility_ok": "bool",
    "authorized": "bool",
    "in_roi": "bool",
    "continuity_verified": "bool",
}


def validate_ruleset(ruleset: RuleSet, event_classes: Optional[Iterable[str]] = None) -> ValidationReport:
    report = ValidationReport(ruleset_id=ruleset.ruleset_id, rule_count=len(ruleset.rules))
    seen_ids: set[str] = set()
    for rule in ruleset.rules:
        prefix = f"[{rule.rule_id}]"
        if rule.rule_id in seen_ids:
            report.errors.append(f"{prefix} rule_id 重复")
        seen_ids.add(rule.rule_id)
        if not rule.rule_id:
            report.errors.append("存在空 rule_id 的规则")
        if rule.action not in ACTIONS:
            report.errors.append(f"{prefix} 非法 action：{rule.action}")
        if not rule.event_classes:
            report.errors.append(f"{prefix} event_classes 不能为空")
        if not isinstance(rule.when, dict):
            report.errors.append(f"{prefix} when 必须是对象")
            continue
        for key in rule.when:
            if key not in ("all", "any", "none"):
                report.errors.append(f"{prefix} when 出现未知子句 {key}")
        conds = [c for key in ("all", "any", "none") for c in rule.when.get(key, [])]
        for cond in conds:
            if not isinstance(cond, dict) or "field" not in cond or "op" not in cond:
                report.errors.append(f"{prefix} 条件缺少 field/op：{cond}")
                continue
            if cond["op"] not in OPS:
                report.errors.append(f"{prefix} 未知操作符 {cond['op']}")
            if "value" not in cond:
                report.errors.append(f"{prefix} 条件缺少 value：{cond}")
            hint = FIELD_DOMAIN_HINT.get(str(cond["field"]))
            if hint == "bool" and cond["op"] not in ("==", "!="):
                report.warnings.append(f"{prefix} 布尔字段 {cond['field']} 使用了 {cond['op']}")
            if hint == "number":
                try:
                    float(cond.get("value"))
                except (TypeError, ValueError):
                    report.errors.append(f"{prefix} 数值字段 {cond['field']} 的 value 非数值")
            for value in cond.get("value", []) if isinstance(cond.get("value"), list) else []:
                if isinstance(value, dict):
                    report.errors.append(f"{prefix} 条件 value 不允许嵌套对象")
        # 单规则自相矛盾检查
        contradictory = _self_contradiction(rule.when)
        if contradictory:
            report.errors.append(f"{prefix} 条件不可满足（死锁）：{contradictory}")
        if rule.action in ("alarm", "suppress") and not rule.norm_ref:
            report.warnings.append(f"{prefix} 缺少 norm_ref（规范依据），卡片无法追溯来源")

    # 跨规则冲突：只在"优先级相同、条件域重叠"或"低优先级规则想否决高优先级结论"时告警，
    # 因为最终结论由优先级唯一决定（suppress/alarm/escalate 的优先级由规则集显式给定）。
    for i, a in enumerate(ruleset.rules):
        for b in ruleset.rules[i + 1:]:
            if a.action == b.action:
                continue
            if not (set(a.event_classes) & set(b.event_classes)) and \
                    "*" not in a.event_classes and "*" not in b.event_classes:
                continue
            if not _overlap(a.when, b.when):
                continue
            pair = {a.action, b.action}
            if a.priority == b.priority:
                report.warnings.append(
                    f"[{a.rule_id}] 与 [{b.rule_id}] 优先级相同且条件域重叠、动作不同，"
                    f"结论取决于平级次序（suppress > escalate > alarm），建议显式拉开优先级")
            elif pair == {"alarm", "suppress"}:
                suppress = a if a.action == "suppress" else b
                alarm = b if suppress is a else a
                if suppress.priority < alarm.priority:
                    report.warnings.append(
                        f"抑制规则 [{suppress.rule_id}] 优先级 {suppress.priority} 低于"
                        f"告警规则 [{alarm.rule_id}] {alarm.priority}，抑制将不生效")
            elif "escalate" in pair:
                escalate = a if a.action == "escalate" else b
                other = b if escalate is a else a
                if escalate.priority < other.priority:
                    report.warnings.append(
                        f"安全/人工复核规则 [{escalate.rule_id}] 优先级低于"
                        f"[{other.rule_id}]，无法阻止后者给出确证结论")

    # 覆盖度
    classes = list(event_classes or [])
    covered: dict[str, list[str]] = {}
    for rule in ruleset.rules:
        for cls in rule.event_classes:
            covered.setdefault(cls, []).append(rule.rule_id)
    report.coverage = covered
    for cls in classes:
        if cls not in covered and "*" not in covered:
            report.warnings.append(f"事件类别 {cls} 没有显式规则覆盖，将走 policy.default_action")

    # 是否每条 alarm 规则都能被"外部授权"覆盖（论文强调事实与规程分离）
    if not any(r.action == "suppress" and r.require_authorization for r in ruleset.rules):
        report.warnings.append("没有基于外部授权的抑制规则：规程适用性无法与画面事实分离核验")
    return report


def _self_contradiction(when: dict) -> str:
    """检测同一字段上的数值区间为空、或同一字段被要求等于两个不同值。"""
    per_field: dict[str, list[tuple[str, Any]]] = {}
    for cond in when.get("all", []):
        if isinstance(cond, dict) and "field" in cond and "op" in cond:
            per_field.setdefault(str(cond["field"]), []).append((cond["op"], cond.get("value")))
    for field_name, items in per_field.items():
        numeric = [(op, v) for op, v in items if op in (">", ">=", "<", "<=")]
        lo, lo_strict = None, False
        hi, hi_strict = None, False
        for op, value in numeric:
            try:
                val = float(value)
            except (TypeError, ValueError):
                continue
            if op in (">", ">="):
                if lo is None or val > lo:
                    lo, lo_strict = val, op == ">"
                elif val == lo:
                    lo_strict = lo_strict or op == ">"
            else:
                if hi is None or val < hi:
                    hi, hi_strict = val, op == "<"
                elif val == hi:
                    hi_strict = hi_strict or op == "<"
        if lo is not None and hi is not None:
            if lo > hi:
                return f"{field_name} 下界 {lo} > 上界 {hi}"
            if lo == hi and (lo_strict or hi_strict):
                return f"{field_name} 区间为空（下界 {lo} 与上界 {hi} 之间无可行值）"
        equals = [v for op, v in items if op == "=="]
        if len({str(v) for v in equals}) > 1:
            return f"{field_name} 被要求同时等于 {equals}"
        if equals and numeric:
            try:
                val = float(equals[0])
                if lo is not None and val < lo:
                    return f"{field_name} 要求 ={val} 但下界为 {lo}"
                if hi is not None and val > hi:
                    return f"{field_name} 要求 ={val} 但上界为 {hi}"
            except (TypeError, ValueError):
                pass
    return ""


def _overlap(a: dict, b: dict) -> bool:
    """保守的重叠判断：只要共享字段可能同时满足，就认为条件域可能重叠。"""
    fa = _numeric_bounds(a)
    fb = _numeric_bounds(b)
    for field_name in set(fa) & set(fb):
        (alo, ahi) = fa[field_name]
        (blo, bhi) = fb[field_name]
        lo = max(v for v in (alo, blo, float("-inf")) if v is not None)
        hi = min(v for v in (ahi, bhi, float("inf")) if v is not None)
        if lo > hi:
            return False
    return True


def _numeric_bounds(when: dict) -> dict[str, tuple[Optional[float], Optional[float]]]:
    out: dict[str, tuple[Optional[float], Optional[float]]] = {}
    for cond in when.get("all", []):
        if not isinstance(cond, dict) or cond.get("op") not in (">", ">=", "<", "<="):
            continue
        try:
            val = float(cond.get("value"))
        except (TypeError, ValueError):
            continue
        lo, hi = out.get(str(cond["field"]), (None, None))
        if cond["op"] in (">", ">="):
            lo = val if lo is None else max(lo, val)
        else:
            hi = val if hi is None else min(hi, val)
        out[str(cond["field"])] = (lo, hi)
    return out


# --------------------------------------------------------------------------- 求值引擎


@dataclass
class RuleDecision:
    action: str
    rule_id: str = ""
    norm_ref: str = ""
    severity: str = "medium"
    description: str = ""
    matched: list[dict] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "rule_id": self.rule_id,
            "norm_ref": self.norm_ref,
            "severity": self.severity,
            "description": self.description,
            "matched": self.matched,
            "diagnostics": self.diagnostics,
        }


class RuleEngine:
    """规则求值：优先级降序取第一条命中；平级时 suppress > escalate > alarm。

    结论由优先级唯一决定，因此"安全规则"（可见性不足转人工）应给最高优先级，
    "授权抑制"次之，普通告警最低——歧义在静态校验阶段就会被提示出来。
    """

    ACTION_RANK = {"suppress": 0, "escalate": 1, "alarm": 2}

    def __init__(self, ruleset: RuleSet) -> None:
        self.ruleset = ruleset
        self._ordered = sorted(ruleset.rules,
                               key=lambda r: (-r.priority, self.ACTION_RANK.get(r.action, 9),
                                              r.rule_id))

    def evaluate(self, event_class: str, context: dict) -> RuleDecision:
        matched: list[dict] = []
        diagnostics: list[str] = []
        chosen: Optional[Rule] = None

        for rule in self._ordered:
            ok, notes = rule.matches(event_class, context)
            if ok:
                matched.append({"rule_id": rule.rule_id, "action": rule.action,
                                "priority": rule.priority})
                if chosen is None:
                    chosen = rule
            elif notes:
                diagnostics.extend(f"{rule.rule_id}: {n}" for n in notes)

        if chosen is None:
            default = str(self.ruleset.policy.get("default_action", "escalate"))
            action = default if default in ACTIONS else "escalate"
            chosen = Rule("__default__", ["*"], {}, action, priority=0,
                          description="未命中任何规则，按策略兜底", norm_ref="")
            diagnostics.append("未命中任何规则，采用 policy.default_action")

        return RuleDecision(
            action=chosen.action,
            rule_id=chosen.rule_id,
            norm_ref=chosen.norm_ref,
            severity=chosen.severity,
            description=chosen.description,
            matched=matched,
            diagnostics=diagnostics,
        )


# --------------------------------------------------------------------------- 版本管理


class RuleRegistry:
    """规则版本仓库：内容寻址 + 待审区 + 主动指针 + 审计账本 + 原子回滚。"""

    def __init__(self, cfg, state_dir: Optional[str] = None) -> None:
        self.cfg = cfg
        self.state_dir = state_dir or cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
        self.versions_dir = ensure_dir(self._join(
            cfg.get("rules.versions_dir", "state/rules_versions")))
        self.staged_dir = ensure_dir(self._join(
            cfg.get("rules.staged_dir", "state/rules_staged")))
        self.ledger_path = self._join(cfg.get("rules.ledger", "state/rule_ledger.jsonl"))
        self.pointer_path = self._join(
            cfg.get("rules.active_pointer", "state/rules_active.json"))
        self._ensure_pointer()

    def _join(self, path: str) -> str:
        """把配置里的相对路径映射到 state_dir 之下。

        约定：配置中形如 "state/xxx" 的路径以 runtime.state_dir 为根，
        其余相对路径按工程根目录解析；绝对路径原样使用。
        """
        if os.path.isabs(path):
            return path
        rel = os.path.relpath(path, "state") if path.startswith("state" + os.sep) or \
            path.startswith("state/") else path
        if rel.startswith(".."):
            return self.cfg.resolve(path)
        return os.path.join(self.state_dir, rel)

    # ------------------------------------------------------------------ 指针
    def _ensure_pointer(self) -> None:
        if os.path.exists(self.pointer_path):
            return
        default_path = self.cfg.resolve(str(self.cfg.get("rules.active", "")))
        if not default_path or not os.path.exists(default_path):
            return
        ruleset = RuleSet.load(default_path)
        digest = ruleset.digest
        version_path = os.path.join(self.versions_dir, f"{digest}.json")
        if not os.path.exists(version_path):
            ruleset.save(version_path)
        write_json(self.pointer_path, {
            "active_hash": digest,
            "version_label": ruleset.version_label,
            "path": os.path.relpath(version_path, self.state_dir),
            "updated_at": now_iso(),
            "source": "bootstrap",
        })
        append_jsonl(self.ledger_path, [{
            "ts": now_iso(),
            "action": "bootstrap",
            "ruleset_hash": digest,
            "version_label": ruleset.version_label,
            "operator": "system",
            "reason": "首次启动，登记默认规则集",
            "prev_hash": None,
            "duration_ms": 0.0,
        }])

    def pointer(self) -> dict:
        return read_json(self.pointer_path, default={}) or {}

    def active(self) -> RuleSet:
        pointer = self.pointer()
        digest = pointer.get("active_hash")
        # Content-addressed versions move with the state directory.
        path = os.path.join(self.versions_dir, f"{digest}.json") if digest else ""
        if not path or not os.path.exists(path):
            legacy = pointer.get("path", "")
            path = legacy if os.path.isabs(legacy) else os.path.join(self.state_dir, legacy)
            if not legacy:
                path = self.cfg.resolve(str(self.cfg.get("rules.active")))
        if not os.path.exists(path):
            raise RuleError(f"当前生效规则集文件缺失：{path}")
        ruleset = RuleSet.load(path)
        if digest and ruleset.digest != digest:
            raise RuleError("活动规则内容与哈希不一致，拒绝加载")
        return ruleset

    @property
    def active_hash(self) -> str:
        return str(self.pointer().get("active_hash", ""))

    # ------------------------------------------------------------------ 版本
    def list_versions(self) -> list[dict]:
        out: list[dict] = []
        active_hash = self.active_hash
        for name in sorted(os.listdir(self.versions_dir)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self.versions_dir, name)
            data = read_json(path, default={}) or {}
            digest = name[:-5]
            out.append({
                "hash": digest,
                "version_label": data.get("version_label", ""),
                "ruleset_id": data.get("ruleset_id", ""),
                "rule_count": len(data.get("rules", [])),
                "created_at": data.get("created_at", ""),
                "active": digest == active_hash,
            })
        return out

    def stage(self, ruleset: RuleSet, operator: str = "operator", reason: str = "") -> str:
        """写入隔离待审区，返回暂存路径；此阶段尚未生效。"""
        digest = ruleset.digest
        path = os.path.join(self.staged_dir, f"{digest}.json")
        ruleset.save(path)
        append_jsonl(self.ledger_path, [{
            "ts": now_iso(),
            "action": "stage",
            "ruleset_hash": digest,
            "version_label": ruleset.version_label,
            "operator": operator,
            "reason": reason,
            "prev_hash": self.active_hash,
            "duration_ms": 0.0,
        }])
        return path

    def stage_path(self, digest_prefix: str) -> str:
        for name in os.listdir(self.staged_dir):
            if name.endswith(".json") and name[:-5].startswith(digest_prefix):
                return os.path.join(self.staged_dir, name)
        raise RuleError(f"待审区找不到规则集：{digest_prefix}")

    def promote(self, ruleset: RuleSet, gate: dict, operator: str = "operator",
                reason: str = "") -> dict:
        """原子发布：备份旧版本 → 写新版本文件 → 原子替换主动指针。"""
        if not gate.get("passed", False):
            failures = "; ".join(gate.get("failures", [])) or "未提供失败原因"
            raise RuleError(f"回归门禁未通过，禁止发布：{failures}")
        t0 = time.perf_counter()
        digest = ruleset.digest
        version_path = os.path.join(self.versions_dir, f"{digest}.json")
        if not os.path.exists(version_path):
            ruleset.save(version_path)
        prev = self.pointer()
        payload = {
            "active_hash": digest,
            "version_label": ruleset.version_label,
            "path": os.path.relpath(version_path, self.state_dir),
            "updated_at": now_iso(),
            "source": "promote",
            "gate": gate,
        }
        write_json(self.pointer_path, payload)  # 内部使用 os.replace，保证原子性
        duration_ms = (time.perf_counter() - t0) * 1000.0
        append_jsonl(self.ledger_path, [{
            "ts": now_iso(),
            "action": "promote",
            "ruleset_hash": digest,
            "version_label": ruleset.version_label,
            "operator": operator,
            "reason": reason,
            "prev_hash": prev.get("active_hash"),
            "gate": gate,
            "duration_ms": round(duration_ms, 3),
        }])
        return {"active_hash": digest, "path": version_path,
                "duration_ms": round(duration_ms, 3), "gate": gate}

    def rollback(self, to_hash: str, operator: str = "operator",
                 reason: str = "回滚到稳定版本") -> dict:
        """原子回滚到指定版本；文件缺失或哈希未知时拒绝执行。"""
        t0 = time.perf_counter()
        path = os.path.join(self.versions_dir, f"{to_hash}.json")
        if not os.path.exists(path):
            raise RuleError(f"版本文件不存在：{path}")
        ruleset = RuleSet.load(path)
        if ruleset.digest != to_hash:
            raise RuleError("版本文件内容与哈希不一致，拒绝回滚（可能被篡改）")
        prev = self.pointer()
        write_json(self.pointer_path, {
            "active_hash": to_hash,
            "version_label": ruleset.version_label,
            "path": os.path.relpath(path, self.state_dir),
            "updated_at": now_iso(),
            "source": "rollback",
        })
        duration_ms = (time.perf_counter() - t0) * 1000.0
        append_jsonl(self.ledger_path, [{
            "ts": now_iso(),
            "action": "rollback",
            "ruleset_hash": to_hash,
            "version_label": ruleset.version_label,
            "operator": operator,
            "reason": reason,
            "prev_hash": prev.get("active_hash"),
            "duration_ms": round(duration_ms, 3),
        }])
        return {"active_hash": to_hash, "version_label": ruleset.version_label,
                "duration_ms": round(duration_ms, 3)}

    def ledger(self, limit: int = 100) -> list[dict]:
        items = list(read_jsonl(self.ledger_path))
        return items[-limit:]


# --------------------------------------------------------------------------- 回归门禁


def regression_gate(candidate: dict, baseline: dict, gate_cfg: dict) -> dict:
    """比较候选规则集与基线的回归指标，决定是否允许发布。

    candidate / baseline: {"event_recall": float, "false_alarms_per_camera_hour": float,
                           "events": n, "fa": n, "camera_hours": float}
    判别口径：关键事件召回不得下降超过 recall_tolerance；
              误报不得上升超过 fa_tolerance。
    仅代表有限样本上的行为，不构成对未来召回的保证（论文 6.4 节）。
    """
    recall_tol = float(gate_cfg.get("recall_tolerance", 0.02))
    fa_tol = float(gate_cfg.get("fa_tolerance", 0.05))
    failures: list[str] = []
    warnings: list[str] = []

    cand_recall = float(candidate.get("event_recall", 0.0))
    base_recall = float(baseline.get("event_recall", 0.0))
    cand_fa = float(candidate.get("false_alarms_per_camera_hour", 0.0))
    base_fa = float(baseline.get("false_alarms_per_camera_hour", 0.0))
    cand_uncertain = float(candidate.get("deferred_rate", 0.0))
    base_uncertain = float(baseline.get("deferred_rate", 0.0))

    if cand_recall < base_recall - recall_tol:
        failures.append(
            f"事件召回下降 {base_recall:.3f} → {cand_recall:.3f}（容忍 {recall_tol:.3f}）")
    if cand_fa > base_fa + fa_tol:
        failures.append(f"FA/CH 上升 {base_fa:.3f} → {cand_fa:.3f}（容忍 {fa_tol:.3f}）")
    if cand_uncertain > base_uncertain + 0.05:
        warnings.append(
            f"转人工比例上升 {base_uncertain:.3f} → {cand_uncertain:.3f}（复核成本增加）")
    if int(candidate.get("events", 0)) < 3:
        warnings.append("回归集事件数少于 3，门禁结论的统计不确定性较大")

    passed = not failures
    return {
        "passed": passed,
        "failures": failures,
        "warnings": warnings,
        "recall_tolerance": recall_tol,
        "fa_tolerance": fa_tol,
        "baseline": baseline,
        "candidate": candidate,
        "checked_at": now_iso(),
    }


def candidate_from_feedback(reason_counts: dict, base_ruleset: RuleSet) -> RuleSet:
    """把驳回理由聚类为候选规则（自然语言反思的工程化落地）。

    产出的是**候选**，必须经过 validate_ruleset + regression_gate + 人工确认才能发布。
    """
    ruleset = RuleSet.from_dict(base_ruleset.to_dict())
    ruleset.ruleset_id = f"{base_ruleset.ruleset_id}-reflect"
    ruleset.version_label = f"{base_ruleset.version_label}+reflect"
    ruleset.created_at = now_iso()
    if reason_counts.get("REFLECTION_OR_SHADOW", 0) > 0:
        ruleset.rules.append(Rule(
            rule_id="R-SUPPRESS-REFLECTION",
            event_classes=["UNAUTHORIZED_INTRUSION", "RESTRICTED_AREA_ACTIVITY", "LOITERING"],
            when={"all": [
                {"field": "mean_det_score", "op": "<", "value": 0.62},
                {"field": "motion_energy", "op": "<", "value": 0.15},
                {"field": "dwell_seconds", "op": "<", "value": 300},
            ]},
            action="suppress",
            priority=140,
            description="人工驳回聚类：低检测分 + 低运动能量 + 短时滞留多为反光/阴影伪目标",
            severity="info",
            norm_ref="《监控误报治理指引》§4.2（反光类伪目标）",
        ))
    if reason_counts.get("DUPLICATE_ALARM", 0) > 0:
        ruleset.rules.append(Rule(
            rule_id="R-DEDUP-REPEAT",
            event_classes=["*"],
            when={"all": [{"field": "recent_duplicate_count", "op": ">=", "value": 1}]},
            action="suppress",
            priority=130,
            description="同一目标同一区域在合并窗口内重复触发，抑制重复卡片",
            severity="info",
            norm_ref="《告警去重与合并规则》§2.1",
        ))
    return ruleset
