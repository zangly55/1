"""数据源：合成连续监控流（含硬负例/遮挡/夜间/丢帧/跨机位漂移）与真实数据回放。

为什么自带合成流：
    论文要求评测必须覆盖"极端无事件占优 + 同场景硬负例 + 遮挡 + 低信噪比 + 丢帧"，
    而这些条件在公开数据集里无法按需复现。合成流让工程实现可自测、可回归、可复现，
    并且每个事件的真值（含 satisfy_ts）都是已知的。

接真实数据：
    `JsonlSource` 读取逐帧检测结果（YOLOv10/ByteTrack 或任何检测+跟踪输出）；
    接入自有检测器只需实现 `FrameSource.iter_frames()`，其余模块零改动。
    合成检测层是**可替换的模拟器**，不是被评测的目标——报告里必须写明这一点。
"""
from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass, field
from typing import Iterator, Optional, Protocol, Sequence

from .geometry import BBox
from .types import CameraInfo, Detection, Frame, GtEvent, Roi
from .util import get_logger, read_json, read_jsonl

LOG = get_logger("cvalarm.source")


# --------------------------------------------------------------------------- 接口


class FrameSource(Protocol):
    """数据源接口。接自有检测器时实现这三个方法即可。"""

    cameras: list[CameraInfo]
    rois: list[Roi]
    gt_events: list[GtEvent]

    def iter_frames(self) -> Iterator[Frame]: ...


# --------------------------------------------------------------------------- 场景描述


@dataclass
class ActorSpec:
    """一个目标的时间线：位置关键帧 + 可见区间。"""

    actor_id: str
    camera_id: str
    cls: str
    keyframes: list[tuple[float, float, float]]  # (t, anchor_x, anchor_y)
    size: tuple[float, float] = (0.055, 0.16)
    visible: list[tuple[float, float]] = field(default_factory=list)
    score_base: float = 0.9
    appearance: list[float] = field(default_factory=list)
    static: bool = False

    def active(self, ts: float) -> bool:
        if ts < self.keyframes[0][0] or ts > self.keyframes[-1][0]:
            return False
        return any(t0 <= ts <= t1 for t0, t1 in (self.visible or [
            (self.keyframes[0][0], self.keyframes[-1][0])]))

    def position(self, ts: float) -> tuple[float, float, float]:
        """线性插值锚点，返回 (x, y)。"""
        frames = self.keyframes
        if ts <= frames[0][0]:
            return frames[0][1], frames[0][2]
        for i in range(1, len(frames)):
            t1, x1, y1 = frames[i]
            if ts <= t1:
                t0, x0, y0 = frames[i - 1]
                dt = t1 - t0
                if dt <= 0:
                    return x1, y1
                r = (ts - t0) / dt
                return x0 + (x1 - x0) * r, y0 + (y1 - y0) * r
        return frames[-1][1], frames[-1][2]

    def bbox(self, ts: float) -> BBox:
        x, y = self.position(ts)
        w, h = self.size
        return (x - w / 2.0, y - h, x + w / 2.0, y)


@dataclass
class CameraSpec:
    camera_id: str
    info: CameraInfo
    rois: list[Roi]
    night: tuple[float, float] = (0.0, 0.0)
    night_snr: float = 9.0
    day_snr: float = 26.0
    night_score_factor: float = 0.72
    drift: float = 1.0
    drop_windows: list[tuple[float, float, float]] = field(default_factory=list)
    actors: list[ActorSpec] = field(default_factory=list)

    def snr(self, ts: float) -> float:
        if self.night[0] <= ts <= self.night[1]:
            return self.night_snr
        return self.day_snr

    def quality_factor(self, ts: float) -> float:
        factor = 1.0 / max(1e-6, self.drift)
        if self.night[0] <= ts <= self.night[1]:
            factor *= self.night_score_factor
        return factor

    def dropped(self, ts: float, frame_idx: int) -> bool:
        for t0, t1, p in self.drop_windows:
            if t0 <= ts <= t1 and _hash_unit(self.camera_id, frame_idx, "drop") < p:
                return True
        return False


def _hash_unit(*parts) -> float:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:4], "big") / 2 ** 32


def _noise(*parts) -> float:
    return (_hash_unit(*parts) - 0.5) * 2.0


# --------------------------------------------------------------------------- 合成源


