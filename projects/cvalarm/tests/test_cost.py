"""成本模型与可靠性链测试。"""
from __future__ import annotations

import math
import unittest

import helpers

from cvalarm.cost import (PipelineStats, TOPOLOGIES, compare_topologies, compute,
                          estimate_egress_bytes)
from cvalarm.reliability import conditional_recall
from cvalarm.types import AlarmRecord, Candidate, GtEvent, Stage2Result

CFG = {
    "topology": "edge-gateway-cascade",
    "price": {"gpu_second": 0.001, "human_hour": 60.0, "egress_gb": 0.1,
              "api_input_token": 0.000001, "api_output_token": 0.000002},
    "stage": {"stage1_gpu_ms_per_frame": 10.0, "stage2_gpu_ms_per_candidate_s": 36.0,
              "stage3_gpu_ms_per_input_s": 3600.0, "encode_bitrate_mbps": 2.0},
    "feedback": {"human_minutes_per_alarm": 5.0,
                 "reflection_minutes_per_camera_week": 0.0},
    "sensitivity": {"r1_range": [0.01, 0.05], "r2_range": [0.05, 0.2], "steps": 5},
}


def stats() -> PipelineStats:
    # 1 机位小时、候选占 1%、r2 = 20%
    return PipelineStats(
        camera_hours=1.0, total_video_seconds=3600.0, frames=7200, dropped_frames=0,
        stage1_gpu_ms=36_000.0,            # 36 GPU 秒 / 机位小时
        candidates=10, candidate_video_seconds=36.0,
        stage2_gpu_ms=360.0,               # 0.36s / 0.01h = 36 GPU 秒 / 候选视频小时
        stage2_processed_seconds=36.0,
        stage3_input_seconds=7.2,          # r2 = 20%
        stage3_gpu_ms=7200.0,              # 7.2s / 0.002h = 3600 GPU 秒 / 输入小时
        stage3_tokens_in=1000, stage3_tokens_out=200, stage3_calls=10,
        displayed_alarms=2, deferred_alarms=0, human_review_minutes=10.0,
        egress_bytes=int(0.1 * 1024 ** 3),
    )


class TestCostFormula(unittest.TestCase):
    def setUp(self):
        self.result = compute(stats(), CFG)

    def test_ratios_measured(self):
        self.assertAlmostEqual(self.result["ratios"]["r1_candidate_video_ratio"], 0.01)
        self.assertAlmostEqual(self.result["ratios"]["r2_stage2_to_stage3_ratio"], 0.2)

    def test_component_values(self):
        comp = self.result["components_gpu_seconds_per_camera_hour"]
        self.assertAlmostEqual(comp["C_always_on_stage1"], 36.0)
        self.assertAlmostEqual(comp["C2_per_candidate_video_hour"], 36.0)
        self.assertAlmostEqual(comp["r1_times_C2"], 0.36)
        self.assertAlmostEqual(comp["C3_per_input_video_hour"], 3600.0)
        self.assertAlmostEqual(comp["r1_r2_times_C3"], 0.01 * 0.2 * 3600.0)
        total = 36.0 + 0.36 + 7.2
        self.assertAlmostEqual(comp["total_gpu_seconds"], total, places=4)

    def test_money_components(self):
        money = self.result["components_money_per_camera_hour"]
        expected_compute = (36.0 + 0.36 + 7.2) * 0.001
        self.assertAlmostEqual(money["compute"], expected_compute, places=4)
        self.assertAlmostEqual(money["egress"], 0.1 * 0.1, places=4)
        self.assertAlmostEqual(money["feedback_human"], (10.0 / 60.0) * 60.0, places=4)
        self.assertAlmostEqual(money["total"],
                               money["compute"] + money["egress"] + money["feedback_human"],
                               places=4)

    def test_sensitivity_matches_paper_range(self):
        sens = self.result["sensitivity"]
        self.assertAlmostEqual(sens["product_min"], 0.0005, places=6)
        self.assertAlmostEqual(sens["product_max"], 0.01, places=6)
        self.assertTrue(sens["matches_paper_range"])

    def test_topology_notes_present(self):
        for topology in TOPOLOGIES:
            result = compute(stats(), CFG, topology=topology)
            self.assertEqual(result["topology"], topology)
            self.assertTrue(result["topology_note"])

    def test_edge_only_has_no_egress(self):
        result = compute(stats(), CFG, topology="edge-only")
        self.assertEqual(result["components_money_per_camera_hour"]["egress"], 0.0)

    def test_cloud_api_priced_by_tokens(self):
        local = compute(stats(), CFG, topology="edge-gateway-cascade")
        cloud = compute(stats(), CFG, topology="edge-cloud-api")
        self.assertNotAlmostEqual(
            local["components_money_per_camera_hour"]["compute"],
            cloud["components_money_per_camera_hour"]["compute"], places=6)

    def test_compare_returns_all_topologies(self):
        rows = compare_topologies(stats(), CFG, cameras=4)
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["topology"] for r in rows], list(TOPOLOGIES))

    def test_totals_scale_with_cameras(self):
        result = compute(stats(), CFG, cameras=10)
        self.assertAlmostEqual(result["totals"]["money_per_day"],
                               10 * 24 * result["components_money_per_camera_hour"]["total"],
                               places=3)

    def test_egress_estimate(self):
        b = estimate_egress_bytes(stats(), CFG)
        self.assertAlmostEqual(b, 36.0 * 2.0 * 1_000_000 / 8.0, delta=1)

    def test_invalid_topology(self):
        with self.assertRaises(ValueError):
            compute(stats(), CFG, topology="edge-magic")


