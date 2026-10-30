"""Stage2 测试：Kadane 解码、标定、三向分流。"""
from __future__ import annotations

import unittest

import helpers

from cvalarm.locator import (EVENT, INSUFFICIENT, NO_EVENT, SYSTEM_ERROR, Calibration,
                             HeuristicScorer, Localizer, calibrate, kadane)
from cvalarm.types import Candidate, FrameFeature


def features(n: int = 10, ts0: float = 0.0, roi: str = "R1", persons: float = 0.0,
             score: float = 0.0, motion: float = 0.0, aspect: float = 0.0,
             ok: bool = True, snr: float = 26.0):
    out = []
    for i in range(n):
        out.append(FrameFeature(camera_id="CAM-T", ts=ts0 + i, ok=ok,
                                frame_idx=i, max_score=score, person_count=persons,
                                roi_persons={roi: persons}, motion=motion, snr=snr,
                                mean_person_aspect=aspect))
    return out


def candidate(threshold: float = 5.0, t_enter: float = 0.0, window=(0.0, 10.0)) -> Candidate:
    return Candidate(
        candidate_id="C1", camera_id="CAM-T", track_id=1, roi_id="R1",
        event_class="UNAUTHORIZED_INTRUSION", t_enter=t_enter, t_trigger=window[1],
        accum_s=threshold, dwell_threshold_s=threshold, window=window,
    )


def localizer(tau_reject: float = 0.25, tau_confirm: float = 0.5,
              ok: bool = True) -> Localizer:
    cfg = helpers.default_config()
    cal = Calibration(version="cal-test" if ok else "uncalibrated",
                      tau_reject=tau_reject, tau_confirm=tau_confirm,
                      hard_negative_windows=40 if ok else 0)
    return Localizer(cfg, calibration=cal)


class TestKadane(unittest.TestCase):
    def test_all_negative_still_returns_nonempty(self):
        start, end, best = kadane([-1.0, -2.0, -3.0])
        self.assertEqual((start, end), (0, 0))
        self.assertAlmostEqual(best, -1.0)

    def test_max_subarray(self):
        start, end, best = kadane([1.0, -2.0, 3.0, 0.5, -1.0])
        self.assertEqual((start, end), (2, 3))
        self.assertAlmostEqual(best, 3.5)

    def test_empty(self):
        self.assertEqual(kadane([]), (0, 0, 0.0))

    def test_with_baseline_shift(self):
        # 减去基线后，全负的窗口仍会挑一个"相对最高"的片段 -> 必须外挂存在性校验
        adjusted = [0.9 - 0.5, 0.8 - 0.5, 0.85 - 0.5]
        start, end, best = kadane(adjusted)
        self.assertEqual((start, end), (0, 2))
        self.assertGreater(best, 0.0)


class TestCalibration(unittest.TestCase):
    def test_insufficient_negatives_marks_uncalibrated(self):
        cal = calibrate([0.1, 0.2], min_negatives=20)
        self.assertFalse(cal.is_ok)
        self.assertEqual(cal.version, "uncalibrated")

    def test_calibration_from_distribution(self):
        negatives = [0.01, 0.02, 0.03, 0.05] * 10
        cal = calibrate(negatives, min_negatives=20)
        self.assertTrue(cal.is_ok)
        self.assertLess(cal.tau_reject, cal.tau_confirm)
        self.assertGreaterEqual(cal.tau_reject, 0.05)
        self.assertEqual(cal.hard_negative_windows, 40)

    def test_confirm_gap_respected(self):
        cal = calibrate([0.01] * 40, min_negatives=20, confirm_gap=0.3)
        self.assertAlmostEqual(cal.tau_confirm - cal.tau_reject, 0.3, places=6)