class SyntheticSource:
    """可复现的多机位连续流生成器。"""

    def __init__(self, cameras: list[CameraSpec], gt_events: list[GtEvent],
                 name: str = "synthetic", seed: int = 7) -> None:
        self.specs = cameras
        self.cameras = [c.info for c in cameras]
        self.rois = [r for c in cameras for r in c.rois]
        self.gt_events = gt_events
        self.name = name
        self.seed = seed

    # ------------------------------------------------------------------ 生成
    def iter_frames(self) -> Iterator[Frame]:
        for cam in self.specs:
            yield from self._iter_camera(cam)

    def _iter_camera(self, cam: CameraSpec) -> Iterator[Frame]:
        fps = max(0.1, cam.info.fps)
        hours = max(0.0, cam.info.valid_hours)
        n_frames = int(round(hours * 3600.0 * fps))
        dt = 1.0 / fps
        gt_windows = [(e.start, e.end) for e in self.gt_events if e.camera_id == cam.camera_id]
        for idx in range(n_frames):
            ts = idx * dt
            ok = not cam.dropped(ts, idx)
            dets: list[Detection] = []
            if ok:
                q = cam.quality_factor(ts)
                for actor in cam.actors:
                    if not actor.active(ts):
                        continue
                    score = actor.score_base * q + _noise(cam.camera_id, actor.actor_id, idx) * 0.04
                    if score < 0.05:
                        continue
                    bbox = actor.bbox(ts)
                    appearance = _jitter_vector(actor.appearance, cam.camera_id, actor.actor_id, idx)
                    dets.append(Detection(cls=actor.cls, bbox=bbox,
                                          score=round(min(0.99, max(0.05, score)), 4),
                                          appearance=appearance))
            label = 1 if any(a <= ts <= b for a, b in gt_windows) else 0
            yield Frame(
                camera_id=cam.camera_id,
                frame_idx=idx,
                ts=round(ts, 4),
                ok=ok,
                detections=dets,
                quality={"snr": round(cam.snr(ts), 2), "night": 1.0 if
                         cam.night[0] <= ts <= cam.night[1] else 0.0},
                gt_label=label,
            )

    def describe(self) -> dict:
        return {
            "name": self.name,
            "kind": "synthetic",
            "cameras": [
                {
                    "camera_id": c.camera_id,
                    "fps": c.info.fps,
                    "hours": c.info.valid_hours,
                    "drift": c.drift,
                    "night": list(c.night),
                    "rois": [r.roi_id for r in c.rois],
                    "actors": len(c.actors),
                    "drop_windows": [list(w) for w in c.drop_windows],
                }
                for c in self.specs
            ],
            "gt_events": [e.to_dict() for e in self.gt_events],
            "note": "检测与跟踪输入为可替换的模拟器；生产环境应接入真实检测器。",
        }


def _jitter_vector(base: Sequence[float], *parts) -> list[float]:
    if not base:
        return []
    out = []
    for i, value in enumerate(base):
        out.append(round(float(value) + _noise(*parts, i) * 0.02, 5))
    norm = math.sqrt(sum(v * v for v in out)) or 1.0
    return [round(v / norm, 5) for v in out]


# --------------------------------------------------------------------------- 真实回放


