"""规则 DSL、静态校验、版本管理与回归门禁测试。"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import helpers

from cvalarm.rules import (Rule, RuleEngine, RuleError, RuleRegistry, RuleSet, eval_when,
                           regression_gate, validate_ruleset)


def rule(rule_id="R1", classes=("X",), when=None, action="alarm", priority=50,
         norm_ref="规范 A") -> Rule:
    return Rule(rule_id=rule_id, event_classes=list(classes), when=when or {},
                action=action, priority=priority, norm_ref=norm_ref,
                description=f"{rule_id} desc")


def ruleset(*rules) -> RuleSet:
    return RuleSet(ruleset_id="test", version_label="t1", rules=list(rules),
                   policy={"default_action": "escalate"}, created_at="2026-01-01T00:00:00+00:00")


class TestConditionEval(unittest.TestCase):
    def test_ops(self):
        ctx = {"a": 5, "b": True, "c": "ROI-A", "d": ["x", "y"]}
        self.assertTrue(eval_when({"all": [{"field": "a", "op": ">=", "value": 5}]}, ctx)[0])
        self.assertFalse(eval_when({"all": [{"field": "a", "op": ">", "value": 5}]}, ctx)[0])
        self.assertTrue(eval_when({"all": [{"field": "b", "op": "==", "value": True}]}, ctx)[0])
        self.assertTrue(eval_when({"all": [{"field": "c", "op": "in", "value": ["ROI-A"]}]}, ctx)[0])
        self.assertTrue(eval_when({"none": [{"field": "a", "op": "<", "value": 0}]}, ctx)[0])
        self.assertTrue(eval_when({"any": [{"field": "a", "op": "==", "value": 1},
                                           {"field": "a", "op": "==", "value": 5}]}, ctx)[0])

    def test_missing_field_not_matched(self):
        ok, notes = eval_when({"all": [{"field": "nope", "op": "==", "value": 1}]}, {})
        self.assertFalse(ok)
        self.assertTrue(notes)

    def test_empty_when_is_true(self):
        self.assertTrue(eval_when({}, {})[0])
        self.assertTrue(eval_when({"all": []}, {})[0])


class TestValidation(unittest.TestCase):
    def test_valid_ruleset(self):
        report = validate_ruleset(ruleset(rule()), ["X"])
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(report.rule_count, 1)

    def test_unsatisfiable_rule_is_error(self):
        bad = rule(when={"all": [{"field": "dwell_seconds", "op": ">=", "value": 1800},
                                 {"field": "dwell_seconds", "op": "<", "value": 1800}]})
        report = validate_ruleset(ruleset(bad), ["X"])
        self.assertFalse(report.ok)
        self.assertTrue(any("不可满足" in e for e in report.errors))

    def test_unknown_operator(self):
        bad = rule(when={"all": [{"field": "dwell_seconds", "op": "~=", "value": 1}]})
        report = validate_ruleset(ruleset(bad), ["X"])
        self.assertFalse(report.ok)

    def test_duplicate_rule_id(self):
        report = validate_ruleset(ruleset(rule("A"), rule("A")), ["X"])
        self.assertFalse(report.ok)
        self.assertTrue(any("重复" in e for e in report.errors))

    def test_invalid_action(self):
        report = validate_ruleset(ruleset(rule(action="ignore")), ["X"])
        self.assertFalse(report.ok)

    def test_bool_field_comparison_warns(self):
        warn = rule(when={"all": [{"field": "visibility_ok", "op": ">", "value": 0}]})
        report = validate_ruleset(ruleset(warn), ["X"])
        self.assertTrue(report.ok)
        self.assertTrue(any("布尔字段" in w for w in report.warnings))

    def test_uncovered_event_class_warns(self):
        report = validate_ruleset(ruleset(rule(classes=["X"])), ["X", "Y"])
        self.assertTrue(any("Y" in w for w in report.warnings))

    def test_conflicting_actions_warn(self):
        a = rule("A", action="alarm", priority=100,
                 when={"all": [{"field": "dwell_seconds", "op": ">=", "value": 10}]})
        b = rule("B", action="suppress", priority=100,
                 when={"all": [{"field": "dwell_seconds", "op": ">=", "value": 20}]})
        report = validate_ruleset(ruleset(a, b), ["X"])
        self.assertTrue(any("优先级相同" in w for w in report.warnings))

    def test_low_priority_suppress_warns(self):
        a = rule("A", action="alarm", priority=90,
                 when={"all": [{"field": "dwell_seconds", "op": ">=", "value": 10}]})
        b = rule("B", action="suppress", priority=10,
                 when={"all": [{"field": "dwell_seconds", "op": ">=", "value": 20}]})
        report = validate_ruleset(ruleset(a, b), ["X"])
        self.assertTrue(any("抑制将不生效" in w for w in report.warnings))

    def test_missing_authorization_rule_warns(self):
        report = validate_ruleset(ruleset(rule()), ["X"])
        self.assertTrue(any("授权" in w for w in report.warnings))

    def test_no_norm_ref_warns(self):
        report = validate_ruleset(ruleset(rule(norm_ref="")), ["X"])
        self.assertTrue(any("norm_ref" in w for w in report.warnings))


class TestEngine(unittest.TestCase):
    def test_suppress_beats_alarm(self):
        engine = RuleEngine(ruleset(
            rule("ALARM", action="alarm", norm_ref="A"),
            rule("SUPPRESS", action="suppress", priority=150, norm_ref="B")))
        decision = engine.evaluate("X", {"camera_id": "C1"})
        self.assertEqual(decision.action, "suppress")
        self.assertEqual(decision.rule_id, "SUPPRESS")

    def test_alarm_when_no_suppress(self):
        engine = RuleEngine(ruleset(
            rule("ALARM", action="alarm", when={"all": [{"field": "dwell_seconds",
                                                         "op": ">=", "value": 10}]}),
            rule("SUPPRESS", action="suppress", priority=150,
                 when={"all": [{"field": "authorized", "op": "==", "value": True}]})))
        decision = engine.evaluate("X", {"dwell_seconds": 30, "authorized": False})
        self.assertEqual(decision.action, "alarm")

    def test_default_action_is_escalate(self):
        engine = RuleEngine(ruleset(rule("A", when={"all": [{"field": "dwell_seconds",
                                                            "op": ">", "value": 9999}]})))
        decision = engine.evaluate("X", {"dwell_seconds": 1})
        self.assertEqual(decision.action, "escalate")
        self.assertEqual(decision.rule_id, "__default__")

    def test_priority_order(self):
        engine = RuleEngine(ruleset(
            rule("LOW", action="alarm", priority=1, norm_ref="L"),
            rule("HIGH", action="alarm", priority=99, norm_ref="H")))
        self.assertEqual(engine.evaluate("X", {}).rule_id, "HIGH")

    def test_safety_escalate_beats_lower_priority_alarm(self):
        """可见性安全规则必须能压住低优先级告警，否则夜间会给出确证结论。"""
        engine = RuleEngine(ruleset(
            rule("SAFETY", action="escalate", priority=200,
                 when={"all": [{"field": "visibility_ok", "op": "==", "value": False}]}),
            rule("ALARM", action="alarm", priority=80)))
        decision = engine.evaluate("X", {"visibility_ok": False})
        self.assertEqual(decision.action, "escalate")

    def test_tie_break_prefers_suppress(self):
        engine = RuleEngine(ruleset(
            rule("ALARM", action="alarm", priority=100),
            rule("SUPPRESS", action="suppress", priority=100)))
        self.assertEqual(engine.evaluate("X", {}).action, "suppress")


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cvalarm-rules-")
        self.cfg = helpers.default_config()
        self.registry = RuleRegistry(self.cfg, self.tmp)

    def test_bootstrap_registers_active(self):
        active = self.registry.active()
        self.assertTrue(active.rules)
        self.assertEqual(self.registry.active_hash, active.digest)

    def test_stage_then_promote_then_rollback(self):
        original = self.registry.active_hash
        candidate = RuleSet.from_dict(self.registry.active().to_dict())
        candidate.ruleset_id = "test-v2"
        candidate.version_label = "v2"
        candidate.rules.append(rule("R-NEW", classes=["UNKNOWN_ANOMALY"],
                                    action="escalate", priority=5))
        staged = self.registry.stage(candidate, reason="测试")
        self.assertTrue(os.path.exists(staged))
        gate = {"passed": True, "failures": [], "warnings": []}
        info = self.registry.promote(candidate, gate, reason="发布 v2")
        self.assertEqual(info["active_hash"], candidate.digest)
        self.assertEqual(self.registry.active().version_label, "v2")
        self.assertGreaterEqual(info["duration_ms"], 0.0)

        back = self.registry.rollback(original, reason="回滚测试")
        self.assertEqual(back["active_hash"], original)
        self.assertEqual(self.registry.active_hash, original)
        actions = [item["action"] for item in self.registry.ledger(50)]
        self.assertIn("stage", actions)
        self.assertIn("promote", actions)
        self.assertIn("rollback", actions)

    def test_promote_blocked_by_failed_gate(self):
        candidate = self.registry.active()
        with self.assertRaises(RuleError):
            self.registry.promote(candidate, {"passed": False, "failures": ["召回下降"]})

    def test_rollback_rejects_unknown_hash(self):
        with self.assertRaises(RuleError):
            self.registry.rollback("deadbeefdead")

    def test_list_versions(self):
        versions = self.registry.list_versions()
        self.assertTrue(versions)
        self.assertTrue(any(v["active"] for v in versions))


class TestRegressionGate(unittest.TestCase):
    GATE = {"recall_tolerance": 0.02, "fa_tolerance": 0.05}

    def test_pass_when_metrics_improve(self):
        gate = regression_gate(
            {"event_recall": 0.9, "false_alarms_per_camera_hour": 0.1, "events": 10},
            {"event_recall": 0.8, "false_alarms_per_camera_hour": 0.2}, self.GATE)
        self.assertTrue(gate["passed"])

    def test_fail_on_recall_drop(self):
        gate = regression_gate(
            {"event_recall": 0.5, "false_alarms_per_camera_hour": 0.1, "events": 10},
            {"event_recall": 0.8, "false_alarms_per_camera_hour": 0.2}, self.GATE)
        self.assertFalse(gate["passed"])
        self.assertTrue(any("召回" in f for f in gate["failures"]))

    def test_fail_on_fa_increase(self):
        gate = regression_gate(
            {"event_recall": 0.8, "false_alarms_per_camera_hour": 0.9, "events": 10},
            {"event_recall": 0.8, "false_alarms_per_camera_hour": 0.2}, self.GATE)
        self.assertFalse(gate["passed"])

    def test_small_set_warns(self):
        gate = regression_gate(
            {"event_recall": 0.9, "false_alarms_per_camera_hour": 0.1, "events": 2},
            {"event_recall": 0.8, "false_alarms_per_camera_hour": 0.2}, self.GATE)
        self.assertTrue(gate["warnings"])


class TestBundledRulesets(unittest.TestCase):
    def _load(self, name):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "config", "rules", name)
        return RuleSet.load(path)

    def test_v1_valid(self):
        report = validate_ruleset(self._load("rules_v1.json"))
        self.assertTrue(report.ok, report.errors)

    def test_v2_valid(self):
        report = validate_ruleset(self._load("rules_v2_candidate.json"))
        self.assertTrue(report.ok, report.errors)

    def test_v3_is_statically_valid_but_behaviourally_harmful(self):
        ruleset_v3 = self._load("rules_v3_overbroad.json")
        report = validate_ruleset(ruleset_v3)
        self.assertTrue(report.ok, report.errors)
        # 静态校验通过，但行为上会把真实的短时入侵静默抑制掉——只能靠回归门禁拦住
        engine = RuleEngine(ruleset_v3)
        context = {"camera_id": "CAM-01", "roi_id": "ROI-A", "dwell_seconds": 90.0,
                   "in_roi": True, "visibility_ok": True, "mean_det_score": 0.9,
                   "authorized": False, "external_records_available": True}
        decision = engine.evaluate("UNAUTHORIZED_INTRUSION", context)
        self.assertEqual(decision.action, "suppress")
        self.assertEqual(decision.rule_id, "R-SUPPRESS-SHORT-DWELL")


if __name__ == "__main__":
    unittest.main()