class TestBins(unittest.TestCase):
    def test_bin_count_and_occupancy(self):
        lz = localizer()
        bins = lz.build_bins(candidate(window=(0.0, 10.0)),
                             features(10, persons=1.0, score=0.9, motion=0.3, aspect=2.6))
        self.assertEqual(len(bins), 10)
        self.assertAlmostEqual(bins[0].occupancy, 1.0)
        self.assertAlmostEqual(bins[0].det_score, 0.9)
        self.assertTrue(bins[0].ok)

    def test_missing_frames_mark_bin_unusable(self):
        lz = localizer()
        bins = lz.build_bins(candidate(), features(10, ok=False))
        self.assertTrue(all(not b.ok for b in bins))


class TestTriage(unittest.TestCase):
    def test_event(self):
        lz = localizer(tau_reject=0.1, tau_confirm=0.4)
        res = lz.run(candidate(), features(10, persons=1.0, score=0.9, motion=0.3, aspect=2.6))
        self.assertEqual(res.decision, EVENT)
        self.assertIsNotNone(res.interval)
        self.assertTrue(res.calibration_ok)

    def test_no_event_when_calibrated_and_low(self):
        lz = localizer(tau_reject=0.25, tau_confirm=0.5)
        res = lz.run(candidate(), features(10))
        self.assertEqual(res.decision, NO_EVENT)

    def test_uncalibrated_low_score_goes_to_human(self):
        lz = localizer(tau_reject=0.25, tau_confirm=0.5, ok=False)
        res = lz.run(candidate(), features(10))
        self.assertEqual(res.decision, INSUFFICIENT)
        self.assertFalse(res.calibration_ok)

    def test_insufficient_when_snr_low(self):
        lz = localizer(tau_reject=0.1, tau_confirm=0.4)
        res = lz.run(candidate(), features(10, persons=1.0, score=0.6, snr=5.0))
        self.assertEqual(res.decision, INSUFFICIENT)
        self.assertTrue(any("信噪比" in r for r in res.reasons))

    def test_system_error_when_frames_dropped(self):
        lz = localizer(tau_reject=0.1, tau_confirm=0.4)
        feats = features(10, persons=1.0, score=0.9)
        for f in feats[:4]:
            f.ok = False
        res = lz.run(candidate(), feats)
        self.assertEqual(res.decision, SYSTEM_ERROR)
        self.assertGreater(res.validity["dropped_ratio"], 0.15)

    def test_occlusion_explained_by_state_machine_is_not_downgraded(self):
        lz = localizer(tau_reject=0.1, tau_confirm=0.4)
        cand = candidate()
        cand.continuity = {"suspended": True, "gaps": [{"delta_s": 90.0}],
                           "policy": "precise", "continuous_verified": False}
        feats = features(10, persons=1.0, score=0.9, motion=0.3, aspect=2.6)
        for f in feats[:6]:
            f.roi_persons = {"R1": 0.0}
        res = lz.run(cand, feats)
        self.assertEqual(res.decision, EVENT)
        self.assertTrue(res.validity["occlusion_explained"])

    def test_audit_sample_not_penalized_for_absent_target(self):
        lz = localizer(tau_reject=0.25, tau_confirm=0.5)
        cand = candidate(t_enter=10.0)
        cand.flags = ["audit_sample"]
        res = lz.run(cand, features(10))
        self.assertEqual(res.decision, NO_EVENT)


class TestScorer(unittest.TestCase):
    def test_weights_normalized(self):
        scorer = HeuristicScorer({"roi_occupancy": 2, "dwell_progress": 2, "motion": 2,
                                  "det_score": 2, "size_consistency": 2})
        self.assertAlmostEqual(sum(scorer.w.values()), 1.0)

    def test_audit_dwell_progress_zeroed(self):
        lz = localizer()
        cand = candidate()
        cand.flags = ["audit_sample"]
        bins = lz.build_bins(cand, features(10, persons=1.0))
        scores = HeuristicScorer({}).score(cand, bins)
        # 只有占用率一项有贡献：0.34
        self.assertAlmostEqual(scores[0], 0.34, delta=0.01)


if __name__ == "__main__":
    unittest.main()