class JsonlSource:
    """读取逐帧检测 JSONL，用于接入自有检测/跟踪输出。

    每行格式：
        {"camera_id":"CAM-01","frame_idx":0,"ts":0.0,"ok":true,"snr":26.0,
         "detections":[{"cls":"person","bbox":[x1,y1,x2,y2],"score":0.9,"appearance":[...]}]}

    可选 --gt 文件提供事件真值（字段同 GtEvent）；缺省时只产出告警与成本，不产出召回指标。
    """

    def __init__(self, frames_path: str, cameras_path: Optional[str] = None,
                 gt_path: Optional[str] = None) -> None:
        self.frames_path = frames_path
        self.cameras_path = cameras_path
        self.gt_path = gt_path
        self.ground_truth_available = bool(gt_path)
        if not os.path.isfile(frames_path):
            raise ValueError("检测 JSONL 文件不存在")
        if gt_path and not os.path.isfile(gt_path):
            raise ValueError("指定的真值文件不存在")
        self.cameras: list[CameraInfo] = []
        self.rois: list[Roi] = []
        if cameras_path and os.path.exists(cameras_path):
            data = read_json(cameras_path, default={}) or {}
            for item in data.get("cameras", []):
                info = CameraInfo(
                    camera_id=item["camera_id"],
                    name=item.get("name", ""),
                    fps=float(item.get("fps", 2.0)),
                    width=int(item.get("width", 1920)),
                    height=int(item.get("height", 1080)),
                    valid_hours=float(item.get("valid_hours", 0.0)),
                    drift=float(item.get("drift", 1.0)),
                )
                info.rois = item.get("rois", [])
                self.cameras.append(info)
                for roi in item.get("rois", []):
                    self.rois.append(Roi.from_dict({**roi, "camera_id": info.camera_id}))
        self.gt_events: list[GtEvent] = []
        if gt_path and os.path.exists(gt_path):
            for row in read_jsonl(gt_path):
                self.gt_events.append(GtEvent(**row))

    def iter_frames(self) -> Iterator[Frame]:
        for row in read_jsonl(self.frames_path):
            dets = [Detection(cls=d["cls"], bbox=tuple(d["bbox"]), score=float(d["score"]),
                              appearance=d.get("appearance"))
                    for d in row.get("detections", [])]
            quality = dict(row.get("quality", {}))
            if "snr" in row:
                quality["snr"] = float(row["snr"])
            yield Frame(
                camera_id=str(row["camera_id"]),
                frame_idx=int(row["frame_idx"]),
                ts=float(row["ts"]),
                ok=bool(row.get("ok", True)),
                detections=dets,
                quality=quality,
                gt_label=int(row["gt_label"]) if row.get("gt_label") is not None else None,
            )

    def describe(self) -> dict:
        return {
            "name": os.path.basename(self.frames_path),
            "kind": "jsonl-replay",
            "cameras": [c.to_dict() for c in self.cameras],
            "gt_events": [e.to_dict() for e in self.gt_events],
            "note": "真实检测结果回放；检测/跟踪质量由外部系统决定。",
        }


# --------------------------------------------------------------------------- 演示场景


def _walk(start: float, end: float, p0: tuple[float, float],
          p1: tuple[float, float]) -> list[tuple[float, float, float]]:
    return [(start, p0[0], p0[1]), (end, p1[0], p1[1])]


def _wander(start: float, end: float, base: tuple[float, float],
            radius: float = 0.02, steps: int = 6) -> list[tuple[float, float, float]]:
    out: list[tuple[float, float, float]] = []
    for i in range(steps):
        t = start + (end - start) * i / max(1, steps - 1)
        ang = i * 2.399  # 黄金角，避免规则路径
        out.append((t, base[0] + math.cos(ang) * radius, base[1] + math.sin(ang) * radius))
    return out


def _appearance(seed_text: str, dim: int = 8) -> list[float]:
    vals = []
    for i in range(dim):
        vals.append(_hash_unit(seed_text, i) - 0.5)
    norm = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [round(v / norm, 4) for v in vals]


