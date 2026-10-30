"""测试辅助：把工程加入 sys.path，并提供小型场景与观测构造器。"""
from __future__ import annotations

import os
import sys
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cvalarm.config import Config  # noqa: E402
from cvalarm.fsm import DwellFSM, FsmConfig  # noqa: E402
from cvalarm.types import (CameraInfo, Detection, Frame, GtEvent, Roi, TrackObs)  # noqa: E402

ROI = Roi(
    roi_id="R1",
    polygon=[[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]],
    event_class="UNAUTHORIZED_INTRUSION",
    camera_id="CAM-T",
    dwell_threshold_s=10.0,
)

OUTSIDE_X = 0.05
INSIDE_X = 0.5


def obs(ts: float, inside: bool = True, seen: bool = True, frame_ok: bool = True,
        track_id: int = 1, appearance: Optional[list[float]] = None,
        x: Optional[float] = None, pred_inside: bool = True) -> TrackObs:
    ax = x if x is not None else (INSIDE_X if inside else OUTSIDE_X)
    # 未观测到时，卡尔曼预测框可能仍在防区内（论文 3.2 节 State2 的遮断判定）
    px = ax if seen else (INSIDE_X if pred_inside else OUTSIDE_X)
    bbox = (ax - 0.05, 0.30, ax + 0.05, 0.50)
    pbox = (px - 0.05, 0.30, px + 0.05, 0.50)
    return TrackObs(
        camera_id="C1", track_id=track_id, frame_idx=int(round(ts * 10)), ts=ts,
        seen=seen, anchor=(ax, 0.5), bbox=bbox, pred_anchor=(px, 0.5), pred_bbox=pbox,
        det_score=0.9, appearance=appearance, frame_ok=frame_ok, track_hits=5,
    )


def make_fsm(**overrides) -> DwellFSM:
    kwargs = dict(
        debounce_frames=overrides.pop("debounce", 2),
        occlusion_tolerance_frames=overrides.pop("occ", 3),
        dwell_threshold_s=overrides.pop("thr", 10.0),
        exit_frames=overrides.pop("exit", 2),
        missing_window_s=overrides.pop("window", 30.0),
        reid_policy=overrides.pop("policy", "precise"),
        reid_sim_threshold=0.6,
        max_speed_norm_per_s=0.35,
        reid_max_speed_slack=0.12,
        history_window_s=30.0,
        out_of_roi_policy=overrides.pop("oop", "pause"),
    )
    kwargs.update(overrides)
    cfg = FsmConfig(**kwargs)
    return DwellFSM("C1", ROI, 1, cfg)


def step(fsm: DwellFSM, ts: float, **kw):
    return fsm.update(obs(ts, **kw))


def default_config(**sets) -> Config:
    cfg = Config.load()
    for key, value in sets.items():
        cfg.set(key.replace("__", "."), value)
    cfg.validate()
    return cfg


class TinySource:
    """最小可运行数据源：单机位、单 ROI、一条真实滞留事件 + 一条授权滞留。"""

    def __init__(self, hours: float = 0.05, fps: float = 2.0, drop_every: int = 0) -> None:
        self.camera = CameraInfo(camera_id="CAM-T", fps=fps, valid_hours=hours,
                                 rois=[ROI.to_dict()])
        self.cameras = [self.camera]
        self.rois = [ROI]
        self.gt_events = [
            GtEvent("T1", "CAM-T", "UNAUTHORIZED_INTRUSION", 20.0, 70.0, "R1",
                    satisfy_ts=30.0, note="测试用滞留事件"),
        ]
        self.hours = hours
        self.fps = fps
        self.drop_every = drop_every

    def iter_frames(self):
        n = int(self.hours * 3600 * self.fps)
        for i in range(n):
            ts = i / self.fps
            ok = not (self.drop_every and i % self.drop_every == 0)
            dets = []
            # 20s~70s：目标在 ROI 内一直停留（10s 阈值 -> 30s 处应触发）
            if 20.0 <= ts <= 70.0:
                dets.append(Detection(cls="person", bbox=(0.45, 0.30, 0.55, 0.50),
                                      score=0.92, appearance=[1.0, 0.0, 0.0]))
            elif 100.0 <= ts <= 160.0:
                # 授权作业：目标同样滞留，但外部许可覆盖该时段
                dets.append(Detection(cls="person", bbox=(0.45, 0.30, 0.55, 0.50),
                                      score=0.92, appearance=[0.0, 1.0, 0.0]))
            else:
                dets.append(Detection(cls="person", bbox=(0.02, 0.90, 0.07, 1.0),
                                      score=0.9, appearance=[0.0, 0.0, 1.0]))
            yield Frame(camera_id="CAM-T", frame_idx=i, ts=ts, ok=ok,
                        detections=dets if ok else [],
                        quality={"snr": 26.0},
                        gt_label=1 if 20.0 <= ts <= 70.0 else 0)

    def describe(self) -> dict:
        return {"name": "tiny", "kind": "test", "cameras": [self.camera.to_dict()],
                "gt_events": [e.to_dict() for e in self.gt_events]}


# --------------------------------------------------------------------------- 运行夹具


def tiny_pipeline(cfg, out_dir: str, persist: bool = True, ruleset=None):
    """用最小场景跑一次完整流水线（供报告/CLI 类测试复用）。"""
    from cvalarm.locator import Calibration, Localizer
    from cvalarm.pipeline import Pipeline

    cal = Calibration(version="cal-test", tau_reject=0.10, tau_confirm=0.30,
                      hard_negative_windows=40)
    pipeline = Pipeline(cfg, TinySource(hours=0.05), ruleset=ruleset,
                        localizer=Localizer(cfg, calibration=cal),
                        persist=persist, out_dir=out_dir)
    return pipeline.run()


def make_run(tmp_dir: str, with_report: bool = True, ruleset=None):
    """生成一份可预测、可复现的运行产物（含 HTML 报告），返回 (cfg, run_dir)。"""
    from cvalarm.report import write_report

    cfg = default_config()
    cfg.set("runtime.state_dir", os.path.join(tmp_dir, "state"))
    cfg.set("stage3.authorization_file", os.path.join(tmp_dir, "none.json"))
    run_dir = os.path.join(tmp_dir, "run")
    tiny_pipeline(cfg, run_dir, persist=True, ruleset=ruleset)
    if with_report:
        write_report(run_dir, cfg)
    return cfg, run_dir


# --------------------------------------------------------------------------- 安全读取


def read_json_file(path: str):
    """读取 UTF-8 JSON（带 with，避免 ResourceWarning）。"""
    import json

    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_text_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()
