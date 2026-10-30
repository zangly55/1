"""评测口径测试：ROC-AUC、事件匹配、FA/CH、TTA。"""
from __future__ import annotations

import math
import unittest

import helpers

from cvalarm.metrics import (evaluate, interval_iou, match_alarms, merge_false_alarms,
                             no_event_rejection, roc_auc)
from cvalarm.types import AlarmRecord, GtEvent

CFG = {"tta_deadline_s": 30, "fa_merge_gap_s": 300,
       "event_match": {"interval_iou": 0.3, "point_tolerance_s": 10.0,
                       "pre_tolerance_s": 5.0, "post_tolerance_s": 20.0}}


def alarm(alarm_id, camera="CAM-01", trigger=100.0, status="confirmed",
          interval=(90.0, 100.0), display=101.0, satisfy=100.0) -> AlarmRecord:
    return AlarmRecord(
        alarm_id=alarm_id, candidate_id="C-" + alarm_id, camera_id=camera, track_id=1,
        roi_id="R1", event_class="UNAUTHORIZED_INTRUSION", t_satisfy=satisfy,
        t_trigger=trigger, t_display=display, status=status, triage="EVENT",
        interval={"start": interval[0], "end": interval[1]})


def event(event_id="E1", camera="CAM-01", start=100.0, end=200.0, satisfy=100.0,
          kind="interval") -> GtEvent:
    return GtEvent(event_id, camera, "UNAUTHORIZED_INTRUSION", start, end, "R1",
                   kind=kind, satisfy_ts=satisfy)


class TestRocAuc(unittest.TestCase):
    def test_perfect_separation(self):
        self.assertAlmostEqual(roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0)

    def test_reversed(self):
        self.assertAlmostEqual(roc_auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]), 0.0)

    def test_ties_are_half(self):
        self.assertAlmostEqual(roc_auc([0, 1], [0.5, 0.5]), 0.5)

    def test_undefined_when_single_class(self):
        self.assertTrue(math.isnan(roc_auc([1, 1, 1], [0.1, 0.2, 0.3])))
        self.assertTrue(math.isnan(roc_auc([], [])))

    def test_length_mismatch(self):
        self.assertTrue(math.isnan(roc_auc([0, 1], [0.1])))


class TestIntervalIoU(unittest.TestCase):
    def test_iou(self):
        self.assertAlmostEqual(interval_iou((0, 10), (0, 10)), 1.0)
        self.assertAlmostEqual(interval_iou((0, 10), (10, 20)), 0.0)
        self.assertAlmostEqual(interval_iou((0, 10), (5, 15)), 5.0 / 15.0)


class TestMatching(unittest.TestCase):
    def test_true_positive(self):
        result = match_alarms([event()], [alarm("A1")], CFG)
        self.assertEqual(result["per_event"][0]["status"], "TP")
        self.assertEqual(len(result["false_alarms"]), 0)

    def test_false_alarm(self):
        result = match_alarms([], [alarm("A1")], CFG)
        self.assertEqual(len(result["false_alarms"]), 1)

    def test_one_to_one(self):
        result = match_alarms([event()], [alarm("A1", trigger=110.0),
                                          alarm("A2", trigger=120.0)], CFG)
        self.assertEqual(result["per_event"][0]["status"], "TP")
        self.assertEqual(result["duplicate_alarms"], 1)
        self.assertEqual(len(result["false_alarms"]), 0)  # 重复提示负担单列，不冒充误报

    def test_trigger_before_event_window_within_tolerance(self):
        # 告警在事件起点前 5 秒内仍算命中（证据区间必然在条件成立之前）
        result = match_alarms([event(start=100.0)], [alarm("A1", trigger=96.0,
                                                           interval=(80.0, 96.0))], CFG)
        self.assertEqual(result["per_event"][0]["status"], "TP")

    def test_trigger_far_before_is_not_match(self):
        result = match_alarms([event(start=100.0)], [alarm("A1", trigger=80.0,
                                                           interval=(70.0, 80.0))], CFG)
        self.assertEqual(result["per_event"][0]["status"], "MISS")

    def test_cross_camera_not_matched(self):
        result = match_alarms([event(camera="CAM-02")], [alarm("A1", camera="CAM-01")], CFG)
        self.assertEqual(result["per_event"][0]["status"], "MISS")

    def test_interval_iou_can_match(self):
        alarm_iv = alarm("A1", trigger=250.0, interval=(150.0, 250.0))
        alarm_iv.t_trigger = 250.0
        result = match_alarms([event(start=240.0, end=260.0)], [alarm_iv], CFG)
        self.assertEqual(result["per_event"][0]["status"], "TP")

    def test_deferred_counts_as_displayed(self):
        result = match_alarms([event()], [alarm("A1", status="deferred")], CFG)
        self.assertEqual(result["per_event"][0]["status"], "TP")
        self.assertEqual(result["per_event"][0]["alarm_status"], "deferred")

    def test_suppressed_is_not_displayed(self):
        result = match_alarms([event()], [alarm("A1", status="suppressed")], CFG)
        self.assertEqual(result["displayed"], [])
        self.assertEqual(result["per_event"][0]["status"], "MISS")


