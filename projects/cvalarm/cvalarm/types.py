"""跨模块共享的数据结构（全部可 JSON 序列化）。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable, Optional

from .geometry import (BBox, Point, bbox_bottom_center, get_anchor, normalize_bbox,
                       point_in_polygon, polygon_area)


def _as_list(obj: Any) -> Any:
    """tuple -> list 递归转换，便于 json.dumps。"""
    if isinstance(obj, tuple):
        return [_as_list(v) for v in obj]
    if isinstance(obj, list):
        return [_as_list(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _as_list(v) for k, v in obj.items()}
    return obj


def to_dict(obj: Any) -> dict:
    return _as_list(asdict(obj))


# --------------------------------------------------------------------------- 视觉输入


@dataclass
class Detection:
    """单帧单目标检测结果（YOLOv10 等检测器输出）。"""

    cls: str
    bbox: BBox
    score: float
    appearance: Optional[list[float]] = None  # ReID 嵌入（可选）

    def normalized(self) -> "Detection":
        return Detection(self.cls, normalize_bbox(self.bbox), float(self.score), self.appearance)


@dataclass
class Frame:
    """一路摄像头的一帧观测。

    ok=False 表示丢帧/解码失败/信道异常——它属于"观测失败"，
    绝不能被下游当作"事件不存在"（论文 4.2 节的分流要求）。
    """

    camera_id: str
    frame_idx: int
    ts: float
    ok: bool = True
    detections: list[Detection] = field(default_factory=list)
    quality: dict[str, float] = field(default_factory=dict)  # snr / blur / exposure
    gt_label: Optional[int] = None  # 未标注不等于正常

    def __post_init__(self) -> None:
        if self.detections:
            self.detections = [
                d if isinstance(d, Detection) else Detection(**d)  # type: ignore[arg-type]
                for d in self.detections
            ]

    @property
    def snr(self) -> float:
        return float(self.quality.get("snr", 99.0))

    def dets_of(self, cls: str) -> list[Detection]:
        return [d for d in self.detections if d.cls == cls]


@dataclass
class FrameFeature:
    """单帧聚合特征，构成 Stage2 可读取的"历史视频缓冲"摘要。"""

    camera_id: str
    ts: float
    ok: bool
    frame_idx: int = 0
    max_score: float = 0.0
    person_count: float = 0.0
    roi_persons: dict[str, float] = field(default_factory=dict)
    motion: float = 0.0
    snr: float = 99.0
    drop_ratio: float = 0.0  # 在一个统计窗内的丢帧比例
    mean_person_aspect: float = 0.0  # 人员框高宽比均值：形态一致性证据

    def to_dict(self) -> dict:
        return to_dict(self)


# --------------------------------------------------------------------------- 跟踪与状态机


@dataclass
class TrackObs:
    """跟踪器交给状态机的一条观测（每帧每目标一条）。"""

    camera_id: str
    track_id: int
    frame_idx: int
    ts: float
    seen: bool                 # 本帧是否有匹配检测
    anchor: Point              # 已量测/最后可靠锚点
    bbox: BBox                 # 量测框或预测框
    pred_anchor: Point         # 卡尔曼预测锚点（seen=False 时用于遮断判定）
    pred_bbox: BBox
    det_score: float = 0.0
    appearance: Optional[list[float]] = None
    frame_ok: bool = True
    track_hits: int = 0


@dataclass
class FsmEvent:
    """状态机对外事件：候选触发 / 正常离开 / 跟踪丢失 / 悬挂与恢复。"""

    kind: str  # candidate | exit | lost | suspended | resumed | entered
    camera_id: str
    track_id: int
    roi_id: str
    ts: float
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return to_dict(self)


@dataclass
class Candidate:
    """Stage1 输出的候选（粗时间窗 + 轨迹状态 + 时空先验）。"""

    candidate_id: str
    camera_id: str
    track_id: int
    roi_id: str
    event_class: str
    t_enter: float
    t_trigger: float
    accum_s: float
    dwell_threshold_s: float
    continuity: dict = field(default_factory=dict)   # suspended / gaps / policy
    snapshot: dict = field(default_factory=dict)    # 轨迹锚点、速度、框尺寸
    window: tuple[float, float] = (0.0, 0.0)        # 送给 Stage2 的视频缓冲区间（因果）
    flags: list[str] = field(default_factory=list)  # occluded / dropped_frames / ...
    t_candidate_ready: float = 0.0                  # 候选在流程中落地（墙钟，相对流起点）

    def to_dict(self) -> dict:
        return to_dict(self)


@dataclass
class FsmArchive:
    """状态机归档记录（审计用：离开 / 丢失 / 证据不完整）。"""

    camera_id: str
    track_id: int
    roi_id: str
    outcome: str  # EXITED | LOST_IDENTITY | LOST_WINDOW_EXPIRED | RESET
    ts: float
    accum_s: float
    t_enter: float
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return to_dict(self)


# --------------------------------------------------------------------------- Stage2 / Stage3


@dataclass
class Stage2Result:
    """时间定位与无事件拒识结果。"""

    decision: str  # EVENT | NO_EVENT | INSUFFICIENT_EVIDENCE | SYSTEM_ERROR
    interval: Optional[tuple[float, float]]
    score: float                 # 最佳区间的调整后得分
    raw_score: float             # 区间内原始证据分
    tau_confirm: float
    tau_reject: float
    margin: float
    bins: list[dict] = field(default_factory=list)  # 每 bin 的得分与时间戳
    validity: dict = field(default_factory=dict)    # valid / reasons / snr / dropped
    reasons: list[str] = field(default_factory=list)
    calibration_ok: bool = True

    def to_dict(self) -> dict:
        return to_dict(self)


@dataclass
class AlarmCard:
    """结构化预警卡片。字段固定，便于中控台解析与人工复核。"""

    card_id: str
    alarm_id: str
    camera_id: str
    event_class: str
    Temporal_Anchor: dict           # start / end / keyframes
    Physical_Fact_Evidence: list[dict]
    Normative_Inference_Uncertainty: dict
    confidence: float = 0.0
    decision: str = "confirm"       # confirm | dismiss | uncertain
    evidence_chain: dict = field(default_factory=dict)
    rule_version: str = ""
    authorization_ref: Optional[str] = None
    signature: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return to_dict(self)


@dataclass
class AlarmRecord:
    """一次告警的全链路记录。"""

    alarm_id: str
    candidate_id: str
    camera_id: str
    track_id: int
    roi_id: str
    event_class: str
    t_satisfy: float      # 事件满足判定条件的理论时刻 = t_enter + threshold
    t_trigger: float      # 状态机触发候选的时刻
    t_display: float      # 中控台卡片完整显示的时刻（含全链路时延）
    status: str           # confirmed | deferred | suppressed | rejected
    triage: str           # Stage2 三向分流结果
    interval: Optional[dict] = None
    card: Optional[dict] = None
    latency: dict = field(default_factory=dict)
    suppression_reason: str = ""
    gt_event_id: Optional[str] = None
    correctness: Optional[str] = None  # TP / FP / 未匹配
    rule_version: str = ""

    def to_dict(self) -> dict:
        return to_dict(self)


# --------------------------------------------------------------------------- 真值与评测


@dataclass
class GtEvent:
    """事件级真值单元。"""

    event_id: str
    camera_id: str
    event_class: str
    start: float
    end: float
    roi_id: str = "ROI-A"
    kind: str = "interval"   # interval | point
    note: str = ""
    satisfy_ts: float = 0.0  # 事件"满足判定条件"的理论时刻；0 表示取 start
    # 支持该判断的"可观测证据区间"（用于定位边界误差评测，与事件存在性分开统计）。
    # 不提供时该事件不进入定位精度统计，并在报告里说明原因。
    evidence_span: Optional[tuple[float, float]] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def condition_ts(self) -> float:
        """TTA 的起点：事件满足判定条件的理论时刻。"""
        return self.satisfy_ts if self.satisfy_ts > 0 else self.start

    def to_dict(self) -> dict:
        return to_dict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "GtEvent":
        payload = dict(data)
        span = payload.get("evidence_span")
        if span:
            payload["evidence_span"] = (float(span[0]), float(span[1]))
        return cls(**payload)


@dataclass
class CameraInfo:
    camera_id: str
    name: str = ""
    fps: float = 2.0
    width: int = 1920
    height: int = 1080
    valid_hours: float = 0.0
    rois: list[dict] = field(default_factory=list)
    drift: float = 1.0        # 跨摄像头漂移系数（影响检测质量）
    night: tuple[float, float] = (0.0, 0.0)

    def to_dict(self) -> dict:
        return to_dict(self)


@dataclass
class Roi:
    """多边形感兴趣区域（防区）。event_class 决定该区域触发的候选事件类别。

    dwell_threshold_s 是该区域所用规程的滞留阈值：不同区域适用不同规程
    （周界 45 秒、装卸区 1800 秒），状态机必须按区域取阈值，
    否则一个全局阈值会让"长滞留"事件在阈值远未达到时就被触发。
    """

    roi_id: str
    polygon: list[list[float]] = field(default_factory=list)
    event_class: str = "UNKNOWN_ANOMALY"
    name: str = ""
    camera_id: str = ""
    dwell_threshold_s: float = 0.0

    def contains(self, point: Point) -> bool:
        return point_in_polygon(point, self.polygon)

    @property
    def area(self) -> float:
        return polygon_area(self.polygon)

    def to_dict(self) -> dict:
        return to_dict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Roi":
        return cls(
            roi_id=data["roi_id"],
            polygon=[[float(p[0]), float(p[1])] for p in data.get("polygon", [])],
            event_class=data.get("event_class", "UNKNOWN_ANOMALY"),
            name=data.get("name", ""),
            camera_id=data.get("camera_id", ""),
            dwell_threshold_s=float(data.get("dwell_threshold_s", 0.0) or 0.0),
        )


def anchor_of(bbox: Iterable[float], mode: str = "bottom_center") -> Point:
    return get_anchor(normalize_bbox(list(bbox)), mode)


__all__ = [
    "Detection", "Frame", "FrameFeature", "TrackObs", "FsmEvent", "Candidate",
    "FsmArchive", "Stage2Result", "AlarmCard", "AlarmRecord", "GtEvent", "CameraInfo", "Roi",
    "to_dict", "anchor_of", "bbox_bottom_center",
]
