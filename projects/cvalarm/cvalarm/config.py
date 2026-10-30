"""配置加载与校验。

所有可调参数集中在 config/default.json；一次运行可用 --config 追加覆盖文件，
或 --set a.b=c 做点号路径覆盖。配置在进程内只读，便于复现实验。
"""
from __future__ import annotations

import copy
import json
import os
from typing import Any, Iterable, Mapping

from .util import get_logger, read_json

LOG = get_logger("cvalarm.config")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def bundled_path(relative: str) -> str:
    source = os.path.join(PROJECT_ROOT, relative)
    if os.path.isfile(source):
        return source
    return os.path.join(os.path.dirname(__file__), "resources", relative)


DEFAULT_CONFIG_PATH = bundled_path("config/default.json")


class ConfigError(ValueError):
    pass


class Config:
    """点号访问的只读配置视图。"""

    def __init__(self, data: Mapping[str, Any], base_dir: str | None = None) -> None:
        self._data: dict[str, Any] = copy.deepcopy(dict(data))
        source_checkout = os.path.isfile(os.path.join(PROJECT_ROOT, "config", "default.json"))
        self.base_dir = base_dir or (PROJECT_ROOT if source_checkout else os.getcwd())

    # ---------------------------------------------------------------- 载入
    @classmethod
    def load(cls, paths: Iterable[str] | None = None,
             overrides: Mapping[str, Any] | None = None,
             base_dir: str | None = None) -> "Config":
        data = read_json(DEFAULT_CONFIG_PATH, default=None)
        if data is None:
            raise ConfigError(f"默认配置缺失：{DEFAULT_CONFIG_PATH}")
        cfg = cls(data, base_dir=base_dir)
        for path in paths or []:
            if not path:
                continue
            payload = read_json(path, default=None)
            if payload is None:
                raise ConfigError(f"配置文件不存在或不是合法 JSON：{path}")
            cfg.merge(payload)
        if overrides:
            for dotted, value in overrides.items():
                cfg.set(dotted, value)
        cfg.validate()
        return cfg

    # ---------------------------------------------------------------- 访问
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def section(self, name: str) -> dict:
        value = self.get(name, {})
        return value if isinstance(value, dict) else {}

    def set(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        node = self._data
        for part in parts[:-1]:
            nxt = node.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                node[part] = nxt
            node = nxt
        node[parts[-1]] = _coerce(value)

    def merge(self, other: Mapping[str, Any]) -> None:
        _deep_merge(self._data, other)

    def as_dict(self) -> dict:
        return copy.deepcopy(self._data)

    def save(self, path: str) -> str:
        from .util import write_json

        return write_json(path, self._data)

    # ---------------------------------------------------------------- 路径
    def resolve(self, path: str) -> str:
        """源码版相对工程根目录；安装版相对工作目录，内置配置从包资源读取。"""
        if not path:
            return path
        if os.path.isabs(path):
            return path
        resolved = os.path.normpath(os.path.join(self.base_dir, path))
        if not os.path.exists(resolved) and path.replace("\\", "/").startswith("config/"):
            resource = bundled_path(path)
            if os.path.isfile(resource):
                return resource
        return resolved

    # ---------------------------------------------------------------- 校验
    def validate(self) -> None:
        errors: list[str] = []

        def need(cond: bool, msg: str) -> None:
            if not cond:
                errors.append(msg)

        dwell = self.get("fsm.dwell_threshold_s")
        need(isinstance(dwell, (int, float)) and dwell > 0, "fsm.dwell_threshold_s 必须为正数")
        need(self.get("fsm.debounce_frames", 0) >= 1, "fsm.debounce_frames 必须 >= 1")
        need(self.get("fsm.occlusion_tolerance_frames", 0) >= 1,
             "fsm.occlusion_tolerance_frames 必须 >= 1")
        need(self.get("fsm.exit_frames", 0) >= 1, "fsm.exit_frames 必须 >= 1")
        need(self.get("fsm.missing_window_s", 0) > 0, "fsm.missing_window_s 必须为正数")
        need(self.get("fsm.reid_policy") in ("precise", "strict", "loose"),
             "fsm.reid_policy 必须是 precise/strict/loose 之一")
        lo = self.get("stage2.tau_reject", 0.0)
        hi = self.get("stage2.tau_confirm", 1.0)
        need(0.0 <= lo < hi <= 1.0, "stage2 阈值需满足 0 <= tau_reject < tau_confirm <= 1")
        need(self.get("tracker.high_thresh", 0) > self.get("tracker.low_thresh", 0),
             "tracker.high_thresh 必须大于 low_thresh")
        need(self.get("metrics.tta_deadline_s", 0) > 0, "metrics.tta_deadline_s 必须为正数")
        for cls_name in self.get("stage3.event_classes", []):
            need(isinstance(cls_name, str) and cls_name, "stage3.event_classes 只能是非空字符串")
        topology = self.get("cost.topology")
        need(topology in ("edge-only", "edge-gateway-cascade", "edge-cloud-api"),
             f"cost.topology 非法：{topology}")
        if errors:
            raise ConfigError("配置校验失败：\n  - " + "\n  - ".join(errors))
        if self.get("protocol.mode") == "holdout":
            blocks = [self.get("protocol." + key, {}) for key in ("dev", "test")]
            for block in blocks:
                ranges = block.get("time_ranges", [])
                if not ranges or any(len(x) != 2 or x[0] < 0 or x[0] >= x[1] for x in ranges):
                    raise ConfigError("holdout 必须提供有效且非空的半开时间区间")
                ordered = sorted(ranges)
                if any(a[1] > b[0] for a,b in zip(ordered, ordered[1:])):
                    raise ConfigError("同一划分的时间区间不能重叠")
            dc, tc = (set(b.get("cameras", [])) for b in blocks)
            if not dc or not tc or dc & tc:
                if any(max(a[0],b[0]) < min(a[1],b[1])
                       for a in blocks[0]["time_ranges"] for b in blocks[1]["time_ranges"]):
                    raise ConfigError("开发与测试区间重叠")

    # ---------------------------------------------------------------- 便捷视图
    @property
    def fsm(self) -> dict:
        return self.section("fsm")

    @property
    def tracker(self) -> dict:
        return self.section("tracker")

    @property
    def stage2(self) -> dict:
        return self.section("stage2")

    @property
    def stage3(self) -> dict:
        return self.section("stage3")

    @property
    def metrics(self) -> dict:
        return self.section("metrics")

    @property
    def cost(self) -> dict:
        return self.section("cost")

    @property
    def event_classes(self) -> list[str]:
        return list(self.get("stage3.event_classes", []))

    def describe(self) -> str:
        """人类可读的关键参数摘要（写入 run_meta.json）。"""
        keys = [
            "project.name", "project.version", "fsm.dwell_threshold_s", "fsm.debounce_frames",
            "fsm.occlusion_tolerance_frames", "fsm.exit_frames", "fsm.missing_window_s",
            "fsm.reid_policy", "stage2.tau_confirm", "stage2.tau_reject", "stage3.mode",
            "cost.topology", "metrics.tta_deadline_s",
        ]
        return json.dumps({k: self.get(k) for k in keys}, ensure_ascii=False)


def _coerce(value: Any) -> Any:
    """命令行的 --set 传进来都是字符串，这里做最小类型推断。"""
    if not isinstance(value, str):
        return value
    text = value.strip()
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        if text.startswith("0") and len(text) > 1 and text[1].isdigit():
            raise ValueError
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    if text.startswith("[") or text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return value


def _deep_merge(base: dict, extra: Mapping[str, Any]) -> dict:
    for key, value in extra.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def load_config(config_files: Iterable[str] | None = None,
                sets: Iterable[str] | None = None,
                base_dir: str | None = None) -> Config:
    overrides: dict[str, Any] = {}
    for item in sets or []:
        if "=" not in item:
            raise ConfigError(f"--set 需要 key=value 形式，收到：{item}")
        key, value = item.split("=", 1)
        overrides[key.strip()] = value.strip()
    return Config.load(config_files, overrides=overrides, base_dir=base_dir)