class TestFalseAlarmMerging(unittest.TestCase):
    def test_merge_within_gap(self):
        items = [alarm("A1", trigger=100.0), alarm("A2", trigger=150.0),
                 alarm("A3", trigger=500.0)]
        merged = merge_false_alarms(items, 300.0)
        self.assertEqual(len(merged), 2)

    def test_merge_is_per_camera(self):
        items = [alarm("A1", camera="CAM-01", trigger=100.0),
                 alarm("A2", camera="CAM-02", trigger=110.0)]
        # 每个机位各留一次
        self.assertEqual(len(merge_false_alarms(items, 300.0)), 2)


class TestEvaluate(unittest.TestCase):
    def test_full_metrics(self):
        alarms = [alarm("A1", trigger=110.0, interval=(50.0, 110.0), display=111.0, satisfy=110.0)]
        metrics = evaluate([event(satisfy=110.0)], alarms, {"CAM-01": 2.0},
                           [(1, 0.9), (1, 0.8), (0, 0.1), (0, 0.2)], CFG)
        self.assertEqual(metrics["events"], 1)
        self.assertAlmostEqual(metrics["event_recall"], 1.0)
        self.assertEqual(metrics["false_alarms"], 0)
        self.assertAlmostEqual(metrics["frame_roc_auc"], 1.0)
        self.assertAlmostEqual(metrics["tta"]["p50"], 1.0)
        self.assertAlmostEqual(metrics["tta"]["deadline_recall"], 1.0)
        self.assertEqual(metrics["per_camera"][0]["camera_id"], "CAM-01")

    def test_fa_per_camera_hour_uses_valid_hours(self):
        alarms = [alarm("A1", trigger=1000.0), alarm("A2", trigger=1005.0)]
        metrics = evaluate([], alarms, {"CAM-01": 4.0}, None, CFG)
        # 两次误报在合并窗口内 -> 1 次 / 4 小时
        self.assertAlmostEqual(metrics["false_alarms_per_camera_hour"], 0.25)

    def test_missed_event(self):
        metrics = evaluate([event()], [], {"CAM-01": 1.0}, None, CFG)
        self.assertEqual(metrics["event_recall"], 0.0)
        self.assertEqual(metrics["event_missed"], 1)

    def test_no_frames_scores(self):
        metrics = evaluate([], [], {}, None, CFG)
        self.assertIsNone(metrics["frame_roc_auc"])


class TestNoEventRejection(unittest.TestCase):
    def test_rate_and_ci(self):
        samples = [{"decision": "NO_EVENT", "silent": True}] * 8 + \
                  [{"decision": "EVENT", "silent": False}] * 2
        summary = no_event_rejection(samples)
        self.assertAlmostEqual(summary["rejection_rate"], 0.8)
        self.assertEqual(summary["windows"], 10)
        self.assertEqual(summary["ci95"][0] < 0.8 < summary["ci95"][1], True)

    def test_empty(self):
        summary = no_event_rejection([])
        self.assertIsNone(summary["rejection_rate"])


if __name__ == "__main__":
    unittest.main()
