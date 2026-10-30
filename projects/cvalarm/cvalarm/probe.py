"""模型与接口探测：把"能不能加载、接口通不通、数据齐不齐"写成可复现记录。

对应工程方向第一步"实测模型加载、推理与接口交换"：在真实资源到位前，
先把每个环节的可验证状态记下来——未配置就如实写 not_configured，不假装通过。
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from . import __version__
from .config import Config
from .evidence import media_info
from .locator import load_calibration
from .rules import RuleRegistry, validate_ruleset
from .util import get_logger, now_iso, read_json

LOG = get_logger("cvalarm.probe")

OK = "ok"
WARN = "warn"
FAIL = "fail"
INFO = "info"


def _row(component: str, status: str, detail: str, **extra: Any) -> dict:
    row = {"component": component, "status": status, "detail": detail}
    row.update(extra)
    return row


def probe_environment(cfg: Config, call: bool = False,
                      state_dir: Optional[str] = None) -> dict:
    state = state_dir or cfg.resolve(str(cfg.get("runtime.state_dir", "state")))
    rows: list[dict] = []

    rows.append(_row("python", INFO,
                     f"{sys.version.split()[0]} on {platform.system()} {platform.machine()}",
                     cvalarm_version=__version__))

    # ---------------------------------------------------------------- 规则与标定
    try:
        registry = RuleRegistry(cfg, state)
        ruleset = registry.active()
        report = validate_ruleset(ruleset, cfg.event_classes)
        rows.append(_row(
            "ruleset", OK if report.ok else FAIL,
            f"{ruleset.ruleset_id}@{ruleset.version_label} hash={ruleset.digest} "
            f"{len(ruleset.rules)} 条；校验{'通过' if report.ok else '不通过'}；"
            f"告警 {len(report.warnings)} 条需人工确认",
            errors=report.errors[:5]))
    except Exception as exc:
        rows.append(_row("ruleset", FAIL, f"规则集加载失败：{exc}"))

    cal = load_calibration(cfg)
    rows.append(_row(
        "calibration", OK if cal.is_ok else WARN,
        (f"τ_reject={cal.tau_reject:.3f} τ_confirm={cal.tau_confirm:.3f} "
         f"负例={cal.hard_negative_windows} 版本={cal.version}")
        if cal.is_ok else
        "未完成同场景硬负例标定：低分窗口只会转人工，不会静默抑制（先跑 calibrate/demo）"))

    # ---------------------------------------------------------------- 授权记录
    auth_path = cfg.resolve(str(cfg.get("stage3.authorization_file", "")))
    if os.path.exists(auth_path):
        data = read_json(auth_path, default={}) or {}
        permits = data.get("permits", []) or []
        rows.append(_row("authorizations", OK if permits else WARN,
                         f"{auth_path}；许可 {len(permits)} 条"))
    else:
        rows.append(_row("authorizations", WARN,
                         f"文件不存在：{auth_path}；规程适用性将无法核验（不会静默抑制）"))

    # ---------------------------------------------------------------- 检测输入
    source_kind = str(cfg.get("probe.source_kind", "synthetic（内置合成流）"))
    rows.append(_row(
        "detector_input", WARN if "synthetic" in source_kind or "内置" in source_kind else OK,
        f"{source_kind}；接真实检测器时实现 FrameSource 或使用 --source jsonl 回放"))

    # ---------------------------------------------------------------- 打分头
    scorer_kind = str(cfg.get("stage2.scorer.kind", "heuristic"))
    if scorer_kind == "external":
        path = cfg.resolve(str(cfg.get("stage2.scorer.path", "")))
        ok = bool(path) and os.path.exists(path)
        rows.append(_row("interval_scorer", OK if ok else FAIL,
                         f"外部打分序列 {path}" if ok else f"外部打分序列缺失：{path}"))
    elif scorer_kind == "http":
        endpoint = str(cfg.get("stage2.scorer.endpoint", ""))
        rows.append(_row("interval_scorer", INFO if endpoint else FAIL,
                         "已配置本工程 HTTP 定位协议；未做真实推理验证" if endpoint else "HTTP 定位端点缺失"))
    else:
        rows.append(_row("interval_scorer", INFO,
                         "内置可解释参考打分头（生产替换点：VideoJev 式轻量打分头）"))

    # ---------------------------------------------------------------- VLM 端点
    vlm = cfg.section("stage3").get("vlm", {}) or {}
    endpoint = str(vlm.get("endpoint", "") or "")
    model = str(vlm.get("model", "") or "")
    key_env = str(vlm.get("api_key_env", "CVALARM_VLM_API_KEY"))
    has_key = bool(os.environ.get(key_env))
    if not endpoint:
        rows.append(_row("vlm_endpoint", WARN,
                         "未配置 stage3.vlm.endpoint：Stage3 使用规则参考核验器（有意为之的对照基线）"))
    elif not call:
        rows.append(_row("vlm_endpoint", INFO,
                         f"已配置 {endpoint}（model={model or '-'}，密钥环境变量 "
                         f"{key_env} {'已设置' if has_key else '未设置'}）；加 --call 做一次真实调用测试"))
    else:
        rows.append(_vlm_call(endpoint, model, key_env, float(vlm.get("timeout_s", 30))))

    # ---------------------------------------------------------------- 媒体
    media = cfg.get("deployment.media", {}) or {}
    mapping = media.get("cameras", {}) or {}
    if not mapping:
        rows.append(_row("media_replay", WARN,
                         "未登记视频文件：证据回放只展示重绘示意图与回放清单"))
    else:
        missing = [cam for cam in mapping if not media_info(cfg, cam).get("available")]
        rows.append(_row("media_replay", OK if not missing else WARN,
                         f"已登记 {len(mapping)} 路媒体文件"
                         + (f"；缺失 {missing}" if missing else "")))

    # ---------------------------------------------------------------- 成本参数
    vram = cfg.get("cost.stage.peak_vram_gb")
    rows.append(_row("resources", INFO if vram else WARN,
                     f"峰值显存实测值：{vram} GB" if vram else
                     "未登记实测峰值显存（cost.stage.peak_vram_gb）；报告会写未测"))

    fails = [r for r in rows if r["status"] == FAIL]
    warns = [r for r in rows if r["status"] == WARN]
    return {
        "probed_at": now_iso(),
        "config_digest": str(cfg.get("project.name", "")),
        "ok": not fails,
        "summary": {"total": len(rows), "fail": len(fails), "warn": len(warns),
                    "ok": len([r for r in rows if r["status"] == OK])},
        "rows": rows,
        "note": ("这是接口与数据就绪度探测，不是性能基准；"
                 "未配置的项如实标记，不代表系统已具备该能力。"),
    }


def _vlm_call(endpoint: str, model: str, key_env: str, timeout: float) -> dict:
    """真实调用一次：只验证接口通、能返回 JSON，不验证理解质量。"""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "只输出一个 JSON 对象，不要解释。"},
            {"role": "user", "content": '回复 {"ok": true}'},
        ],
        "max_tokens": 32,
        "temperature": 0.0,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get(key_env)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(endpoint, data=data, method="POST", headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        elapsed = round((time.perf_counter() - t0) * 1000.0, 1)
        usage = payload.get("usage", {}) or {}
        content = ""
        try:
            content = payload["choices"][0]["message"]["content"][:120]
        except (KeyError, IndexError, TypeError):
            pass
        return _row("vlm_endpoint", OK,
                    f"调用成功：{endpoint}（{elapsed} ms，token {usage.get('total_tokens', '?')}）"
                    f" 返回片段：{content}",
                    latency_ms=elapsed, tokens=usage)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        elapsed = round((time.perf_counter() - t0) * 1000.0, 1)
        return _row("vlm_endpoint", FAIL, f"调用失败（{elapsed} ms）：{exc}", latency_ms=elapsed)


def format_probe(result: dict) -> str:
    icon = {OK: "✓", WARN: "!", FAIL: "✗", INFO: "·"}
    lines = [f"接口与数据就绪度探测（{result['probed_at']}）",
             "-" * 72]
    for row in result["rows"]:
        lines.append(f"  {icon.get(row['status'], '?')} {row['component']:<16} {row['detail']}")
    s = result["summary"]
    lines.append("-" * 72)
    lines.append(f"  合计 {s['total']} 项：ok={s['ok']} warn={s['warn']} fail={s['fail']}")
    lines.append("  " + result["note"])
    return "\n".join(lines)
