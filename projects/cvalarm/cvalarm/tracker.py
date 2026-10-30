"""Stage1 检测-跟踪层：ByteTrack 式两级数据关联 + 常速度卡尔曼预测。

为什么需要两级关联（论文 3.1 节）：
    只保留高分框会在短时遮挡后切断轨迹（ID Switch / 轨迹碎裂）。
    ByteTrack 先关联高分框，再把低分框与已有轨迹的预测框匹配，
    使置信度跌到检测阈值以下的同一目标仍能延续轨迹。

本模块不依赖 numpy / scipy：卡尔曼滤波用 2x2 解析式，匹配用贪心 IoU 指派。
对于监控场景（每路每帧数个目标）贪心与匈牙利解一致的概率很高；
若目标密集，可替换 `associate()` 为最优指派而不影响其它模块。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import BBox, bbox_bottom_center, bbox_iou, clip01, get_anchor
from .types import Detection, Frame, TrackObs
from .util import get_logger

LOG = get_logger("cvalarm.tracker")


# --------------------------------------------------------------------------- 卡尔曼


class KalmanAxis:
    """单轴常速度卡尔曼滤波（状态 [p, v]）。"""

    __slots__ = ("p", "v", "p00", "p01", "p11", "q", "r")

    def __init__(self, pos: float, accel_noise: float = 0.02, meas_noise: float = 0.04) -> None:
        self.p = float(pos)
        self.v = 0.0
        self.p00 = 0.5
        self.p01 = 0.0
        self.p11 = 1.0
        self.q = float(accel_noise)
        self.r = float(meas_noise)

    def predict(self, dt: float) -> float:
        if dt <= 0.0:
            return self.p
        # F = [[1, dt], [0, 1]]
        self.p = self.p + self.v * dt
        # P = F P F^T + Q
        p00 = self.p00 + dt * (2.0 * self.p01 + dt * self.p11)
        p01 = self.p01 + dt * self.p11
        p11 = self.p11
        q = self.q
        self.p00 = p00 + q * dt ** 4 / 4.0
        self.p01 = p01 + q * dt ** 3 / 2.0
        self.p11 = p11 + q * dt ** 2
        return self.p

    def update(self, z: float) -> float:
        s = self.p00 + self.r
        if s <= 0.0:
            return self.p
        k0 = self.p00 / s
        k1 = self.p01 / s
        resid = float(z) - self.p
        self.p += k0 * resid
        self.v += k1 * resid
        p00 = (1.0 - k0) * self.p00
        p01 = (1.0 - k0) * self.p01
        p11 = self.p11 - k1 * self.p01
        self.p00, self.p01, self.p11 = p00, p01, max(p11, 1e-6)
        # 速度限幅，避免遮挡后外推发散
        self.v = max(-2.0, min(2.0, self.v))
        return self.p


class KalmanBox:
    """包围框的常速度跟踪：中心点用卡尔曼，宽高沿用最近一次量测。

    predict 按**绝对时间**幂等推进（同一时刻重复调用不会重复外推），
    因为跟踪器在关联、观测生成与丢失处理里会多次取预测框。
    """

    def __init__(self, bbox: BBox, accel_noise: float, meas_noise: float,
                 ts: float = 0.0) -> None:
        x1, y1, x2, y2 = bbox
        self.cx = KalmanAxis((x1 + x2) / 2.0, accel_noise, meas_noise)
        self.cy = KalmanAxis((y1 + y2) / 2.0, accel_noise, meas_noise)
        self.w = max(1e-4, x2 - x1)
        self.h = max(1e-4, y2 - y1)
        self.ts = float(ts)
        self.age = 0

    def predict_at(self, ts: float) -> BBox:
        dt = float(ts) - self.ts
        if dt > 0:
            self.ts = float(ts)
            self.cx.predict(dt)
            self.cy.predict(dt)
        return self._wrap(self.cx.p, self.cy.p)

    def update_at(self, bbox: BBox, ts: float) -> BBox:
        self.predict_at(ts)
        self.cx.update((bbox[0] + bbox[2]) / 2.0)
        self.cy.update((bbox[1] + bbox[3]) / 2.0)
        self.w = 0.6 * self.w + 0.4 * max(1e-4, bbox[2] - bbox[0])
        self.h = 0.6 * self.h + 0.4 * max(1e-4, bbox[3] - bbox[1])
        return self._wrap(self.cx.p, self.cy.p)

    def _wrap(self, cx: float, cy: float) -> BBox:
        half_w = self.w / 2.0
        half_h = self.h / 2.0
        return (clip01(cx - half_w), clip01(cy - half_h), clip01(cx + half_w), clip01(cy + half_h))


# --------------------------------------------------------------------------- 轨迹


@dataclass
class Track:
    """一条轨迹。"""

    track_id: int
    camera_id: str
    cls: str
    bbox: BBox
    score: float
    ts: float
    kalman: KalmanBox
    hits: int = 1
    age: int = 1
    time_since_update: int = 0
    confirmed: bool = False
    appearance: list[float] | None = None
    last_anchor_ts: float = 0.0

    def predicted_bbox(self, ts: float) -> BBox:
        return self.kalman.predict_at(ts)

    def update(self, det: Detection, ts: float) -> None:
        self.bbox = self.kalman.update_at(det.bbox, ts)
        self.score = 0.7 * self.score + 0.3 * det.score
        self.ts = ts
        self.last_anchor_ts = ts
        self.hits += 1
        self.age += 1
        self.time_since_update = 0
        if det.appearance:
            self.appearance = _ema_vector(self.appearance, det.appearance)

    def miss(self) -> None:
        self.time_since_update += 1
        self.age += 1

    @property
    def bbox_anchor(self) -> tuple[float, float]:
        return bbox_bottom_center(self.bbox)


def _ema_vector(prev: list[float] | None, cur: list[float], alpha: float = 0.6) -> list[float]:
    if not prev or len(prev) != len(cur):
        return [float(v) for v in cur]
    return [alpha * float(c) + (1 - alpha) * float(p) for p, c in zip(prev, cur)]


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    num = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        num += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return num / ((na ** 0.5) * (nb ** 0.5))


# --------------------------------------------------------------------------- 跟踪器


@dataclass
class TrackerUpdate:
    obs: list[TrackObs] = field(default_factory=list)
    removed: list[Track] = field(default_factory=list)
    created: list[Track] = field(default_factory=list)

    @property
    def tracks(self) -> list[TrackObs]:
        return self.obs


class ByteTracker:
    """ByteTrack 式多目标跟踪器（两阶段关联）。"""

    def __init__(self, cfg: dict, anchor_mode: str = "bottom_center") -> None:
        self.high_thresh = float(cfg.get("high_thresh", 0.5))
        self.low_thresh = float(cfg.get("low_thresh", 0.1))
        self.new_track_thresh = float(cfg.get("new_track_thresh", 0.55))
        self.match_iou = float(cfg.get("match_iou", 0.3))
        self.low_match_iou = float(cfg.get("low_match_iou", 0.2))
        self.min_hits = int(cfg.get("min_hits", 3))
        self.max_lost_frames = int(cfg.get("max_lost_frames", 80))
        kal = cfg.get("kalman", {}) or {}
        self.accel_noise = float(kal.get("accel_noise", 0.02))
        self.meas_noise = float(kal.get("meas_noise", 0.04))
        self.anchor_mode = anchor_mode
        self.tracks: dict[int, Track] = {}
        self._next_id = 1

    # ------------------------------------------------------------------ 主循环
    def step(self, frame: Frame) -> TrackerUpdate:
        ts = frame.ts
        # 1) 全部轨迹向前预测
        preds: dict[int, BBox] = {}
        for trk in self.tracks.values():
            preds[trk.track_id] = trk.predicted_bbox(ts)

        dets = [d.normalized() for d in frame.detections]
        high = [d for d in dets if d.score >= self.high_thresh]
        low = [d for d in dets if self.low_thresh <= d.score < self.high_thresh]

        matched_det: set[int] = set()
        matched_trk: set[int] = set()

        # 2) 第一阶段：高分检测关联
        pairs = self._associate(list(self.tracks.values()), preds, high, self.match_iou)
        for trk_id, det_idx in pairs:
            self.tracks[trk_id].update(high[det_idx], ts)
            matched_trk.add(trk_id)
            matched_det.add(det_idx)

        # 3) 第二阶段：低分检测关联未匹配轨迹（遮挡续轨的关键）
        rest_trks = [t for t in self.tracks.values() if t.track_id not in matched_trk]
        rest_preds = {t.track_id: t.predicted_bbox(ts) for t in rest_trks}
        pairs2 = self._associate(rest_trks, rest_preds, low, self.low_match_iou)
        for trk_id, det_idx in pairs2:
            self.tracks[trk_id].update(low[det_idx], ts)
            matched_trk.add(trk_id)
            matched_det.add(det_idx)

        # 4) 未匹配的高分检测 -> 新轨迹
        created: list[Track] = []
        for idx, det in enumerate(high):
            if idx in matched_det:
                continue
            if det.score < self.new_track_thresh:
                continue
            trk = Track(
                track_id=self._next_id,
                camera_id=frame.camera_id,
                cls=det.cls,
                bbox=det.bbox,
                score=det.score,
                ts=ts,
                kalman=KalmanBox(det.bbox, self.accel_noise, self.meas_noise, ts=ts),
                appearance=list(det.appearance) if det.appearance else None,
                last_anchor_ts=ts,
            )
            trk.confirmed = self.min_hits <= 1
            self.tracks[trk.track_id] = trk
            created.append(trk)
            self._next_id += 1

        # 5) 丢失计数与淘汰
        removed: list[Track] = []
        for trk in list(self.tracks.values()):
            if trk.track_id not in matched_trk:
                trk.miss()
                if trk.time_since_update > self.max_lost_frames:
                    removed.append(trk)
                    del self.tracks[trk.track_id]
            elif trk.hits >= self.min_hits:
                trk.confirmed = True

        # 6) 生成给状态机的逐帧观测
        obs: list[TrackObs] = []
        for trk in self.tracks.values():
            seen = trk.track_id in matched_trk
            pred = preds.get(trk.track_id, trk.bbox)
            if seen:
                pred = trk.bbox
            obs.append(
                TrackObs(
                    camera_id=frame.camera_id,
                    track_id=trk.track_id,
                    frame_idx=frame.frame_idx,
                    ts=ts,
                    seen=seen,
                    anchor=get_anchor(trk.bbox, self.anchor_mode),
                    bbox=trk.bbox,
                    pred_anchor=get_anchor(pred, self.anchor_mode),
                    pred_bbox=pred,
                    det_score=trk.score,
                    appearance=list(trk.appearance) if trk.appearance else None,
                    frame_ok=frame.ok,
                    track_hits=trk.hits,
                )
            )
        for trk in removed:
            pred = trk.predicted_bbox(ts)
            obs.append(
                TrackObs(
                    camera_id=frame.camera_id,
                    track_id=trk.track_id,
                    frame_idx=frame.frame_idx,
                    ts=ts,
                    seen=False,
                    anchor=get_anchor(trk.bbox, self.anchor_mode),
                    bbox=trk.bbox,
                    pred_anchor=get_anchor(pred, self.anchor_mode),
                    pred_bbox=pred,
                    det_score=trk.score,
                    appearance=list(trk.appearance) if trk.appearance else None,
                    frame_ok=frame.ok,
                    track_hits=trk.hits,
                )
            )
        return TrackerUpdate(obs=obs, removed=removed, created=created)

    # ------------------------------------------------------------------ 关联
    def _associate(self, tracks: list[Track], preds: dict[int, BBox],
                   dets: list[Detection], iou_thresh: float) -> list[tuple[int, int]]:
        """贪心 IoU 指派，按 IoU 从大到小依次占用；同类别才能匹配。"""
        if not tracks or not dets:
            return []
        candidates: list[tuple[float, int, int]] = []
        for trk in tracks:
            pred = preds.get(trk.track_id, trk.bbox)
            for idx, det in enumerate(dets):
                if det.cls != trk.cls:
                    continue
                iou = bbox_iou(pred, det.bbox)
                if iou >= iou_thresh:
                    candidates.append((iou, trk.track_id, idx))
        candidates.sort(reverse=True)
        used_trk: set[int] = set()
        used_det: set[int] = set()
        pairs: list[tuple[int, int]] = []
        for _iou, trk_id, det_idx in candidates:
            if trk_id in used_trk or det_idx in used_det:
                continue
            used_trk.add(trk_id)
            used_det.add(det_idx)
            pairs.append((trk_id, det_idx))
        return pairs

    # ------------------------------------------------------------------ 工具
    def reset(self) -> None:
        self.tracks.clear()
        self._next_id = 1

    def stats(self) -> dict:
        return {
            "active_tracks": len(self.tracks),
            "confirmed_tracks": sum(1 for t in self.tracks.values() if t.confirmed),
        }
