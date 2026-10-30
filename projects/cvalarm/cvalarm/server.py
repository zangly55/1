"""实时看板：标准库 http.server，无第三方依赖，无外网资源。

用途：值班室/演示现场直接打开 http://127.0.0.1:8080/ 查看最新运行结果，
页面每 4 秒轮询 /api/run 自动刷新（不依赖任何前端构建工具）。
"""
from __future__ import annotations

import json
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urlparse

from .config import Config
from .report import build_page_data
from .rules import RuleRegistry
from .util import get_logger, read_json, read_jsonl
from .webpage import render_page

LOG = get_logger("cvalarm.server")

_CONTENT_TYPES = {
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
    ".mkv": "video/x-matroska", ".avi": "video/x-msvideo", ".mov": "video/quicktime",
    ".ts": "video/mp2t", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
}


def _content_type(path: str) -> str:
    _, ext = os.path.splitext(path.lower())
    return _CONTENT_TYPES.get(ext, "application/octet-stream")


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "cvalarm-dashboard/1.0"
    cfg: Config
    run_dir: str
    state_dir: str

    def run_config(self) -> Config:
        meta = read_json(os.path.join(self.run_dir, "run_meta.json"), default={}) or {}
        config = Config(meta.get("effective_config") or self.cfg.as_dict(), base_dir=self.cfg.base_dir)
        # Explicit nonempty media configuration can remap files after relocation.
        if self.cfg.get("deployment.media.cameras"):
            config.set("deployment.media",self.cfg.get("deployment.media"))
        return config

    # ------------------------------------------------------------------ 路由
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                self._send_html(render_page({}, title="持续视频监控异常告警 · 实时看板", live=True))
            elif path == "/api/run":
                payload = build_page_data(self.run_dir, self.cfg, self.state_dir)
                self._send_json(payload)
            elif path == "/api/alarms":
                self._send_json(list(read_jsonl(os.path.join(self.run_dir, "alarms.jsonl"))))
            elif path == "/api/metrics":
                self._send_json(read_json(os.path.join(self.run_dir, "metrics.json"), default={}))
            elif path == "/api/feedback":
                from .feedback import FeedbackStore
                meta = read_json(os.path.join(self.run_dir, "run_meta.json"), default={}) or {}
                self._send_json([x for x in FeedbackStore(self.run_config(), self.state_dir).entries()
                                 if x.get("run_id") == meta.get("run_id")])
            elif path == "/api/cost":
                self._send_json(read_json(os.path.join(self.run_dir, "cost.json"), default={}))
            elif path == "/api/rules":
                registry = RuleRegistry(self.cfg, self.state_dir)
                self._send_json({"active": registry.active().to_dict(),
                                 "versions": registry.list_versions(),
                                 "ledger": registry.ledger(50)})
            elif path == "/api/health":
                self._send_json({"ok": True, "run_dir": self.run_dir,
                                 "files": sorted(os.listdir(self.run_dir))
                                 if os.path.isdir(self.run_dir) else []})
            elif path.startswith("/media/"):
                self._serve_media(path[len("/media/"):].strip("/"), head=False)
            else:
                self._send_json({"error": "not found", "path": path}, HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover - 服务端兜底
            LOG.exception("请求处理失败：%s", exc)
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/media/"):
            self._serve_media(path[len("/media/"):].strip("/"), head=True)
        else:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Length", "0")
            self.end_headers()

    # ------------------------------------------------------------------ 媒体回放
    def _media_path(self, camera_id: str) -> tuple[str, str]:
        """返回 (绝对路径, 错误说明)。未配置或文件不存在时路径为空。"""
        cfg = self.run_config()
        media = cfg.get("deployment.media", {}) or {}
        rel = (media.get("cameras", {}) or {}).get(camera_id) or ""
        if not rel:
            return ("", "未在 deployment.media.cameras 里登记该机位的视频文件")
        root = str(media.get("root", "") or "")
        path = rel if os.path.isabs(rel) else os.path.join(cfg.resolve(root or "."), rel)
        if not os.path.exists(path):
            return ("", f"媒体文件不存在：{path}")
        return (path, "")

    def _serve_media(self, camera_id: str, head: bool = False) -> None:
        path, err = self._media_path(camera_id)
        if not path:
            self._send_json({"error": err, "camera_id": camera_id}, HTTPStatus.NOT_FOUND)
            return
        size = os.path.getsize(path)
        ctype = _content_type(path)
        range_header = self.headers.get("Range", "")
        start, end = 0, size - 1
        partial = False
        if range_header.startswith("bytes="):
            spec = range_header[len("bytes="):].split(",")[0].strip()
            try:
                lo, _, hi = spec.partition("-")
                if lo:
                    start = max(0, int(lo))
                    end = int(hi) if hi else size - 1
                elif hi:
                    start = max(0, size - int(hi))
                    end = size - 1
                end = min(end, size - 1)
                partial = True
            except ValueError:
                start, end, partial = 0, size - 1, False
        if start > end or start >= size:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        length = end - start + 1
        self.send_response(HTTPStatus.PARTIAL_CONTENT if partial else HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if head:
            return
        with open(path, "rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_POST(self) -> None:
        """保留扩展点：处置界面回传 Confirm/Dismiss/Uncertain。"""
        path = urlparse(self.path).path
        if path != "/api/feedback":
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)
            return
        from .feedback import FeedbackEntry, FeedbackStore

        try:
            if not isinstance(payload, dict):
                raise ValueError("反馈必须是 JSON 对象")
            meta = read_json(os.path.join(self.run_dir, "run_meta.json"), default={}) or {}
            run_id = meta.get("run_id")
            if payload.get("run_id") != run_id or not run_id:
                raise ValueError("反馈 run_id 与当前运行不一致")
            alarm = next((a for a in read_jsonl(os.path.join(self.run_dir, "alarms.jsonl"))
                          if a.get("alarm_id") == payload.get("alarm_id")), None)
            if alarm is None or alarm.get("status") not in ("confirmed", "deferred"):
                raise ValueError("当前运行没有这条可复核告警")
            entry = FeedbackEntry(
                run_id=run_id,
                alarm_id=str(payload.get("alarm_id", "")),
                verdict=str(payload.get("verdict", "")),
                camera_id=alarm["camera_id"],
                event_class=alarm["event_class"],
                rule_version=alarm.get("rule_version", ""),
                reason_code=str(payload.get("reason_code", "")),
                note=str(payload.get("note", "")),
                operator=str(payload.get("operator", "operator")),
                ts_display=float(alarm.get("t_display", 0.0)),
            )
            saved = FeedbackStore(self.run_config(), self.state_dir).add(entry)
            self._send_json({"ok": True, "entry": saved})
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    # ------------------------------------------------------------------ 输出
    def _send_html(self, text: str) -> None:
        data = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:  # 用统一 logger，不污染 stderr 格式
        LOG.debug("%s - %s", self.address_string(), fmt % args)


def serve(run_dir: str, cfg: Config, host: str = "127.0.0.1", port: int = 8080,
          state_dir: Optional[str] = None) -> ThreadingHTTPServer:
    meta = read_json(os.path.join(run_dir,"run_meta.json"),default={}) or {}
    snapshot = Config(meta.get("effective_config") or cfg.as_dict(), base_dir=cfg.base_dir)
    handler = type("BoundDashboardHandler", (DashboardHandler,), {
        "cfg": cfg,
        "run_dir": os.path.abspath(run_dir),
        "state_dir": state_dir or snapshot.resolve(str(snapshot.get("runtime.state_dir", "state"))),
    })
    httpd = ThreadingHTTPServer((host, port), handler)
    LOG.info("看板已启动：http://%s:%d/  （数据目录 %s）", host, port, os.path.abspath(run_dir))
    return httpd


def serve_forever(run_dir: str, cfg: Config, host: str = "127.0.0.1", port: int = 8080,
                  state_dir: Optional[str] = None) -> None:
    httpd = serve(run_dir, cfg, host, port, state_dir)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        LOG.info("收到中断，关闭看板")
    finally:
        httpd.shutdown()
        httpd.server_close()


def serve_background(run_dir: str, cfg: Config, host: str = "127.0.0.1",
                     port: int = 8080) -> tuple[ThreadingHTTPServer, threading.Thread]:
    httpd = serve(run_dir, cfg, host, port)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread
