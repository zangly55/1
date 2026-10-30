"""Portable visual evidence boundary: local frame manifest or explicitly configured media."""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
from pathlib import Path

from .evidence import media_info


def visual_frames(cfg, candidate, stage2):
    start, end = stage2.interval or candidate.window
    end = min(end, candidate.t_trigger)
    manifest = cfg.get("stage3.vlm.frames_manifest", "")
    limit = max(1, min(16, int(cfg.get("stage3.vlm.max_frames", 3))))
    if manifest:
        path = Path(cfg.resolve(manifest))
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = sorted((x for x in data.get(candidate.camera_id, [])
                       if start <= float(x["ts"]) <= end), key=lambda x: float(x["ts"]))
        if not rows:
            raise ValueError("候选区间没有已到达的真实图像")
        indices = sorted({round(i * (len(rows)-1) / max(1, limit-1)) for i in range(limit)})
        out = []
        for i in indices:
            row = rows[i]
            image_path = (path.parent / row["path"]).resolve()
            payload = image_path.read_bytes()
            mime = mimetypes.guess_type(str(image_path))[0]
            if mime not in ("image/jpeg", "image/png", "image/webp"):
                raise ValueError("视觉证据仅支持 JPEG/PNG/WebP")
            out.append({"ts":float(row["ts"]), "frame_idx":int(row.get("frame_idx", i)),
                        "sha256":hashlib.sha256(payload).hexdigest(),
                        "url":f"data:{mime};base64," + base64.b64encode(payload).decode("ascii")})
        return out
    media = media_info(cfg, candidate.camera_id)
    if not media.get("available"):
        raise ValueError("VLM 尚未配置真实视频或 frames_manifest，禁止以文字冒充视觉核验")
    try:
        import cv2
    except ImportError as exc:
        raise ValueError("读取真实视频需要安装可选 video 依赖") from exc
    cap = cv2.VideoCapture(media["path"])
    try:
        if not cap.isOpened():
            raise ValueError("无法解码媒体文件")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            raise ValueError("视频缺少有效帧率")
        out = []
        # Select frames at or before the available timestamp, never after it.
        for idx in sorted({int((start + (end-start)*i/max(1,limit-1))*fps) for i in range(limit)}):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            actual_idx = int(round(cap.get(cv2.CAP_PROP_POS_FRAMES))) - 1
            if not ok or actual_idx < 0 or actual_idx / fps > end + 1e-6:
                raise ValueError("证据帧解码失败或超出已到达时间")
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                raise ValueError("证据帧编码失败")
            payload = encoded.tobytes()
            out.append({"ts":actual_idx/fps, "frame_idx":actual_idx,
                        "sha256":hashlib.sha256(payload).hexdigest(),
                        "url":"data:image/jpeg;base64," + base64.b64encode(payload).decode("ascii")})
        return out
    finally:
        cap.release()
