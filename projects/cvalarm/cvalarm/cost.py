"""全链路分级成本核算（论文 7.2 节）。

    C_total = C_always_on + r1 · C2 + r1 · r2 · C3 + C_feedback

约定（与论文一致，避免量纲混用）：
  * 全部折算到"每摄像头小时"；
  * GPU 时间与货币并行给出，人工工时另列；
  * r1 = 传至第二级的候选视频时长 / 原始时长（实测，不套通用范围）；
  * r2 = 第二级切片后实际传至第三级的视频时长比例（按时长加权，不是按候选数）；
  * C2 是"每处理一个候选视频小时"的成本，C3 同理。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from .util import clamp, safe_div

TOPOLOGIES = ("edge-only", "edge-gateway-cascade", "edge-cloud-api")

TOPOLOGY_NOTES = {
    "edge-only": "纯边缘一体化：视频不出场，前筛、定位与轻量 VLM 都在边缘盒子完成；"
                 "并发能力受模型规模与上下文长度限制，需按量化配置实测。",
    "edge-gateway-cascade": "边-网关分级级联：Stage1 在摄像头/NVR，Stage2/3 在区域网关 GPU 集群；"
                            "候选窗口与轨迹元数据经局域网传输，带宽节省取决于候选频率与窗口长度。",
    "edge-cloud-api": "边-云 API 协同：前两级留在边缘，核心切片经加密公网调用商用视觉 API；"
                      "需另计 Token 费用、公网排队时延波动与视频出站合规审查。",
}


@dataclass
class PipelineStats:
    """一次运行的真实计量，成本模型只从这里取值。"""

    camera_hours: float = 0.0
    total_video_seconds: float = 0.0
    frames: int = 0
    dropped_frames: int = 0
    stage1_gpu_ms: float = 0.0
    candidates: int = 0
    candidate_video_seconds: float = 0.0
    stage2_gpu_ms: float = 0.0
    stage2_processed_seconds: float = 0.0
    stage3_input_seconds: float = 0.0
    stage3_tokens_in: int = 0
    stage3_tokens_out: int = 0
    stage3_gpu_ms: float = 0.0
    stage3_calls: int = 0
    displayed_alarms: int = 0
    deferred_alarms: int = 0
    human_review_minutes: float = 0.0
    egress_bytes: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def compute(stats: PipelineStats, cfg: dict, topology: Optional[str] = None,
            cameras: Optional[int] = None) -> dict:
    topology = topology or str(cfg.get("topology", "edge-gateway-cascade"))
    if topology not in TOPOLOGIES:
        raise ValueError(f"未知拓扑：{topology}")
    stage = cfg.get("stage", {}) or {}
    price = cfg.get("price", {}) or {}
    fb = cfg.get("feedback", {}) or {}

    camera_hours = max(1e-9, stats.camera_hours)
    total_s = max(1e-9, stats.total_video_seconds)
    n_cameras = cameras or max(1, int(round(camera_hours))) or 1

    c_always_on = (stats.stage1_gpu_ms / 1000.0) / camera_hours
    r1 = clamp(stats.candidate_video_seconds / total_s, 0.0, 1.0)
    cand_hours = stats.candidate_video_seconds / 3600.0
    c2 = (stats.stage2_gpu_ms / 1000.0) / cand_hours if cand_hours > 1e-9 else 0.0
    r2 = clamp(safe_div(stats.stage3_input_seconds, stats.candidate_video_seconds), 0.0, 1.0)
    stage3_hours = stats.stage3_input_seconds / 3600.0
    c3_gpu = (stats.stage3_gpu_ms / 1000.0) / stage3_hours if stage3_hours > 1e-9 else 0.0

    gpu_second_price = float(price.get("gpu_second", 0.000333))
    human_hour_price = float(price.get("human_hour", 18.0))
    egress_price = float(price.get("egress_gb", 0.08))
    api_in = float(price.get("api_input_token", 0.0000005))
    api_out = float(price.get("api_output_token", 0.000002))

    gpu_s_per_ch = c_always_on + r1 * c2 + r1 * r2 * c3_gpu
    stage3_share = clamp(safe_div(r1 * r2 * c3_gpu, gpu_s_per_ch), 0.0, 1.0)
    stage1_share = clamp(safe_div(c_always_on, gpu_s_per_ch), 0.0, 1.0)

    # API 计费折算回"每摄像头小时"（仅 edge-cloud-api 使用）
    api_cost_per_ch = (stats.stage3_tokens_in / camera_hours) * api_in + \
                      (stats.stage3_tokens_out / camera_hours) * api_out

    egress_gb_per_ch = (stats.egress_bytes / (1024 ** 3)) / camera_hours
    if topology == "edge-only":
        egress_gb_per_ch = 0.0
    feedback_human_minutes_per_ch = stats.human_review_minutes / camera_hours
    reflection_minutes_per_ch = float(fb.get("reflection_minutes_per_camera_week", 30.0)) / (7.0 * 24.0)
    c_feedback_money = (feedback_human_minutes_per_ch + reflection_minutes_per_ch) / 60.0 * human_hour_price

    gpu_money_per_ch = gpu_s_per_ch * gpu_second_price
    egress_money_per_ch = egress_gb_per_ch * egress_price

    if topology == "edge-cloud-api":
        stage3_money = api_cost_per_ch
        compute_money = c_always_on * gpu_second_price + r1 * c2 * gpu_second_price + stage3_money
    else:
        compute_money = gpu_money_per_ch
    total_money_per_ch = compute_money + egress_money_per_ch + c_feedback_money

    sensitivity = _sensitivity(cfg)

    return {
        "topology": topology,
        "topology_note": TOPOLOGY_NOTES[topology],
        "units": {
            "cost_per": "camera-hour",
            "compute": "GPU-second",
            "money": "currency",
            "note": "GPU 时间与货币并行报告；人工工时另列，不与 GPU 秒混用。",
        },
        "measured": {
            "camera_hours": round(camera_hours, 4),
            "total_video_hours": round(total_s / 3600.0, 4),
            "frames": stats.frames,
            "dropped_frames": stats.dropped_frames,
            "candidates": stats.candidates,
            "candidate_video_hours": round(cand_hours, 6),
            "stage2_processed_hours": round(stats.stage2_processed_seconds / 3600.0, 6),
            "stage3_input_hours": round(stage3_hours, 6),
            "stage3_calls": stats.stage3_calls,
            "stage3_tokens_in": stats.stage3_tokens_in,
            "stage3_tokens_out": stats.stage3_tokens_out,
            "human_review_minutes": round(stats.human_review_minutes, 2),
            "egress_gb": round(stats.egress_bytes / (1024 ** 3), 6),
        },
        "ratios": {
            "r1_candidate_video_ratio": round(r1, 6),
            "r2_stage2_to_stage3_ratio": round(r2, 6),
            "r1_x_r2": round(r1 * r2, 8),
        },
        "components_gpu_seconds_per_camera_hour": {
            "C_always_on_stage1": round(c_always_on, 6),
            "C2_per_candidate_video_hour": round(c2, 6),
            "r1_times_C2": round(r1 * c2, 6),
            "C3_per_input_video_hour": round(c3_gpu, 6),
            "r1_r2_times_C3": round(r1 * r2 * c3_gpu, 6),
            "total_gpu_seconds": round(gpu_s_per_ch, 6),
        },
        "components_money_per_camera_hour": {
            "compute": round(compute_money, 6),
            "egress": round(egress_money_per_ch, 6),
            "feedback_human": round(c_feedback_money, 6),
            "total": round(total_money_per_ch, 6),
        },
        "shares": {
            "stage1_share_of_gpu": round(stage1_share, 4),
            "stage3_share_of_gpu": round(stage3_share, 4),
        },
        "feedback": {
            "human_minutes_per_camera_hour": round(feedback_human_minutes_per_ch, 4),
            "reflection_minutes_per_camera_hour": round(reflection_minutes_per_ch, 4),
        },
        "totals": {
            "cameras": n_cameras,
            "money_per_day": round(total_money_per_ch * 24.0 * n_cameras, 4),
            "money_per_month": round(total_money_per_ch * 24.0 * 30.0 * n_cameras, 4),
        },
        "sensitivity": sensitivity,
        "caveats": [
            "后级输入减少后，总成本与显存占用不一定按相同比例缩减。",
            "窗口变长/重叠、重试或多轮调用，须按每摄像头小时各级调用次数乘平均单次成本核算。",
            "排队、峰值并发与常驻模型显存应分别记录，不能混入单次前向时间。",
            "边缘侧并发数须按实际量化配置与上下文长度实测，本模型不含显存溢出判定。",
        ],
    }


def _sensitivity(cfg: dict) -> dict:
    sens = cfg.get("sensitivity", {}) or {}
    r1_lo, r1_hi = (float(x) for x in sens.get("r1_range", [0.01, 0.05]))
    r2_lo, r2_hi = (float(x) for x in sens.get("r2_range", [0.05, 0.2]))
    steps = max(2, int(sens.get("steps", 5)))
    rows = []
    products = []
    for i in range(steps):
        r1 = r1_lo + (r1_hi - r1_lo) * i / (steps - 1)
        row = []
        for j in range(steps):
            r2 = r2_lo + (r2_hi - r2_lo) * j / (steps - 1)
            product = r1 * r2
            row.append(round(product, 8))
            products.append(product)
        rows.append({"r1": round(r1, 4), "r1_x_r2": row})
    return {
        "r1_range": [r1_lo, r1_hi],
        "r2_range": [r2_lo, r2_hi],
        "steps": steps,
        "matrix": rows,
        "product_min": round(min(products), 8),
        "product_max": round(max(products), 8),
        "paper_reference": "论文 7.2 节算术示例：r1∈[1%,5%]、r2∈[5%,20%] 时乘积落在 5e-4~1e-2",
        "matches_paper_range": bool(
            abs(min(products) - 5e-4) <= 2e-4 and abs(max(products) - 1e-2) <= 2e-3),
    }


def compare_topologies(stats: PipelineStats, cfg: dict, cameras: int = 8) -> list[dict]:
    """三种部署拓扑在同一实测计量下的成本对比。"""
    return [compute(stats, cfg, topology=t, cameras=cameras) for t in TOPOLOGIES]


def estimate_egress_bytes(stats: PipelineStats, cfg: dict) -> int:
    """按码率估算候选窗口出站流量（用于成本模型）。"""
    bitrate = float((cfg.get("stage", {}) or {}).get("encode_bitrate_mbps", 2.0))
    return int(stats.candidate_video_seconds * bitrate * 1_000_000 / 8.0)
