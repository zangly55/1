"""通用工具：IO、日志、哈希、统计、随机数。"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, Sequence

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"


def get_logger(name: str = "cvalarm", level: str | int | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        logger.propagate = False
    if level is not None:
        logger.setLevel(level.upper() if isinstance(level, str) else level)
    elif logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)
    return logger


# --------------------------------------------------------------------------- 时间


def now_iso() -> str:
    """UTC ISO-8601 时间戳（秒精度），用于审计日志。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ts_to_iso(seconds_since_epoch: float) -> str:
    return datetime.fromtimestamp(seconds_since_epoch, timezone.utc).replace(microsecond=0).isoformat()


def fmt_hms(seconds: float) -> str:
    """把秒数格式化为 HH:MM:SS（用于告警卡片与时延展示）。"""
    if seconds is None:
        return "-"
    sign = "-" if seconds < 0 else ""
    seconds = abs(float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{sign}{h:02d}:{m:02d}:{s:05.2f}"


def fmt_duration(seconds: float) -> str:
    """人类可读的时长（用于累计在场时长展示）。"""
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m{seconds % 60:04.1f}s"
    return f"{int(seconds // 3600)}h{int(seconds % 3600 // 60):02d}m"


# --------------------------------------------------------------------------- IO


def ensure_dir(path: str | os.PathLike[str]) -> str:
    path = os.fspath(path)
    if path:
        os.makedirs(path, exist_ok=True)
    return path


def read_json(path: str | os.PathLike[str], default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def write_json(path: str | os.PathLike[str], obj: Any, indent: int = 2) -> str:
    ensure_dir(os.path.dirname(os.fspath(path)) or ".")
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=indent))
    return os.fspath(path)


def atomic_write_text(path: str | os.PathLike[str], text: str) -> str:
    """先写临时文件再原子替换，避免并发读到半截文件。"""
    path = os.fspath(path)
    directory = os.path.dirname(path) or "."
    ensure_dir(directory)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def append_jsonl(path: str | os.PathLike[str], records: Iterable[Any]) -> int:
    ensure_dir(os.path.dirname(os.fspath(path)) or ".")
    n = 0
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: str | os.PathLike[str]) -> Iterator[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)
    except FileNotFoundError:
        return


def write_jsonl(path: str | os.PathLike[str], records: Iterable[Any]) -> int:
    ensure_dir(os.path.dirname(os.fspath(path)) or ".")
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    atomic_write_text(path, text)
    return text.count("\n")


# --------------------------------------------------------------------------- 哈希


def canonical_json(obj: Any) -> str:
    """规范化 JSON：键排序、紧凑分隔符、不转义中文，用于内容寻址。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def content_hash(obj: Any, length: int = 12) -> str:
    """类 Git 的内容哈希：同样内容得到同样哈希，便于规则版本追踪。"""
    return sha256_hex(canonical_json(obj))[:length]


# --------------------------------------------------------------------------- 统计


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


def percentile(values: Sequence[float], q: float) -> float:
    """线性插值分位数（q ∈ [0,1]），空序列返回 NaN。"""
    vals = sorted(float(v) for v in values)
    if not vals:
        return float("nan")
    if len(vals) == 1:
        return vals[0]
    pos = clamp(q, 0.0, 1.0) * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(vals) - 1)
    frac = pos - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def mean(values: Sequence[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else float("nan")


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """二项比例的 Wilson 置信区间，小样本比正态近似稳健（用于漏检率估计）。"""
    if trials <= 0:
        return (0.0, 1.0)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return (clamp(centre - margin, 0.0, 1.0), clamp(centre + margin, 0.0, 1.0))


def round_floats(obj: Any, ndigits: int = 4) -> Any:
    """递归四舍五入，便于把人读的报告与小数值写入磁盘。"""
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_floats(v, ndigits) for v in obj]
    return obj


# --------------------------------------------------------------------------- 随机


class Rng:
    """带命名子流的确定性随机源：同一 seed 下各模块互不干扰。"""

    def __init__(self, seed: int = 7) -> None:
        self.seed = int(seed)

    def stream(self, name: str) -> random.Random:
        return random.Random(f"{self.seed}:{name}")


def jitter(rng: random.Random, base: float, rel: float = 0.15) -> float:
    """在 base 附近做乘性抖动（模拟排队、网络、解码时延波动）。"""
    return max(0.0, base * (1.0 + rng.uniform(-rel, rel)))


# --------------------------------------------------------------------------- 度量


class Stopwatch:
    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self._t0

    def reset(self) -> None:
        self._t0 = time.perf_counter()
