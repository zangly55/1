"""可选深度检查：用 node + 最小 DOM 桩真正执行报告页的渲染脚本。

纯 Python 的结构检查见 `test_report_html.py`；这里补的是"脚本能不能跑"这一层：
所有 render 函数被执行、每个面板都被写入内容、证据示意图按卡片数量生成。

没有 node 时自动 skip，不破坏工程"零第三方依赖"的前提。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest

import helpers

NODE = shutil.which("node") or shutil.which("node.exe")
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_check.js")


@unittest.skipUnless(NODE and os.path.exists(SCRIPT), "需要 node 才能执行 DOM 桩渲染检查")
class TestRenderedPageRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="cvalarm-render-")
        cls.cfg, cls.run_dir = helpers.make_run(cls.tmp, with_report=True)
        cls.report = os.path.join(cls.run_dir, "report.html")

    def test_boot_runs_without_error(self):
        proc = subprocess.run([NODE, SCRIPT, self.report],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=120)
        self.assertEqual(proc.returncode, 0,
                         f"渲染检查失败：\n{proc.stdout}\n{proc.stderr}")
        self.assertIn("RENDER: PASS", proc.stdout or "")

    def test_self_contained_page_has_no_external_refs(self):
        with open(self.report, encoding="utf-8") as fh:
            html = fh.read()
        for needle in ("src=\"http", "href=\"http", "src=\"//", "href=\"//"):
            self.assertNotIn(needle, html)


if __name__ == "__main__":
    unittest.main()
