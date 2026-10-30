"""几何工具：包围框、多边形 ROI、IoU、锚点。

坐标系约定：图像坐标为归一化 [0,1] 的浮点数，x 向右，y 向下。
包围框统一写成 (x1, y1, x2, y2)，满足 x1 < x2、y1 < y2。
目标锚点默认取包围框底边中心（bottom_center），即人员与地面的接触点，
这也是监控场景中判定"是否位于防区"最稳定的几何量。
"""
from __future__ import annotations

from typing import Sequence

Point = tuple[float, float]
BBox = tuple[float, float, float, float]


def clip01(value: float) -> float:
    return 0.0 if value < 0.0 else (1.0 if value > 1.0 else value)


def normalize_bbox(bbox: Sequence[float]) -> BBox:
    """规范化包围框：保证 x1<=x2、y1<=y2，并裁剪到 [0,1]。"""
    x1, y1, x2, y2 = (float(v) for v in bbox)
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return (clip01(x1), clip01(y1), clip01(x2), clip01(y2))


def bbox_wh(bbox: BBox) -> tuple[float, float]:
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


def bbox_center(bbox: BBox) -> Point:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def bbox_bottom_center(bbox: BBox) -> Point:
    """人员落脚点：底边中心。论文 3.2 节的状态机即以此为 ROI 锚点。"""
    return ((bbox[0] + bbox[2]) / 2.0, bbox[3])


def get_anchor(bbox: BBox, mode: str = "bottom_center") -> Point:
    if mode == "center":
        return bbox_center(bbox)
    if mode == "top_center":
        return ((bbox[0] + bbox[2]) / 2.0, bbox[1])
    return bbox_bottom_center(bbox)


def bbox_area(bbox: BBox) -> float:
    w, h = bbox_wh(bbox)
    return max(0.0, w) * max(0.0, h)


def bbox_iou(a: BBox, b: BBox) -> float:
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    union = bbox_area(a) + bbox_area(b) - inter
    return inter / union if union > 0.0 else 0.0


def bbox_aspect(bbox: BBox) -> float:
    w, h = bbox_wh(bbox)
    return (h / w) if w > 0 else 0.0


def point_distance(a: Point, b: Point) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return (dx * dx + dy * dy) ** 0.5


def point_in_polygon(point: Point, polygon: Sequence[Sequence[float]], boundary_inclusive: bool = True) -> bool:
    """射线法判断点是否在多边形内。

    boundary_inclusive=True 时，落在边界上的点判定为"在内"——
    防区判定的高召回优先原则要求边界处不轻易判为区外。
    boundary_inclusive=False 时先显式排除边界点，避免"左侧边界"被奇偶规则判为内部。
    """
    if not polygon or len(polygon) < 3:
        return False
    x, y = float(point[0]), float(point[1])
    n = len(polygon)
    on_edge = False
    for i in range(n):
        x1, y1 = float(polygon[i][0]), float(polygon[i][1])
        x2, y2 = float(polygon[(i + 1) % n][0]), float(polygon[(i + 1) % n][1])
        if _on_segment(x, y, x1, y1, x2, y2):
            on_edge = True
            break
    if on_edge:
        return bool(boundary_inclusive)
    inside = False
    for i in range(n):
        x1, y1 = float(polygon[i][0]), float(polygon[i][1])
        x2, y2 = float(polygon[(i + 1) % n][0]), float(polygon[(i + 1) % n][1])
        if (y1 > y) != (y2 > y):
            x_cross = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_cross:
                inside = not inside
    return inside


def _on_segment(x: float, y: float, x1: float, y1: float, x2: float, y2: float,
                eps: float = 1e-9) -> bool:
    cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
    if abs(cross) > eps:
        return False
    if min(x1, x2) - eps <= x <= max(x1, x2) + eps and min(y1, y2) - eps <= y <= max(y1, y2) + eps:
        return True
    return False


def polygon_bbox(polygon: Sequence[Sequence[float]]) -> BBox:
    xs = [float(p[0]) for p in polygon]
    ys = [float(p[1]) for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def polygon_area(polygon: Sequence[Sequence[float]]) -> float:
    """鞋带公式，用于校验 ROI 面积是否为退化的 0。"""
    if not polygon or len(polygon) < 3:
        return 0.0
    s = 0.0
    n = len(polygon)
    for i in range(n):
        x1, y1 = float(polygon[i][0]), float(polygon[i][1])
        x2, y2 = float(polygon[(i + 1) % n][0]), float(polygon[(i + 1) % n][1])
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def linear_path(start: Point, end: Point, steps: int) -> list[Point]:
    """生成线性插值路径点（仅用于场景生成与测试）。"""
    if steps <= 1:
        return [tuple(start)]  # type: ignore[list-item]
    out: list[Point] = []
    for i in range(steps):
        t = i / (steps - 1)
        out.append((start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t))
    return out


def clip_bbox_to_frame(bbox: BBox, margin: float = 0.02) -> BBox:
    """把可能溢出画面的预测框裁剪回可视范围（卡尔曼外推可能越界）。"""
    return (clip01(bbox[0] - 0.0), clip01(bbox[1]), clip01(bbox[2] + 0.0), clip01(bbox[3])) \
        if margin <= 0 else (clip01(bbox[0]), clip01(bbox[1]), clip01(bbox[2]), clip01(bbox[3]))


def convex_overlap_ratio(polygon: Sequence[Sequence[float]], bbox: BBox) -> float:
    """粗估多边形与包围框的重叠比例（无 shapely 依赖的工程近似）。

    对 8x8 网格采样：既判定 ROI 覆盖率，也用于场景校验与报告可视化。
    """
    if not polygon:
        return 0.0
    hits = 0
    total = 0
    steps = 8
    for i in range(steps):
        for j in range(steps):
            x = bbox[0] + (bbox[2] - bbox[0]) * (i + 0.5) / steps
            y = bbox[1] + (bbox[3] - bbox[1]) * (j + 0.5) / steps
            total += 1
            if point_in_polygon((x, y), polygon):
                hits += 1
    return hits / total if total else 0.0