def cand(cid="C1", camera="CAM-01", enter=100.0, trigger=110.0) -> Candidate:
    return Candidate(candidate_id=cid, camera_id=camera, track_id=1, roi_id="R1",
                     event_class="E", t_enter=enter, t_trigger=trigger, accum_s=10.0,
                     dwell_threshold_s=10.0, window=(90.0, 110.0))


def stage2(decision: str) -> Stage2Result:
    return Stage2Result(decision=decision, interval=(90.0, 110.0), score=0.5,
                        raw_score=0.7, tau_confirm=0.5, tau_reject=0.2, margin=0.2)


def alarm(aid="A1", camera="CAM-01", status="confirmed", cid="C1") -> AlarmRecord:
    return AlarmRecord(alarm_id=aid, candidate_id=cid, camera_id=camera, track_id=1,
                       roi_id="R1", event_class="E", t_satisfy=100.0, t_trigger=110.0,
                       t_display=111.0, status=status, triage="EVENT")


class TestReliability(unittest.TestCase):
    def test_chain(self):
        events = [GtEvent("E1", "CAM-01", "E", 100.0, 200.0, "R1"),
                  GtEvent("E2", "CAM-01", "E", 300.0, 400.0, "R1")]
        candidates = [cand("C1", enter=100.0, trigger=110.0),
                      cand("C2", enter=300.0, trigger=310.0)]
        stage2_map = {"C1": stage2("EVENT"), "C2": stage2("INSUFFICIENT_EVIDENCE")}
        alarms = [alarm("A1", cid="C1")]
        result = conditional_recall(events, candidates, stage2_map, alarms)
        self.assertAlmostEqual(result["p1_prefilter"], 1.0)
        self.assertAlmostEqual(result["p2_given_1_localizer"], 0.5)
        self.assertAlmostEqual(result["p3_given_12_verifier"], 1.0)
        self.assertAlmostEqual(result["end_to_end_recall_observed"], 0.5)
        self.assertEqual(result["bottleneck"], "p2_given_1_localizer")
        self.assertEqual([e["lost_at"] for e in result["per_event"]],
                         ["none", "stage2_localizer"])

    def test_prefilter_miss_is_attributed(self):
        events = [GtEvent("E1", "CAM-01", "E", 100.0, 200.0, "R1")]
        result = conditional_recall(events, [], {}, [])
        self.assertEqual(result["p1_prefilter"], 0.0)
        self.assertEqual(result["per_event"][0]["lost_at"], "stage1_prefilter")

    def test_empty(self):
        result = conditional_recall([], [], {}, [])
        self.assertIsNone(result["p1_prefilter"])
        self.assertEqual(result["events"], 0)


if __name__ == "__main__":
    unittest.main()
