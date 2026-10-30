"""几何与基础工具测试。"""
from __future__ import annotations

import math
import unittest

import helpers  # noqa: F401  (把工程加入 sys.path)

from cvalarm.geometry import (bbox_aspect, bbox_bottom_center, bbox_iou, convex_overlap_ratio,
                              get_anchor, normalize_bbox, point_in_polygon, polygon_area)
from cvalarm.util import (content_hash, percentile, safe_div, sha256_hex, wilson_interval)


SQUARE = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
TRIANGLE = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]


class TestPolygon(unittest.TestCase):
    def test_inside_outside(self):
        self.assertTrue(point_in_polygon((0.5, 0.5), SQUARE))
        self.assertFalse(point_in_polygon((1.5, 0.5), SQUARE))
        self.assertTrue(point_in_polygon((0.1, 0.1), TRIANGLE))
        self.assertFalse(point_in_polygon((0.8, 0.8), TRIANGLE))

    def test_boundary_inclusive(self):
        self.assertTrue(point_in_polygon((0.0, 0.5), SQUARE))
        self.assertFalse(point_in_polygon((0.0, 0.5), SQUARE, boundary_inclusive=False))

    def test_degenerate_polygon(self):
        self.assertFalse(point_in_polygon((0.0, 0.0), []))
        self.assertFalse(point_in_polygon((0.0, 0.0), [[0, 0], [1, 1]]))
        self.assertEqual(polygon_area([[0, 0], [1, 1]]), 0.0)

    def test_polygon_area(self):
        self.assertAlmostEqual(polygon_area(SQUARE), 1.0)
        self.assertAlmostEqual(polygon_area(TRIANGLE), 0.5)

    def test_overlap_ratio(self):
        self.assertAlmostEqual(convex_overlap_ratio(SQUARE, (0.0, 0.0, 1.0, 1.0)), 1.0)
        self.assertAlmostEqual(convex_overlap_ratio(SQUARE, (2.0, 2.0, 3.0, 3.0)), 0.0)


class TestBBox(unittest.TestCase):
    def test_normalize_and_anchor(self):
        self.assertEqual(normalize_bbox((0.6, 0.7, 0.4, 0.5)), (0.4, 0.5, 0.6, 0.7))
        self.assertEqual(normalize_bbox((-1.0, -1.0, 2.0, 2.0)), (0.0, 0.0, 1.0, 1.0))
        bx, by = bbox_bottom_center((0.2, 0.2, 0.4, 0.6))
        self.assertAlmostEqual(bx, 0.3)
        self.assertAlmostEqual(by, 0.6)
        cx, cy = get_anchor((0.2, 0.2, 0.4, 0.6), "center")
        self.assertAlmostEqual(cx, 0.3)
        self.assertAlmostEqual(cy, 0.4)

    def test_iou(self):
        self.assertAlmostEqual(bbox_iou((0, 0, 1, 1), (0, 0, 1, 1)), 1.0)
        self.assertAlmostEqual(bbox_iou((0, 0, 1, 1), (1, 1, 2, 2)), 0.0)
        # 交并比：交 0.25 / 并 1.75
        self.assertAlmostEqual(bbox_iou((0, 0, 1, 1), (0.5, 0.5, 1.5, 1.5)), 0.25 / 1.75)

    def test_aspect(self):
        self.assertAlmostEqual(bbox_aspect((0.0, 0.0, 0.1, 0.3)), 3.0)
        self.assertEqual(bbox_aspect((0.0, 0.0, 0.0, 0.3)), 0.0)


class TestUtil(unittest.TestCase):
    def test_hash_stability(self):
        self.assertEqual(content_hash({"a": 1, "b": [1, 2]}), content_hash({"b": [1, 2], "a": 1}))
        self.assertNotEqual(content_hash({"a": 1}), content_hash({"a": 2}))
        self.assertEqual(len(sha256_hex("x")), 64)

    def test_percentile(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(percentile(vals, 0.5), 2.5)
        self.assertAlmostEqual(percentile(vals, 0.0), 1.0)
        self.assertAlmostEqual(percentile(vals, 1.0), 4.0)
        self.assertTrue(math.isnan(percentile([], 0.5)))

    def test_safe_div(self):
        self.assertEqual(safe_div(1, 0), 0.0)
        self.assertEqual(safe_div(1, 0, default=-1), -1)
        self.assertEqual(safe_div(4, 2), 2.0)

    def test_wilson(self):
        lo, hi = wilson_interval(0, 10)
        self.assertLess(lo, hi)
        self.assertAlmostEqual(lo, 0.0, places=6)
        lo2, hi2 = wilson_interval(5, 10)
        self.assertLess(lo2, 0.5)
        self.assertGreater(hi2, 0.5)
        self.assertEqual(wilson_interval(0, 0), (0.0, 1.0))


if __name__ == "__main__":
    unittest.main()