def build_demo(hours: float = 3.0, fps: float = 2.0) -> SyntheticSource:
    """构造演示场景：5 个真实事件 + 4 类硬负例 + 1 个静态物体误检。

    时间轴（流内相对秒）：
      CAM-01 / ROI-A（周界防区，阈值 45s）
        t=10–25    接近防区但未进入（硬负例：H2）
        t=40–60    进入 20s 后离开（低于阈值，H1）
        t=120–152  进入 32s（低于阈值，H1b）
        t=300–660  保洁作业，滞留 350s（有许可 WP-2291 → 应抑制，H3）
        t=540–560  反光伪目标，持续 12s（低于滞留阈值，H4）
        t=720–810  未授权闯入 90s（E1，违规成立于 765）
        t=900–1145 闯入 + 90s 完全遮挡后重现并继续滞留（E3，违规成立于 1035）
        t=1080–1200 静止物体被误识别为人员（静态误检 → 误报）
        t=1500–1620 夜间低信噪比闯入（E5，转人工）
      CAM-02（广角漂移机位）
        ROI-B（装卸区，滞留阈值 1800s）
          t=60–80    进入 20s（H1）
          t=300–2400 授权检修滞留 2100s（有许可 WP-2384 → 应抑制）
          t=4000–6100 未授权长时间滞留（E2，违规成立于 5800）
        ROI-C（装卸通道，阈值 45s）
          t=7600–7690 夜间闯入 + 25% 丢帧（E4，系统异常，转重检）
    """
    rois_cam1 = [Roi(
        roi_id="ROI-A",
        polygon=[[0.36, 0.55], [0.74, 0.55], [0.82, 0.95], [0.28, 0.95]],
        event_class="UNAUTHORIZED_INTRUSION",
        name="周界防区",
        dwell_threshold_s=45.0,
    )]
    rois_cam2 = [
        Roi(roi_id="ROI-B",
            polygon=[[0.08, 0.38], [0.42, 0.38], [0.46, 0.92], [0.04, 0.92]],
            event_class="LOITERING", name="装卸区", dwell_threshold_s=1800.0),
        Roi(roi_id="ROI-C",
            polygon=[[0.55, 0.45], [0.90, 0.45], [0.94, 0.96], [0.52, 0.96]],
            event_class="RESTRICTED_AREA_ACTIVITY", name="装卸通道", dwell_threshold_s=45.0),
    ]
    for r in rois_cam1:
        r.camera_id = "CAM-01"
    for r in rois_cam2:
        r.camera_id = "CAM-02"

    cam1 = CameraSpec(
        camera_id="CAM-01",
        info=CameraInfo(camera_id="CAM-01", name="一号门周界", fps=fps, valid_hours=hours,
                        drift=1.0, rois=[r.to_dict() for r in rois_cam1]),
        rois=rois_cam1,
        night=(1200.0, 2100.0),
        drift=1.0,
    )
    cam2 = CameraSpec(
        camera_id="CAM-02",
        info=CameraInfo(camera_id="CAM-02", name="装卸区广角", fps=fps, valid_hours=hours,
                        drift=1.25, rois=[r.to_dict() for r in rois_cam2]),
        rois=rois_cam2,
        night=(7000.0, 8000.0),
        drift=1.25,
        drop_windows=[(7590.0, 7700.0, 0.55)],
    )

    A = _appearance
    # ---------------- CAM-01
    cam1.actors += [
        ActorSpec("c1-approach", "CAM-01", "person",
                  _walk(10, 25, (0.18, 1.02), (0.24, 0.70)), (0.055, 0.15),
                  [(10, 25)], 0.9, A("c1-approach")),
        ActorSpec("c1-short1", "CAM-01", "person",
                  _walk(40, 60, (0.30, 0.98), (0.56, 0.74)), (0.055, 0.16),
                  [(40, 60)], 0.9, A("c1-short1")),
        ActorSpec("c1-short2", "CAM-01", "person",
                  _wander(120, 152, (0.52, 0.74), 0.03), (0.055, 0.16),
                  [(120, 152)], 0.9, A("c1-short2")),
        ActorSpec("c1-cleaner", "CAM-01", "person",
                  _wander(300, 660, (0.54, 0.80), 0.05, 8), (0.056, 0.16),
                  [(300, 660)], 0.92, A("c1-cleaner")),
        ActorSpec("c1-reflection", "CAM-01", "person",
                  _walk(540, 552, (0.70, 0.60), (0.66, 0.62)), (0.03, 0.05),
                  [(540, 552)], 0.62, A("c1-reflection")),
        ActorSpec("c1-intrusion", "CAM-01", "person",
                  _wander(720, 810, (0.58, 0.78), 0.04), (0.058, 0.17),
                  [(720, 810)], 0.92, A("c1-intrusion")),
        ActorSpec("c1-occlusion", "CAM-01", "person",
                  _wander(900, 1145, (0.60, 0.80), 0.03, 8), (0.058, 0.17),
                  [(900, 925), (1015, 1145)], 0.92, A("c1-occlusion")),
        ActorSpec("c1-static-object", "CAM-01", "person",
                  [(1080, 0.60, 0.84), (1200, 0.605, 0.84)], (0.26, 0.20),
                  [(1080, 1200)], 0.60, A("c1-static-object"), static=True),
        ActorSpec("c1-night", "CAM-01", "person",
                  _wander(1500, 1620, (0.56, 0.79), 0.03), (0.058, 0.17),
                  [(1500, 1620)], 0.95, A("c1-night")),
    ]
    # 背景正常行人（区外，制造真实的无事件占优）
    t = 100
    i = 0
    while t < hours * 3600 - 100:
        i += 1
        cam1.actors.append(ActorSpec(
            f"c1-bg{i}", "CAM-01", "person",
            _walk(t, t + 22, (0.05, 1.02), (0.95, 1.06)), (0.05, 0.13),
            [(t, t + 22)], 0.88, A(f"c1-bg{i}")))
        t += 240

    # ---------------- CAM-02
    cam2.actors += [
        ActorSpec("c2-short", "CAM-02", "person",
            _wander(60, 80, (0.24, 0.72), 0.03), (0.06, 0.16),
            [(60, 80)], 0.86, A("c2-short")),
        ActorSpec("c2-maintain", "CAM-02", "person",
            _wander(300, 2400, (0.26, 0.74), 0.06, 8), (0.062, 0.17),
            [(300, 2400)], 0.86, A("c2-maintain")),
        ActorSpec("c2-loiter", "CAM-02", "person",
            _wander(4000, 6100, (0.25, 0.75), 0.05, 8), (0.062, 0.17),
            [(4000, 6100)], 0.86, A("c2-loiter")),
        ActorSpec("c2-night", "CAM-02", "person",
            _walk(7600, 7690, (0.60, 0.55), (0.82, 0.90)), (0.062, 0.17),
            [(7600, 7690)], 0.95, A("c2-night")),
        ActorSpec("c2-channel", "CAM-02", "person",
            _walk(500, 530, (0.60, 0.60), (0.88, 0.92)), (0.06, 0.16),
            [(500, 530)], 0.88, A("c2-channel")),
    ]
    t = 150
    i = 0
    while t < hours * 3600 - 100:
        i += 1
        cam2.actors.append(ActorSpec(
            f"c2-bg{i}", "CAM-02", "person",
            _walk(t, t + 30, (0.02, 0.99), (0.98, 1.02)), (0.052, 0.14),
            [(t, t + 30)], 0.85, A(f"c2-bg{i}")))
        t += 300

    gt_events = [
        GtEvent("E1", "CAM-01", "UNAUTHORIZED_INTRUSION", 720.0, 810.0, "ROI-A",
                satisfy_ts=765.0, note="未授权闯入并滞留 90 秒",
                evidence_span=(720.0, 810.0)),
        GtEvent("E3", "CAM-01", "UNAUTHORIZED_INTRUSION", 900.0, 1145.0, "ROI-A",
                satisfy_ts=1029.0, note="遮挡 90 秒后重现，分段累计达阈值（含 L 帧遮挡容差）",
                evidence_span=(900.0, 1145.0)),
        GtEvent("E5", "CAM-01", "UNAUTHORIZED_INTRUSION", 1500.0, 1620.0, "ROI-A",
                satisfy_ts=1545.0, note="夜间低信噪比，证据不足转人工",
                evidence_span=(1500.0, 1620.0)),
        GtEvent("E2", "CAM-02", "LOITERING", 4000.0, 6100.0, "ROI-B",
                satisfy_ts=5800.0, note="装卸区未授权长时间滞留",
                evidence_span=(4000.0, 6100.0)),
        GtEvent("E4", "CAM-02", "RESTRICTED_AREA_ACTIVITY", 7600.0, 7690.0, "ROI-C",
                satisfy_ts=7645.0, note="夜间闯入叠加 55% 丢帧，属采集中断",
                evidence_span=(7600.0, 7690.0)),
    ]
    return SyntheticSource([cam1, cam2], [e for e in gt_events if e.end <= hours*3600], name="demo", seed=7)


