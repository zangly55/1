"""状态机测试：覆盖论文 3.2 节六个状态与三种植入策略。"""
from __future__ import annotations

import unittest

import helpers

from cvalarm.fsm import ENTERING, LOST, MISSING, OUTSIDE, STAYING, TRIGGERED


APP_A = [1.0, 0.0, 0.0]
APP_B = [0.0, 1.0, 0.0]


class TestEntering(unittest.TestCase):
    def test_debounce_and_t_enter_is_first_crossing(self):
        fsm = helpers.make_fsm(debounce=3)
        helpers.step(fsm, 0.0, appearance=APP_A)
        self.assertEqual(fsm.state, ENTERING)
        helpers.step(fsm, 0.1, appearance=APP_A)
        helpers.step(fsm, 0.2, appearance=APP_A)
        self.assertEqual(fsm.state, STAYING)
        # t_enter 取首帧越界时刻，而不是防抖确认时刻
        self.assertAlmostEqual(fsm.t_enter, 0.0)
        # 防抖等待计入在场时长
        self.assertAlmostEqual(fsm.accum, 0.2, places=6)

    def test_debounce_reset_when_leaving(self):
        fsm = helpers.make_fsm(debounce=3)
        helpers.step(fsm, 0.0, appearance=APP_A)
        helpers.step(fsm, 0.1, inside=False, appearance=APP_A)
        self.assertEqual(fsm.state, OUTSIDE)
        self.assertIsNone(fsm.t_enter)

    def test_frame_failure_does_not_break_debounce(self):
        fsm = helpers.make_fsm(debounce=2)
        helpers.step(fsm, 0.0, appearance=APP_A)
        helpers.step(fsm, 0.1, seen=False, inside=False, frame_ok=False, appearance=APP_A)
        self.assertEqual(fsm.state, ENTERING)
        helpers.step(fsm, 0.2, appearance=APP_A)
        self.assertEqual(fsm.state, STAYING)


class TestDwellTrigger(unittest.TestCase):
    def test_trigger_at_threshold(self):
        fsm = helpers.make_fsm(debounce=2, thr=10.0)
        events = []
        for i in range(0, 110):
            events += helpers.step(fsm, i * 0.1, appearance=APP_A)
        kinds = [e.kind for e in events]
        self.assertIn("entered", kinds)
        self.assertIn("candidate", kinds)
        cand = [e for e in events if e.kind == "candidate"][0]
        self.assertAlmostEqual(cand.payload["t_enter"], 0.0)
        self.assertAlmostEqual(cand.payload["accum_s"], 10.0, delta=0.15)
        self.assertEqual(fsm.state, TRIGGERED)
        self.assertTrue(cand.payload["continuity"]["continuous_verified"])

    def test_no_duplicate_trigger(self):
        fsm = helpers.make_fsm(debounce=2, thr=2.0)
        hits = 0
        for i in range(0, 100):
            for ev in helpers.step(fsm, i * 0.1, appearance=APP_A):
                if ev.kind == "candidate":
                    hits += 1
        self.assertEqual(hits, 1)

    def test_out_of_roi_pauses_accumulation(self):
        fsm = helpers.make_fsm(debounce=2, thr=5.0, exit=3, oop="pause")
        for i in range(0, 20):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        before = fsm.accum
        helpers.step(fsm, 2.0, inside=False, appearance=APP_A)
        self.assertEqual(fsm.state, STAYING)     # 尚未确认离开
        self.assertAlmostEqual(fsm.accum, before, places=6)

    def test_out_of_roi_accumulate_policy(self):
        fsm = helpers.make_fsm(debounce=2, thr=50.0, exit=5, oop="accumulate")
        for i in range(0, 20):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        before = fsm.accum
        helpers.step(fsm, 2.0, inside=False, appearance=APP_A)
        self.assertGreater(fsm.accum, before)


class TestExit(unittest.TestCase):
    def test_exit_requires_consecutive_out_frames(self):
        fsm = helpers.make_fsm(debounce=2, thr=100.0, exit=3)
        for i in range(0, 10):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        events = helpers.step(fsm, 1.0, inside=False, appearance=APP_A)
        self.assertEqual([e.kind for e in events], [])
        helpers.step(fsm, 1.1, inside=False, appearance=APP_A)
        events = helpers.step(fsm, 1.2, inside=False, appearance=APP_A)
        self.assertEqual(events[-1].kind, "exit")
        self.assertEqual(events[-1].payload["outcome"], "EXITED")
        self.assertTrue(fsm.terminal)


