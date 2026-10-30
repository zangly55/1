"""证据回放：为每张告警卡片构造"可核验"的时间片段、前后文、关键帧与回放入口。

三件事必须分清（否则就是拿示意图冒充视频）：
  1. **片段与前后文**（真实数据）：`clip = [start - pre_roll, end + post_roll]`，
     配置了媒体文件时看板可通过 `/media/<camera>` 支持 Range 播放原片段；
  2. **关键帧示意图**（重绘）：按检测/跟踪结果重绘 ROI 与目标框，
     明确标注"由检测结果重绘，非原始视频帧"；
  3. **回放清单**：即使没有媒体文件，也给出机位、时间区间、关键帧编号，
     方便人工按清单去 NVR 里取证。
"""
from __future__ import annotations

import os
from typing import Any, Optional, Sequence

from .geometry import BBox
from .util import clamp, get_logger

LOG = get_logger("cvalarm.evidence")

PANEL_W = 208
PANEL_H = 132
PAD = 10
HEADER_H = 18


# --------------------------------------------------------------------------- 媒体


def media_info(cfg: Any, camera_id: str) -> dict:
    """媒体可用性：只有真的配置了文件才声称可以回放原片段。"""
    media = (cfg.get("deployment.media", {}) or {}) if cfg is not None else {}
    mapping = media.get("cameras", {}) or {}
    rel = mapping.get(camera_id) or ""
    if not rel:
        return {
            "available": False,
            "url_template": "",
            "reason": "未配置该机位的媒体文件；接入后在 deployment.media.cameras 里登记即可回放原片段",
        }
    root = cfg.resolve(str(media.get("root", "") or "."))
    path = rel if os.path.isabs(rel) else os.path.join(root, rel)
    if not os.path.exists(path):
        return {
            "available": False,
            "url_template": "",
            "reason": f"媒体文件不存在：{path}",
        }
    return {
        "available": True,
        "url_template": f"/media/{camera_id}",
        "path": path,
        "reason": "",
    }


# --------------------------------------------------------------------------- 关键帧


def _pick_times(interval: tuple[float, float], clip: tuple[float, float], n: int) -> list[float]:
    start, end = interval
    c0, c1 = clip
    targets = [start, (start + end) / 2.0, end] if n >= 3 else \
        [start + (end - start) * i / max(1, n - 1) for i in range(max(1, n))]
    out = []
    for t in targets[:max(1, n)]:
        out.append(round(clamp(t, c0, c1), 3))
    # 去重但保持顺序
    seen: set[float] = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _nearest_box(history_boxes: Sequence[Sequence[float]], ts: float) -> Optional[BBox]:
    best = None
    best_d = float("inf")
    for item in history_boxes or []:
        try:
            t = float(item[0])
            box = (float(item[1]), float(item[2]), float(item[3]), float(item[4]))
        except (TypeError, ValueError, IndexError):
            continue
        d = abs(t - ts)
        if d < best_d:
            best, best_d = box, d
    return best


# --------------------------------------------------------------------------- SVG


def _panel(rois: Sequence[dict], bbox: Optional[BBox], ts: float, role: str,
           width: int = PANEL_W, height: int = PANEL_H) -> str:
    inner_w = width - 2 * PAD
    inner_h = height - 2 * PAD - HEADER_H
    parts = [f'<g><rect x="0" y="0" width="{width}" height="{height}" rx="6" '
             f'fill="#0b0f16" stroke="#2a3441"/>']
    for roi in rois:
        poly = roi.get("polygon") or []
        if len(poly) < 3:
            continue
        pts = " ".join(
            f"{PAD + float(p[0]) * inner_w:.1f},{PAD + HEADER_H + float(p[1]) * inner_h:.1f}"
            for p in poly)
        parts.append(f'<polygon points="{pts}" fill="rgba(74,168,255,0.10)" '
                     f'stroke="#4aa8ff" stroke-width="1"/>')
        parts.append(f'<text x="{PAD}" y="{PAD + 11}" fill="#4aa8ff" font-size="9" '
                     f'font-family="monospace">{_esc(roi.get("roi_id", ""))}</text>')
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        rx = PAD + min(x1, x2) * inner_w
        ry = PAD + HEADER_H + min(y1, y2) * inner_h
        rw = abs(x2 - x1) * inner_w
        rh = abs(y2 - y1) * inner_h
        parts.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{max(1.5, rw):.1f}" '
                     f'height="{max(1.5, rh):.1f}" fill="rgba(240,136,62,0.22)" '
                     f'stroke="#f0883e" stroke-width="1.4"/>')
        parts.append(f'<line x1="{rx:.1f}" y1="{ry + rh:.1f}" x2="{rx + rw:.1f}" '
                     f'y2="{ry + rh:.1f}" stroke="#f0883e" stroke-width="2"/>')
    label = {"start": "片段起点", "mid": "区间中段", "end": "证据末端",
             "trigger": "触发时刻"}.get(role, role)
    parts.append(f'<text x="{width - PAD}" y="{PAD + 11}" fill="#8b98a5" font-size="9" '
                 f'text-anchor="end" font-family="monospace">{label}</text>')
    parts.append(f'<text x="{PAD}" y="{height - 6}" fill="#e6edf3" font-size="10" '
                 f'font-family="monospace">t={ts:.1f}s</text>')
    parts.append("</g>")
    return "".join(parts)


