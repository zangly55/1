"""端到端管线测试：四阶段串联、授权抑制、采集中断、产物落盘。"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import helpers

from cvalarm.locator import Calibration, Localizer
from cvalarm.pipeline import Pipeline
from cvalarm.rules import Rule, RuleSet


def ruleset() -> RuleSet:
    return RuleSet(
        ruleset_id="pipeline-test", version_label="pt1",
        policy={"default_action": "escalate"},
        created_at="2026-01-01T00:00:00+00:00",
        rules=[
            Rule("R-SAFETY", ["*"], {"any": [{"field": "visibility_ok", "op": "==", "value": False}]},
                 "escalate", priority=200, norm_ref="复核要求", description="可见性不足转人工"),
            Rule("R-SUPPRESS-AUTH", ["UNAUTHORIZED_INTRUSION", "LOITERING"],
                 {"all": [{"field": "authorized", "op": "==", "value": True}]},
                 "suppress", priority=150, norm_ref="作业许可办法", description="有许可则不违规",
                 require_authorization=["work_permit"]),
            Rule("R-INTRUSION", ["UNAUTHORIZED_INTRUSION"],
                 {"all": [{"field": "dwell_seconds", "op": ">=", "value": 10}]},
                 "alarm", priority=80, norm_ref="周界细则", description="滞留达阈值"),
        ])


def authorizations(path: str) -> str:
    payload = {"source": "test", "complete": True, "permits": [{
        "permit_id": "WP-TEST", "kind": "cleaning", "holder": "测试班组",
        "camera_id": "CAM-T", "roi_id": "R1", "start": 100.0, "end": 160.0,
        "scope": ["UNAUTHORIZED_INTRUSION"], "approver": "安全科",
    }]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    return path


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cvalarm-pipe-")
        self.cfg = helpers.default_config()
        self.cfg.set("stage3.authorization_file", authorizations(
            os.path.join(self.tmp, "auth.json")))
        self.cfg.set("runtime.state_dir", self.tmp)
        self.cal = Calibration(version="cal-test", tau_reject=0.10, tau_confirm=0.30,
                               hard_negative_windows=40)

    def _run(self, source, persist=False):
        localizer = Localizer(self.cfg, calibration=self.cal)
        pipeline = Pipeline(self.cfg, source, ruleset=ruleset(), localizer=localizer,
                            persist=persist, out_dir=os.path.join(self.tmp, "run"))
        return pipeline.run()

    def test_confirm_and_suppress(self):
        result = self._run(helpers.TinySource(hours=0.05))
        self.assertEqual(len(result.alarms), 2)
        first, second = result.alarms
        self.assertEqual(first["status"], "confirmed")
        self.assertEqual(first["card"]["decision"], "confirm")
        self.assertEqual(second["status"], "suppressed")
        self.assertEqual(second["card"]["decision"], "dismiss")
        self.assertIn("WP-TEST", json.dumps(second["card"], ensure_ascii=False))

    def test_metrics_and_reliability(self):
        result = self._run(helpers.TinySource(hours=0.05))
        metrics = result.metrics
        self.assertEqual(metrics["events"], 1)
        self.assertEqual(metrics["event_recall"], 1.0)
        self.assertEqual(metrics["false_alarms"], 0)
        self.assertEqual(result.reliability["p1_prefilter"], 1.0)
        self.assertEqual(result.reliability["end_to_end_recall_observed"], 1.0)
        self.assertGreater(result.stats["frames"], 0)

    def test_tta_within_deadline(self):
        result = self._run(helpers.TinySource(hours=0.05))
        tta = result.metrics["tta"]
        self.assertEqual(tta["n"], 1)
        self.assertLess(tta["p50"], 30.0)
        self.assertEqual(tta["deadline_recall"], 1.0)

    def test_card_fields_complete(self):
        result = self._run(helpers.TinySource(hours=0.05))
        card = result.alarms[0]["card"]
        for field_name in ("Event_Class" if False else "event_class", "Temporal_Anchor",
                           "Physical_Fact_Evidence", "Normative_Inference_Uncertainty",
                           "evidence_chain", "signature"):
            self.assertIn(field_name, card)
        self.assertTrue(card["Physical_Fact_Evidence"])
        self.assertEqual(card["Temporal_Anchor"]["keyframes"] != [], True)

    def test_system_error_when_frames_dropped(self):
        result = self._run(helpers.TinySource(hours=0.05, drop_every=2))
        statuses = [a["status"] for a in result.alarms]
        self.assertIn("system_error", statuses)
        triage = result.metrics["triage_counts"]
        self.assertGreaterEqual(triage["SYSTEM_ERROR"], 1)
        # 采集中断不被当作"正常"，也不产生确证告警
        self.assertEqual(result.metrics["event_recall"], 0.0)
        self.assertEqual(result.metrics["false_alarms"], 0)

    def test_persist_artifacts(self):
        result = self._run(helpers.TinySource(hours=0.05), persist=True)
        run_dir = result.run_dir
        for name in ("run_meta.json", "metrics.json", "cost.json", "alarms.jsonl",
                     "candidates.jsonl", "stage2.jsonl", "fsm_audit.jsonl",
                     "audit_samples.jsonl", "run_summary.json"):
            self.assertTrue(os.path.exists(os.path.join(run_dir, name)), name)
        meta = json.load(open(os.path.join(run_dir, "run_meta.json"), encoding="utf-8"))
        self.assertIn("ruleset", meta)
        self.assertEqual(meta["ruleset"]["version_label"], "pt1")
        alarms = [json.loads(l) for l in open(os.path.join(run_dir, "alarms.jsonl"),
                                              encoding="utf-8")]
        self.assertEqual(len(alarms), len(result.alarms))

    def test_cost_included(self):
        result = self._run(helpers.TinySource(hours=0.05))
        money = result.cost["components_money_per_camera_hour"]
        self.assertGreater(money["total"], 0.0)
        self.assertGreater(result.cost["components_gpu_seconds_per_camera_hour"]
                           ["C_always_on_stage1"], 0.0)

    def test_missing_roi_raises(self):
        source = helpers.TinySource(hours=0.02)
        source.rois = []
        with self.assertRaises(ValueError):
            self._run(source)


if __name__ == "__main__":
    unittest.main()