def build_v1(hours: float = 2.0, fps: float = 2.0) -> SyntheticSource:
    """首版范围场景（对应工程方向"缩到单镜头 + 两类事件"）。

    单机位、两个防区、两类定义清楚的可见事件：
      * 人员进入指定区域后累计在场达 45 秒（ROI-A）；
      * 区域内停留超过设定时长（ROI-D，300 秒阈值）。

    保留完整模型链路与困难输入（无事件 / 短暂停留 / 遮挡 / 夜间 / 授权作业 / 静态物误检），
    只是把机位与事件种类缩到首版规模。暂缓项（多摄像头、实时接流、多 Agent、自动规则演化）
    由 run_meta.capabilities 显式标注。
    """
    src = build_demo(hours=hours, fps=fps)
    cam1 = src.specs[0]
    roi_d = Roi(
        roi_id="ROI-D",
        polygon=[[0.05, 0.28], [0.32, 0.28], [0.34, 0.90], [0.02, 0.90]],
        event_class="UNAUTHORIZED_DWELL",
        name="重点区域（停留超时）",
        camera_id="CAM-01",
        dwell_threshold_s=300.0,
    )
    cam1.rois = list(cam1.rois) + [roi_d]
    cam1.info.rois = [r.to_dict() for r in cam1.rois]
    cam1.actors.extend([
        # 授权作业：停留 500 秒，许可 WP-V1 覆盖 -> 应被抑制
        ActorSpec("v1-dwell-authorized", "CAM-01", "person",
                  _wander(2200, 2700, (0.17, 0.62), 0.03, 6), (0.056, 0.16),
                  [(2200, 2700)], 0.9, _appearance("v1-dwell-authorized")),
        # 未授权停留 600 秒 -> 应确证告警（E6）
        ActorSpec("v1-dwell", "CAM-01", "person",
                  _wander(3000, 3600, (0.18, 0.63), 0.03, 6), (0.056, 0.16),
                  [(3000, 3600)], 0.9, _appearance("v1-dwell")),
    ])
    gt_events = [
        GtEvent("E1", "CAM-01", "UNAUTHORIZED_INTRUSION", 720.0, 810.0, "ROI-A",
                satisfy_ts=765.0, note="未授权闯入并滞留 90 秒",
                evidence_span=(720.0, 810.0)),
        GtEvent("E3", "CAM-01", "UNAUTHORIZED_INTRUSION", 900.0, 1145.0, "ROI-A",
                satisfy_ts=1029.0, note="遮挡 90 秒后重现，分段累计达阈值",
                evidence_span=(900.0, 1145.0)),
        GtEvent("E5", "CAM-01", "UNAUTHORIZED_INTRUSION", 1500.0, 1620.0, "ROI-A",
                satisfy_ts=1545.0, note="夜间低信噪比，证据不足转人工",
                evidence_span=(1500.0, 1620.0)),
        GtEvent("E6", "CAM-01", "UNAUTHORIZED_DWELL", 3000.0, 3600.0, "ROI-D",
                satisfy_ts=3300.0, note="重点区域停留 600 秒（阈值 300 秒）",
                evidence_span=(3000.0, 3600.0)),
    ]
    source = SyntheticSource([cam1], [e for e in gt_events if e.end <= hours*3600], name="v1-scope", seed=7)
    source.cameras = [cam1.info]
    source.rois = list(cam1.rois)
    return source


