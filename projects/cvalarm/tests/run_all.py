#!/usr/bin/env python
"""一键跑全部测试（单元 + CLI 冒烟 + 报告结构 + 可选渲染执行）。

用法：
    python tests/run_all.py            # 全部
    python tests/run_all.py -v         # 详细
    python tests/run_all.py -k fsm     # 只跑文件名含 fsm 的测试文件

输出：每个测试文件的用例数/失败数/耗时，以及总计与退出码。
不依赖 pytest：纯 unittest。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

SKIP_MODULES = {"helpers", "run_all"}


def discover_modules(keyword: str = "") -> list[str]:
    mods = []
    for name in sorted(os.listdir(HERE)):
        if not name.startswith("test_") or not name.endswith(".py"):
            continue
        stem = name[:-3]
        if stem in SKIP_MODULES:
            continue
        if keyword and keyword not in stem:
            continue
        mods.append(stem)
    return mods


def run_module(stem: str, verbosity: int) -> tuple[unittest.TestResult, float, int]:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f"tests.{stem}")
    if hasattr(suite, "countTestCases") and suite.countTestCases() == 0:
        suite = loader.loadTestsFromName(stem)
    count = suite.countTestCases()
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stderr)
    t0 = time.perf_counter()
    result = runner.run(suite)
    return result, time.perf_counter() - t0, count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cvalarm 全量测试运行器")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-k", "--keyword", default="", help="只跑文件名包含该关键字的测试文件")
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass

    modules = discover_modules(args.keyword)
    if not modules:
        print("没有匹配的测试文件", file=sys.stderr)
        return 2

    print("=" * 78)
    print(f"cvalarm 测试 · 共 {len(modules)} 个测试文件")
    print("=" * 78)
    total = failures = errors = skipped = 0
    rows = []
    t_all = time.perf_counter()
    for stem in modules:
        result, elapsed, count = run_module(stem, 2 if args.verbose else 0)
        total += result.testsRun
        failures += len(result.failures)
        errors += len(result.errors)
        skipped += len(result.skipped)
        rows.append((stem, result.testsRun, len(result.failures) + len(result.errors),
                     len(result.skipped), elapsed))

    print("=" * 78)
    print(f"{'测试文件':<34}{'用例':>6}{'失败':>6}{'跳过':>6}{'耗时(s)':>10}")
    print("-" * 78)
    for stem, n, bad, sk, elapsed in rows:
        flag = "  <-- FAIL" if bad else ""
        print(f"{stem:<34}{n:>6}{bad:>6}{sk:>6}{elapsed:>10.2f}{flag}")
    print("-" * 78)
    print(f"{'合计':<34}{total:>6}{failures + errors:>6}{skipped:>6}"
          f"{time.perf_counter() - t_all:>10.2f}")
    print("=" * 78)
    if skipped:
        print("提示：跳过的用例通常是需要 node 的可选渲染检查（不影响零依赖主链路）。")
    ok = failures == 0 and errors == 0
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