def _esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def schematic_svg(rois: Sequence[dict], keyframes: Sequence[dict]) -> str:
    """把关键帧重绘成横向证据条（纯 SVG，可离线嵌入页面）。"""
    if not keyframes:
        return ""
    n = len(keyframes)
    total_w = PANEL_W * n + 8 * (n - 1)
    total_h = PANEL_H + 20
    parts = [f'<svg viewBox="0 0 {total_w} {total_h}" width="100%" '
             f'height="{total_h}" xmlns="http://www.w3.org/2000/svg" role="img">']
    parts.append(f'<text x="0" y="13" fill="#8b98a5" font-size="10" '
                 f'font-family="monospace">证据示意：由检测/跟踪结果重绘，非原始视频帧</text>')
    for i, item in enumerate(keyframes):
        x = i * (PANEL_W + 8)
        parts.append(f'<g transform="translate({x},{20})">')
        parts.append(_panel(rois, item.get("bbox"), float(item.get("ts", 0.0)),
                            str(item.get("role", ""))))
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- 组装


def build_evidence(cfg: Any, candidate: Any, interval: tuple[float, float],
                   rois: Sequence[dict]) -> dict:
    """构造卡片的 evidence 块（片段 / 前后文 / 关键帧 / 回放入口 / 示意图）。"""
    ev_cfg = (cfg.get("evidence", {}) or {}) if cfg is not None else {}
    if not bool(ev_cfg.get("enabled", True)):
        return {"enabled": False}
    pre = float(ev_cfg.get("pre_roll_s", 5.0))
    post = float(ev_cfg.get("post_roll_s", 0.0))
    k = int(ev_cfg.get("keyframes", 3))
    requested_end = interval[1] + post
    clip = (max(0.0, interval[0] - pre), min(requested_end, candidate.t_trigger))
    times = _pick_times(interval, clip, k)
    roles = ["start"] + ["mid"] * max(0, len(times) - 2) + ["end"] if len(times) > 1 else ["start"]
    history_boxes = (candidate.snapshot or {}).get("history_boxes") or []
    keyframes = []
    for i, ts in enumerate(times):
        keyframes.append({
            "ts": round(ts, 3),
            "role": roles[i] if i < len(roles) else "mid",
            "bbox": [round(v, 4) for v in (_nearest_box(history_boxes, ts) or [])] or None,
        })
    # 触发时刻单独补一帧：它是"条件成立"的可视证据，也是被截断的位置
    trigger_ts = round(float(candidate.t_trigger), 3)
    if all(abs(trigger_ts - kf["ts"]) > 0.5 for kf in keyframes):
        keyframes.append({
            "ts": trigger_ts, "role": "trigger",
            "bbox": [round(v, 4) for v in (_nearest_box(history_boxes, trigger_ts) or [])] or None,
        })
    media = media_info(cfg, candidate.camera_id)
    evidence = {
        "available_at": candidate.t_trigger,
        "requested_post_roll_s": post,
        "future_context_pending_s": max(0.0, requested_end - candidate.t_trigger),
        "enabled": True,
        "clip": {"start": round(clip[0], 3), "end": round(clip[1], 3),
                 "pre_roll_s": pre, "post_roll_s": post,
                 "duration_s": round(clip[1] - clip[0], 3)},
        "interval": [round(interval[0], 3), round(interval[1], 3)],
        "keyframes": keyframes,
        "media": media,
        "replay_mode": "media_range" if media.get("available") else "schematic_only",
        "manifest": (f"{candidate.camera_id} [{clip[0]:.1f}, {clip[1]:.1f}] s，"
                     f"关键帧 {len(keyframes)} 个；按此清单可在 NVR 中取证"),
    }
    if bool(ev_cfg.get("schematic", True)):
        evidence["schematic_svg"] = schematic_svg(rois, keyframes)
    return evidence