def build_small(hours: float = 0.5, fps: float = 2.0) -> SyntheticSource:
    """小规模场景（用于单元测试与快速回归门禁）。"""
    src = build_demo(hours=max(hours, 0.5), fps=fps)
    # 只保留前 30 分钟窗口内的事件与演员，缩短运行时间
    cutoff = hours * 3600.0
    for cam in src.specs:
        cam.info.valid_hours = hours
        cam.actors = [a for a in cam.actors if a.keyframes[0][0] < cutoff]
    src.gt_events = [e for e in src.gt_events if e.end <= cutoff]
    return src


def build_regression(hours: float = 1.0, fps: float = 2.0) -> SyntheticSource:
    """回归门禁专用场景：覆盖已知真事件与典型误报（论文 6.4 节要求重放固定回归集）。"""
    return build_demo(hours=max(hours, 1.2), fps=fps)


# --------------------------------------------------------------------------- 装载


def load_source(kind: str = "demo", frames: str = "", cameras: str = "",
                gt: str = "", hours: float = 3.0, fps: float = 2.0) -> FrameSource:
    if kind == "demo":
        return build_demo(hours=hours, fps=fps)
    if kind == "v1":
        return build_v1(hours=hours, fps=fps)
    if kind == "regression":
        return build_regression(hours=hours, fps=fps)
    if kind == "jsonl":
        if not frames:
            raise ValueError("kind=jsonl 时必须提供 --frames 检测结果文件")
        return JsonlSource(frames, cameras or None, gt or None)
    raise ValueError(f"未知数据源类型：{kind}")


def write_frames_jsonl(source: FrameSource, path: str, limit: int = 0) -> int:
    """把任意数据源的逐帧检测导出为 JSONL（便于复现与接真实系统）。"""
    from .util import ensure_dir

    ensure_dir(os.path.dirname(os.path.abspath(path)))
    n = 0
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for frame in source.iter_frames():
            payload = {
                "camera_id": frame.camera_id,
                "frame_idx": frame.frame_idx,
                "ts": frame.ts,
                "ok": frame.ok,
                "snr": frame.quality.get("snr", 99.0),
                "gt_label": frame.gt_label,
                "detections": [
                    {
                        "cls": d.cls,
                        "bbox": [round(v, 5) for v in d.bbox],
                        "score": d.score,
                        **({"appearance": d.appearance} if d.appearance else {}),
                    }
                    for d in frame.detections
                ],
            }
            import json as _json
            fh.write(_json.dumps(payload, ensure_ascii=False) + "\n")
            n += 1
            if limit and n >= limit:
                break
    return n
