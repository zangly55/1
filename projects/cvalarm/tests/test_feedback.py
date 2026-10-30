"""人工反馈与抽样审计测试。"""
from __future__ import annotations

import os
import tempfile
import unittest

import helpers

from cvalarm.feedback import (AuditStore, FeedbackEntry, FeedbackStore, estimate_miss_rate)


class TestFeedbackStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cvalarm-fb-")
        self.cfg = helpers.default_config()
        self.store = FeedbackStore(self.cfg, self.tmp)

    def test_confirm_entry(self):
        entry = self.store.add(FeedbackEntry(alarm_id="A1", verdict="confirm",
                                             camera_id="CAM-01", event_class="E"))
        self.assertEqual(entry["verdict"], "confirm")
        self.assertEqual(len(self.store.entries()), 1)

    def test_dismiss_requires_reason(self):
        with self.assertRaises(ValueError):
            self.store.add(FeedbackEntry(alarm_id="A1", verdict="dismiss"))

    def test_unknown_reason_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add(FeedbackEntry(alarm_id="A1", verdict="dismiss",
                                         reason_code="NOT_A_CODE"))

    def test_invalid_verdict(self):
        with self.assertRaises(ValueError):
            self.store.add(FeedbackEntry(alarm_id="A1", verdict="ignore"))

    def test_summary_and_reason_counts(self):
        self.store.add(FeedbackEntry("A1", "confirm"))
        self.store.add(FeedbackEntry("A2", "dismiss", reason_code="REFLECTION_OR_SHADOW"))
        self.store.add(FeedbackEntry("A3", "dismiss", reason_code="REFLECTION_OR_SHADOW"))
        self.store.add(FeedbackEntry("A4", "uncertain"))
        summary = self.store.summary()
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["dismiss"], 2)
        self.assertAlmostEqual(summary["dismiss_rate"], 0.5)
        self.assertIn("选择偏差", summary["selection_bias_note"])
        self.assertEqual(self.store.reason_counts()["REFLECTION_OR_SHADOW"], 2)


class TestAuditStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cvalarm-audit-")
        self.cfg = helpers.default_config()
        self.store = AuditStore(self.cfg, self.tmp)

    def test_add_and_summarise(self):
        n = self.store.add([{"camera_id": "CAM-01", "window_start": 0.0,
                             "window_end": 30.0, "decision": "NO_EVENT"}])
        self.assertEqual(n, 1)
        summary = self.store.summary()
        self.assertEqual(summary["samples"], 1)
        self.assertTrue(summary["blind"])
        self.assertEqual(summary["by_decision"]["NO_EVENT"], 1)


class TestMissEstimate(unittest.TestCase):
    def test_estimate_with_wilson(self):
        samples = [
            {"window_start": 0.0, "window_end": 30.0, "decision": "NO_EVENT",
             "event_in_window": True},
            {"window_start": 30.0, "window_end": 60.0, "decision": "EVENT",
             "event_in_window": True},
            {"window_start": 60.0, "window_end": 90.0, "decision": "NO_EVENT",
             "event_in_window": False},
        ]
        cfg = helpers.default_config()
        result = estimate_miss_rate(samples, cfg, camera_hours=1.0)
        self.assertEqual(result["event_containing_windows"], 2)
        self.assertEqual(result["missed_by_prefilter"], 1)
        self.assertAlmostEqual(result["estimated_miss_rate"], 0.5)
        self.assertLess(result["ci95"][0], 0.5)
        self.assertGreater(result["ci95"][1], 0.5)
        self.assertAlmostEqual(result["time_coverage"], 90.0 / 3600.0)

    def test_no_event_windows(self):
        result = estimate_miss_rate([{"window_start": 0.0, "window_end": 30.0,
                                      "decision": "NO_EVENT", "event_in_window": False}],
                                    helpers.default_config(), camera_hours=1.0)
        self.assertIsNone(result["estimated_miss_rate"])


if __name__ == "__main__":
    unittest.main()