class TestOcclusion(unittest.TestCase):
    def test_short_occlusion_keeps_accumulating(self):
        fsm = helpers.make_fsm(debounce=2, thr=20.0, occ=5)
        for i in range(0, 10):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        before = fsm.accum
        for k in range(1, 4):  # 中断 3 帧，未超过 L=5
            helpers.step(fsm, 1.0 + k * 0.1, seen=False, inside=False, appearance=APP_A)
        self.assertEqual(fsm.state, STAYING)
        self.assertGreater(fsm.accum, before)

    def test_occlusion_beyond_tolerance_enters_missing(self):
        fsm = helpers.make_fsm(debounce=2, thr=20.0, occ=3, window=30.0)
        for i in range(0, 10):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        frozen = None
        for k in range(1, 6):
            helpers.step(fsm, 1.0 + k * 0.1, seen=False, inside=False, appearance=APP_A)
        self.assertEqual(fsm.state, MISSING)
        self.assertIsNotNone(fsm.t_lost)
        frozen = fsm.frozen_accum
        self.assertGreater(frozen, 0.0)

    def test_precise_policy_deducts_gap(self):
        fsm = helpers.make_fsm(debounce=2, thr=10.0, occ=2, window=60.0, policy="precise")
        for i in range(0, 20):
            helpers.step(fsm, i * 0.1, appearance=APP_A)      # 0~1.9s
        for k in range(1, 10):
            helpers.step(fsm, 1.9 + k * 0.1, seen=False, inside=False, appearance=APP_A)
        frozen = fsm.frozen_accum
        self.assertEqual(fsm.state, MISSING)
        events = helpers.step(fsm, 5.0, appearance=APP_A)
        kinds = [e.kind for e in events]
        self.assertIn("resumed", kinds)
        self.assertEqual(fsm.state, STAYING)  # 未达阈值
        self.assertAlmostEqual(fsm.accum, frozen, places=6)  # 失踪间隔被扣除
        resumed = [e for e in events if e.kind == "resumed"][0]
        self.assertGreater(resumed.payload["delta_missing_s"], 0.0)
        self.assertEqual(resumed.payload["policy"], "precise")
        self.assertFalse(fsm.snapshot()["continuity"]["continuous_verified"])

    def test_loose_policy_carries_gap(self):
        fsm = helpers.make_fsm(debounce=2, thr=10.0, occ=2, window=60.0, policy="loose")
        for i in range(0, 20):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        for k in range(1, 10):
            helpers.step(fsm, 1.9 + k * 0.1, seen=False, inside=False, appearance=APP_A)
        frozen = fsm.frozen_accum
        helpers.step(fsm, 5.0, appearance=APP_A)
        self.assertGreater(fsm.accum, frozen + 2.0)

    def test_strict_policy_resets(self):
        fsm = helpers.make_fsm(debounce=2, thr=10.0, occ=2, window=60.0, policy="strict")
        for i in range(0, 20):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        for k in range(1, 10):
            helpers.step(fsm, 1.9 + k * 0.1, seen=False, inside=False, appearance=APP_A)
        helpers.step(fsm, 5.0, appearance=APP_A)
        self.assertEqual(fsm.accum, 0.0)

    def test_identity_mismatch_lost(self):
        fsm = helpers.make_fsm(debounce=2, thr=10.0, occ=2, window=60.0)
        for i in range(0, 20):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        for k in range(1, 10):
            helpers.step(fsm, 1.9 + k * 0.1, seen=False, inside=False, appearance=APP_A)
        # 截然不同的外观 + 远处位置 -> 判定为不同身份
        events = helpers.step(fsm, 6.0, appearance=APP_B, x=0.75)
        self.assertEqual(events[-1].kind, "lost")
        self.assertEqual(events[-1].payload["outcome"], "LOST_IDENTITY")
        self.assertTrue(fsm.terminal)

    def test_window_expiry_lost(self):
        fsm = helpers.make_fsm(debounce=2, thr=10.0, occ=2, window=5.0)
        for i in range(0, 20):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        for k in range(1, 10):
            helpers.step(fsm, 1.9 + k * 0.1, seen=False, inside=False, appearance=APP_A)
        events = helpers.step(fsm, 20.0, seen=False, inside=False, appearance=APP_A)
        self.assertEqual(events[-1].kind, "lost")
        self.assertEqual(events[-1].payload["outcome"], "LOST_WINDOW_EXPIRED")
        self.assertTrue(fsm.terminal)

    def test_observation_failure_not_exit(self):
        fsm = helpers.make_fsm(debounce=2, thr=10.0, occ=50)
        for i in range(0, 10):
            helpers.step(fsm, i * 0.1, appearance=APP_A)
        for k in range(1, 6):
            helpers.step(fsm, 1.0 + k * 0.1, seen=False, inside=False, frame_ok=False,
                         appearance=APP_A)
        self.assertEqual(fsm.state, STAYING)      # 丢帧不算离开
        self.assertEqual(fsm.sys_error_frames, 5)

    def test_resumed_candidate_marks_continuity_loss(self):
        fsm = helpers.make_fsm(debounce=2, thr=3.0, occ=2, window=60.0)
        events = []
        for i in range(0, 10):
            events += helpers.step(fsm, i * 0.1, appearance=APP_A)
        for k in range(1, 10):
            events += helpers.step(fsm, 0.9 + k * 0.1, seen=False, inside=False,
                                   appearance=APP_A)
        for j in range(0, 40):
            events += helpers.step(fsm, 3.0 + j * 0.1, appearance=APP_A)
        cands = [e for e in events if e.kind == "candidate"]
        self.assertEqual(len(cands), 1)
        self.assertTrue(cands[0].payload["continuity"]["suspended"])
        self.assertFalse(cands[0].payload["continuity"]["continuous_verified"])
        self.assertEqual(len(cands[0].payload["continuity"]["gaps"]), 1)


if __name__ == "__main__":
    unittest.main()
