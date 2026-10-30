"""针对工程方向（导师汇报稿）要求的专项测试。

覆盖：双时延口径、定位精度与存在性分开、证据回放块、溯源标记、
资源与模型记录、开发/测试隔离协议、首版单镜头两类事件场景、接口探测。
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import helpers

from cvalarm.config import Config
from cvalarm.evidence import build_evidence, media_info, schematic_svg
from cvalarm.locator import Calibration, Localizer
from cvalarm.metrics import evaluate, localization_metrics, match_alarms
from cvalarm.pipeline import Pipeline
from cvalarm.probe import probe_environment
from cvalarm.rules import Rule, RuleSet
from cvalarm.source import build_v1
from cvalarm.types import AlarmRecord, Candidate, GtEvent

CFG_METRICS = {
    "tta_deadline_s": 30,
    "fa_merge_gap_s": 300,
    "localization": {"tolerance_s": 5.0},
    "event_match": {"interval_iou": 0.3, "point_tolerance_s": 10.0,
                    "pre_tolerance_s": 5.0, "post_tolerance_s": 20.0},
}


def alarm(aid="A1", camera="CAM-01", trigger=100.0, status="confirmed",
          interval=(90.0, 100.0), display=101.0, satisfy=100.0) -> AlarmRecord:
    return AlarmRecord(
        alarm_id=aid, candidate_id="C-" + aid, camera_id=camera, track_id=1, roi_id="R1",
        event_class="UNAUTHORIZED_INTRUSION", t_satisfy=satisfy, t_trigger=trigger,
        t_display=display, status=status, triage="EVENT",
        interval={"start": interval[0], "end": interval[1]})


class TestDualLatency(unittest.TestCase):
    def test_two_tta_definitions(self):
        ev = GtEvent("E1", "CAM-01", "UNAUTHORIZED_INTRUSION", 100.0, 200.0, "R1",
                     satisfy_ts=145.0, evidence_span=(100.0, 200.0))
        al = alarm("A1", trigger=146.0, interval=(86.0, 146.0), display=147.5, satisfy=146.0)
        m = evaluate([ev], [al], {"CAM-01": 1.0}, None, CFG_METRICS)
        # 阈值满足→告警（系统处理时延）
        self.assertAlmostEqual(m["tta"]["p50"], 147.5 - 145.0, places=3)
        # 事件起点→告警（含规程等待）
        self.assertAlmostEqual(m["tta_event_start"]["p50"], 147.5 - 100.0, places=3)
        # 两者差值即规程等待
        self.assertAlmostEqual(m["threshold_delay"]["p50"], 45.0, places=3)
        self.assertIsNone(m["tta_event_start"]["deadline_recall"])

    def test_event_start_deadline_not_comparable_to_processing(self):
        ev = GtEvent("E1", "CAM-01", "UNAUTHORIZED_INTRUSION", 100.0, 1600.0, "R1", satisfy_ts=1545.0,
                     evidence_span=(100.0, 1600.0))
        al = alarm("A1", trigger=1545.0, interval=(1485.0, 1545.0), display=1546.0, satisfy=1545.0)
        m = evaluate([ev], [al], {"CAM-01": 1.0}, None, CFG_METRICS)
        self.assertAlmostEqual(m["tta"]["p50"], 1.0, places=3)
        self.assertGreater(m["tta_event_start"]["p50"], 1000.0)


class TestLocalizationMetrics(unittest.TestCase):
    def test_window_relative_error_is_small(self):
        # 触发时只看得到最后 60 秒：窗口内应对齐，raw 误差被结构性放大
        ev = GtEvent("E1", "CAM-01", "UNAUTHORIZED_INTRUSION", 100.0, 400.0, "R1", evidence_span=(100.0, 400.0))
        al = alarm("A1", trigger=400.0, interval=(340.0, 400.0))
        matching = match_alarms([ev], [al], CFG_METRICS)
        loc = localization_metrics(matching["matched"], [ev], [al],
                                   {**CFG_METRICS, "fsm": {"history_window_s": 60.0}})
        self.assertEqual(loc["n"], 1)
        self.assertAlmostEqual(loc["ref_start_error_s"] if False else loc["ref_start_mae_s"], 0.0,
                               places=3)
        self.assertAlmostEqual(loc["ref_end_mae_s"], 0.0, places=3)
        self.assertAlmostEqual(loc["ref_coverage_mean"], 1.0, places=3)
        # raw 起点误差 = 340-100，被窗口上限放大
        self.assertAlmostEqual(loc["start_mae_s"], 240.0, places=3)
        self.assertAlmostEqual(loc["end_truncation_p50_s"], 0.0, places=3)

    def test_skips_events_without_evidence_span(self):
        ev = GtEvent("E1", "CAM-01", "UNAUTHORIZED_INTRUSION", 100.0, 200.0, "R1")  # 无 evidence_span
        al = alarm("A1")
        matching = match_alarms([ev], [al], CFG_METRICS)
        loc = localization_metrics(matching["matched"], [ev], [al], CFG_METRICS)
        self.assertEqual(loc["n"], 0)
        self.assertEqual(loc["skipped_matched_without_span"], 1)
        self.assertIsNone(loc["start_mae_s"])

    def test_existence_and_localization_are_separate_keys(self):
        ev = GtEvent("E1", "CAM-01", "E", 100.0, 200.0, "R1", evidence_span=(100.0, 200.0))
        al = alarm("A1")
        m = evaluate([ev], [al], {"CAM-01": 1.0}, None, CFG_METRICS)
        self.assertIn("event_recall", m)
        self.assertIn("localization", m)
        self.assertNotIn("event_recall", m["localization"])


class TestEvidence(unittest.TestCase):
    def _candidate(self) -> Candidate:
        return Candidate(
            candidate_id="C1", camera_id="CAM-01", track_id=3, roi_id="ROI-A",
            event_class="UNAUTHORIZED_INTRUSION", t_enter=0.0, t_trigger=45.0, accum_s=45.0,
            dwell_threshold_s=45.0, window=(0.0, 45.0),
            snapshot={"history_boxes": [[0.0, 0.4, 0.3, 0.5, 0.6],
                                        [20.0, 0.5, 0.3, 0.6, 0.6],
                                        [45.0, 0.6, 0.3, 0.7, 0.6]]})

    def test_build_evidence_fields(self):
        cfg = helpers.default_config()
        roi = {"roi_id": "ROI-A", "polygon": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]}
        ev = build_evidence(cfg, self._candidate(), (20.0, 45.0), [roi])
        self.assertTrue(ev["enabled"])
        self.assertAlmostEqual(ev["clip"]["start"], 15.0, places=3)   # 前卷 5 秒
        self.assertGreaterEqual(len(ev["keyframes"]), 3)
        self.assertTrue(all(kf["bbox"] for kf in ev["keyframes"]))
        self.assertFalse(ev["media"]["available"])  # 演示数据源没有视频文件
        self.assertEqual(ev["replay_mode"], "schematic_only")
        self.assertIn("<svg", ev["schematic_svg"])
        self.assertIn("非原始视频帧", ev["schematic_svg"])
        self.assertIn("ROI-A", ev["schematic_svg"])

    def test_media_mapping_makes_replay_available(self):
        tmp = tempfile.mkdtemp(prefix="cvalarm-media-")
        video = os.path.join(tmp, "cam01.mp4")
        with open(video, "wb") as fh:
            fh.write(b"\x00" * 64)
        cfg = helpers.default_config()
        cfg.set("deployment.media.root", tmp)
        cfg.set("deployment.media.cameras", {"CAM-01": "cam01.mp4"})
        info = media_info(cfg, "CAM-01")
        self.assertTrue(info["available"])
        self.assertEqual(info["url_template"], "/media/CAM-01")
        cfg.set("deployment.media.cameras", {"CAM-01": "missing.mp4"})
        self.assertFalse(media_info(cfg, "CAM-01")["available"])

    def test_schematic_without_keyframes(self):
        self.assertEqual(schematic_svg([], []), "")


def _ruleset() -> RuleSet:
    return RuleSet(ruleset_id="t", version_label="t1", policy={}, created_at="",
                   rules=[Rule("R1", ["UNAUTHORIZED_INTRUSION"],
                               {"all": [{"field": "dwell_seconds", "op": ">=", "value": 10}]},
                               "alarm", priority=80, norm_ref="细则", description="滞留")])


class TestProvenanceAndResources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cvalarm-docx-")
        self.cfg = helpers.default_config()
        self.cfg.set("runtime.state_dir", self.tmp)
        self.cfg.set("stage3.authorization_file", os.path.join(self.tmp, "none.json"))

    def _run(self, **cfg_sets):
        for key, value in cfg_sets.items():
            self.cfg.set(key.replace("__", "."), value)
        localizer = Localizer(self.cfg, calibration=Calibration(
            version="cal", tau_reject=0.1, tau_confirm=0.3, hard_negative_windows=40))
        pipeline = Pipeline(self.cfg, helpers.TinySource(hours=0.04), ruleset=_ruleset(),
                            localizer=localizer, persist=False,
                            out_dir=os.path.join(self.tmp, "run"))
        return pipeline.run()

    def test_provenance_on_card_and_run(self):
        result = self._run()
        card = result.alarms[0]["card"]
        self.assertEqual(card["provenance"]["verifier"], "rule_based_reference")
        self.assertEqual(card["provenance"]["replay_mode"], "offline_replay")
        self.assertIn("claim", card["provenance"])
        self.assertEqual(result.meta["provenance"]["data_source"], "test")
        self.assertEqual(result.meta["protocol"]["mode"], "none")

    def test_evidence_block_on_card(self):
        result = self._run()
        ev = result.alarms[0]["card"]["evidence"]
        self.assertTrue(ev["enabled"])
        self.assertIn("clip", ev)
        self.assertIn("manifest", ev)

    def test_resources_recorded(self):
        result = self._run()
        res = result.meta["resources"]
        self.assertGreater(res["frames"], 0)
        self.assertGreater(res["wall_seconds"], 0.0)
        self.assertIn("actual_calls", res)
        self.assertGreaterEqual(res["actual_calls"]["stage2_localizer"], 1)
        self.assertFalse(res["gpu"]["used"])
        self.assertIn("peak_memory_mb", res)

    def test_models_manifest(self):
        result = self._run()
        models = result.meta["models"]
        for key in ("detector", "localizer", "verifier"):
            self.assertIn(key, models)
        self.assertEqual(models["verifier"]["id"], "rule-based-reference")
        self.assertTrue(models["localizer"]["id"])

    def test_capabilities_declared(self):
        result = self._run()
        caps = result.meta["capabilities"]
        self.assertEqual(caps["live_stream_ingest"]["status"], "deferred")
        self.assertEqual(caps["evidence_replay"]["status"], "implemented")
        self.assertIn("multi_agent", caps)

    def test_difficult_cases_panel_data(self):
        result = self._run()
        dc = result.metrics["difficult_cases"]
        self.assertIn("short_stay", dc)
        self.assertIn("evidence_incomplete", dc)
        self.assertIn("no_event_windows", dc)
        for key in ("short_stay", "authorized_suppressed", "insufficient_evidence"):
            self.assertIn(key, dc["counts"])


class TestProtocolHoldout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cvalarm-proto-")
        self.cfg = helpers.default_config()
        self.cfg.set("runtime.state_dir", self.tmp)
        self.cfg.set("stage3.authorization_file", os.path.join(self.tmp, "none.json"))
        self.cfg.set("protocol.mode", "holdout")
        self.cfg.set("protocol.dev", {"cameras": ["CAM-T"], "time_ranges": [[0.0, 20.0]]})
        self.cfg.set("protocol.test", {"cameras": ["CAM-T"], "time_ranges": [[20.0, 200.0]]})
        self.cfg.set("feedback.audit_windows_per_camera_hour", 400.0)
        self.cfg.set("feedback.audit_window_s", 5.0)

    def _run(self):
        localizer = Localizer(self.cfg, calibration=Calibration(
            version="cal", tau_reject=0.1, tau_confirm=0.3, hard_negative_windows=40))
        return Pipeline(self.cfg, helpers.TinySource(hours=0.12), ruleset=_ruleset(),
                        localizer=localizer, persist=False,
                        out_dir=os.path.join(self.tmp, "run")).run()

    def test_events_and_hours_filtered_to_test_split(self):
        result = self._run()
        proto = result.meta["protocol"]
        self.assertTrue(proto["applied"])
        self.assertEqual(proto["events_in_test"], 1)      # T1(20-70) 落在测试段
        self.assertLess(result.metrics["evaluable_video_hours"], 0.12)
        self.assertEqual(result.metrics["protocol"]["mode"], "holdout")

    def test_audit_windows_only_from_dev(self):
        result = self._run()
        samples = result.audit_samples
        self.assertTrue(samples)
        self.assertTrue(all(s["split"] == "dev" for s in samples))
        self.assertTrue(all(s["window_end"] <= 20.5 for s in samples))
        self.assertGreater(result.meta["protocol"]["audit_windows_skipped"], 0)


class TestV1Scope(unittest.TestCase):
    def test_single_camera_two_event_classes(self):
        src = build_v1(hours=1.2)
        self.assertEqual(len(src.cameras), 1)
        classes = {r.event_class for r in src.rois}
        self.assertEqual(classes, {"UNAUTHORIZED_INTRUSION", "UNAUTHORIZED_DWELL"})
        rois = {r.roi_id: r for r in src.rois}
        self.assertAlmostEqual(rois["ROI-A"].dwell_threshold_s, 45.0)
        self.assertAlmostEqual(rois["ROI-D"].dwell_threshold_s, 300.0)
        self.assertEqual({e.event_class for e in src.gt_events},
                         {"UNAUTHORIZED_INTRUSION", "UNAUTHORIZED_DWELL"})
        self.assertTrue(all(e.evidence_span for e in src.gt_events))

    def test_v1_frames_carry_both_event_kinds(self):
        src = build_v1(hours=1.2)
        frames = list(src.iter_frames())
        self.assertTrue(frames)
        self.assertTrue(all(f.camera_id == "CAM-01" for f in frames))


class TestProbe(unittest.TestCase):
    def test_probe_rows_and_status(self):
        cfg = helpers.default_config()
        with tempfile.TemporaryDirectory() as tmp:
            cfg.set("runtime.state_dir", tmp)
            result = probe_environment(cfg, call=False)
        rows = {r["component"]: r for r in result["rows"]}
        for key in ("ruleset", "calibration", "authorizations", "vlm_endpoint",
                    "media_replay", "interval_scorer", "detector_input"):
            self.assertIn(key, rows)
        # 未配置 VLM 端点时必须如实写未配置，而不是假装通过
        self.assertEqual(rows["vlm_endpoint"]["status"], "warn")
        self.assertIn("未配置", rows["vlm_endpoint"]["detail"])
        self.assertEqual(rows["media_replay"]["status"], "warn")
        self.assertIn("summary", result)
        self.assertTrue(result["ok"])  # 没有 fail 项


if __name__ == "__main__":
    unittest.main()
