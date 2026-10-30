"""跟踪器测试：两级关联、遮挡续轨、预测外推。"""
from __future__ import annotations

import unittest

import helpers  # noqa: F401

from cvalarm.tracker import ByteTracker, KalmanAxis, KalmanBox, cosine_similarity
from cvalarm.types import Detection, Frame


def frame(ts: float, idx: int, dets) -> Frame:
    return Frame(camera_id="C1", frame_idx=idx, ts=ts,
                 detections=[Detection(cls="person", bbox=b, score=s, appearance=a)
                             for (b, s, a) in dets])


def tracker(anchor_mode: str = "bottom_center") -> ByteTracker:
    return ByteTracker({
        "high_thresh": 0.5, "low_thresh": 0.1, "new_track_thresh": 0.55,
        "match_iou": 0.3, "low_match_iou": 0.2, "min_hits": 2, "max_lost_frames": 5,
        "kalman": {"accel_noise": 0.02, "meas_noise": 0.04},
    }, anchor_mode=anchor_mode)


class TestKalman(unittest.TestCase):
    def test_axis_follows_measurement(self):
        axis = KalmanAxis(0.0)
        for i in range(1, 21):
            axis.predict(0.1)
            axis.update(i * 0.02)
        self.assertAlmostEqual(axis.p, 0.4, delta=0.05)
        self.assertGreater(axis.v, 0.0)

    def test_box_predict_is_idempotent_per_timestamp(self):
        box = KalmanBox((0.10, 0.10, 0.20, 0.30), 0.02, 0.04, ts=0.0)
        for i in range(1, 10):
            box.update_at((0.10 + i * 0.01, 0.10, 0.20 + i * 0.01, 0.30), i * 0.1)
        first = box.predict_at(1.5)
        second = box.predict_at(1.5)
        self.assertEqual(first, second)          # 同一时刻重复预测不应重复外推
        third = box.predict_at(2.0)
        self.assertGreater(third[0], first[0])   # 时间推进才继续外推

    def test_cosine(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)
        self.assertEqual(cosine_similarity(None, [1.0]), 0.0)
        self.assertEqual(cosine_similarity([1.0], [1.0, 2.0]), 0.0)


class TestByteTracker(unittest.TestCase):
    def test_track_created_and_confirmed(self):
        t = tracker()
        for i in range(3):
            t.step(frame(i * 0.5, i, [((0.40, 0.20, 0.50, 0.40), 0.9, None)]))
        self.assertEqual(len(t.tracks), 1)
        trk = list(t.tracks.values())[0]
        self.assertTrue(trk.confirmed)

    def test_low_score_keeps_existing_track(self):
        """遮挡导致置信度跌到 high_thresh 以下时，低分框仍应延续原轨迹（ByteTrack 要点）。"""
        t = tracker()
        for i in range(3):
            t.step(frame(i * 0.5, i, [((0.40, 0.20, 0.50, 0.40), 0.9, None)]))
        first_id = list(t.tracks.values())[0].track_id
        # 之后两帧只有低分框（0.3），高于 high_thresh? 不高于，走第二阶段关联
        for i in range(3, 5):
            upd = t.step(frame(i * 0.5, i, [((0.41, 0.20, 0.51, 0.40), 0.3, None)]))
            self.assertTrue(upd.obs[0].seen)
        self.assertEqual(len(t.tracks), 1)
        self.assertEqual(list(t.tracks.values())[0].track_id, first_id)

    def test_new_track_requires_threshold(self):
        t = tracker()
        upd = t.step(frame(0.0, 0, [((0.4, 0.2, 0.5, 0.4), 0.2, None)]))
        self.assertEqual(len(t.tracks), 0)
        self.assertEqual(upd.created, [])

    def test_track_removed_after_max_lost(self):
        t = tracker()
        for i in range(3):
            t.step(frame(i * 0.5, i, [((0.40, 0.20, 0.50, 0.40), 0.9, None)]))
        removal_obs = None
        for i in range(3, 12):
            upd = t.step(frame(i * 0.5, i, []))
            if upd.removed:
                removal_obs = upd.obs
                break
        self.assertIsNotNone(removal_obs)
        self.assertTrue(any(o.seen is False for o in removal_obs))
        self.assertEqual(len(t.tracks), 0)

    def test_class_mismatch_not_matched(self):
        t = tracker()
        t.step(frame(0.0, 0, [((0.4, 0.2, 0.5, 0.4), 0.9, None)]))
        t.step(frame(0.5, 1, [((0.4, 0.2, 0.5, 0.4), 0.9, None)]))
        t.step(Frame(camera_id="C1", frame_idx=2, ts=1.0,
                     detections=[Detection(cls="car", bbox=(0.4, 0.2, 0.5, 0.4), score=0.9)]))
        self.assertEqual(len(t.tracks), 2)  # person 轨迹 + car 新轨迹

    def test_prediction_used_when_unseen(self):
        t = tracker()
        for i in range(3):
            t.step(frame(i * 0.5, i, [((0.30 + i * 0.02, 0.2, 0.40 + i * 0.02, 0.4), 0.9, None)]))
        upd = t.step(frame(1.5, 3, []))
        self.assertEqual(len(upd.obs), 1)
        self.assertFalse(upd.obs[0].seen)
        self.assertGreater(upd.obs[0].pred_anchor[0], 0.30)


if __name__ == "__main__":
    unittest.main()
