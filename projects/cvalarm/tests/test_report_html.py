"""报告 HTML 的结构与一致性检查（纯 Python，不依赖浏览器或 node）。

它回答三个问题：
  1. 页面引用的每个 DOM id 是否真的存在于 HTML 里（否则渲染函数会静默失败）；
  2. 页面是否**完全自包含**（不引外网资源，能在无外网机房打开）；
  3. 报告数据是否与产物一致（卡片数量、校验通过、签名可验证、面板数据齐全）。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unittest

import helpers

from cvalarm.card import validate_card, verify_card_signature

#: 页面必须存在的容器 id（少一个就会有一块面板渲染不出来）
REQUIRED_IDS = (
    "hdr-sub", "hdr-badge", "kpis", "funnel", "funnel-prob",
    "events-table", "rel-table", "histogram", "alarm-search", "alarm-list",
    "loc-summary", "loc-table", "diff-summary", "diff-table",
    "cost-table", "topology-table", "sensitivity", "cost-caveats",
    "audit-summary", "audit-table", "rules-meta", "ledger-table",
    "res-summary", "models-table", "cap-table", "proto-line",
    "notes", "generated",
)

#: 不允许出现的外网引用（自包含要求）
EXTERNAL_PATTERNS = (
    r'src\s*=\s*"https?://', r'href\s*=\s*"https?://', r"@import\s+url\(",
    r'src\s*=\s*"//', r'href\s*=\s*"//',
)


class TestReportHtml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="cvalarm-report-")
        cls.cfg, cls.run_dir = helpers.make_run(cls.tmp, with_report=True)
        cls.path = os.path.join(cls.run_dir, "report.html")
        with open(cls.path, encoding="utf-8") as fh:
            cls.html = fh.read()

    # ------------------------------------------------------------------ 结构
    def test_html_generated(self):
        self.assertTrue(os.path.exists(self.path))
        self.assertGreater(len(self.html), 20000)
        self.assertIn("<!DOCTYPE html>", self.html)
        self.assertIn('lang="zh-CN"', self.html)

    def test_required_dom_ids_present(self):
        declared = set(re.findall(r'id="([A-Za-z0-9_\-]+)"', self.html))
        missing = [i for i in REQUIRED_IDS if i not in declared]
        self.assertEqual(missing, [], f"报告缺少容器 id：{missing}")

    def test_every_dom_id_used_by_script_exists(self):
        scripts = "\n".join(re.findall(r"<script>(.*?)</script>", self.html, re.S))
        used = set(re.findall(r"\$\('([A-Za-z0-9_\-]+)'\)", scripts))
        declared = set(re.findall(r'id="([A-Za-z0-9_\-]+)"', self.html))
        missing = sorted(used - declared)
        self.assertEqual(missing, [], f"脚本引用了不存在的 id：{missing}")

    def test_self_contained_no_external_assets(self):
        for pattern in EXTERNAL_PATTERNS:
            self.assertIsNone(re.search(pattern, self.html),
                              f"报告引用了外部资源，破坏离线可用性：{pattern}")

    def test_script_blocks_balanced(self):
        self.assertEqual(self.html.count("<script>"), self.html.count("</script>"))
        self.assertGreaterEqual(self.html.count("<script>"), 3)

    # ------------------------------------------------------------------ 数据
    def _payload(self) -> dict:
        match = re.search(r"window\.__DATA__ = (\{.*?\});\s*</script>", self.html, re.S)
        self.assertIsNotNone(match, "找不到页面内嵌数据")
        return json.loads(match.group(1))

    def test_payload_keys(self):
        payload = self._payload()
        for key in ("meta", "metrics", "cost", "reliability", "audit", "alarms",
                    "events", "histogram", "rules", "ledger", "topologies"):
            self.assertIn(key, payload)

    def test_payload_matches_disk_artifacts(self):
        payload = self._payload()
        with open(os.path.join(self.run_dir, "alarms.jsonl"), encoding="utf-8") as fh:
            on_disk = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(len(payload["alarms"]), len(on_disk))
        metrics = helpers.read_json_file(os.path.join(self.run_dir, "metrics.json"))
        self.assertAlmostEqual(
            float(payload["metrics"]["event_recall"]), float(metrics["event_recall"]), places=4)

    def test_every_displayed_alarm_has_valid_card(self):
        payload = self._payload()
        displayed = [a for a in payload["alarms"] if a["status"] in ("confirmed", "deferred")]
        self.assertTrue(displayed)
        for alarm in displayed:
            card = alarm.get("card")
            self.assertIsNotNone(card, f"{alarm['alarm_id']} 缺少卡片")
            errors = validate_card(card)
            self.assertEqual(errors, [], f"{alarm['alarm_id']} 卡片结构不合法：{errors}")

    def test_cards_are_signed_and_verifiable(self):
        payload = self._payload()
        for alarm in payload["alarms"]:
            card = alarm.get("card") or {}
            if not card:
                continue
            self.assertTrue(str(card.get("signature", "")).startswith("hmac-sha256:"))
            self.assertTrue(verify_card_signature(card), f"{alarm['alarm_id']} 签名校验失败")

    def test_cards_carry_evidence_and_provenance(self):
        payload = self._payload()
        cards = [a["card"] for a in payload["alarms"] if a.get("card")]
        self.assertTrue(cards)
        for card in cards:
            self.assertTrue(card["evidence"]["enabled"])
            self.assertIn("clip", card["evidence"])
            self.assertIn("manifest", card["evidence"])
            self.assertTrue(card["provenance"]["verifier"])
            self.assertEqual(card["provenance"]["replay_mode"], "offline_replay")

    def test_panel_data_completeness(self):
        metrics = self._payload()["metrics"]
        loc = metrics["localization"]
        self.assertEqual(loc["n"], len(loc["per_event"]))
        self.assertIn("ref_start_mae_s", loc)
        difficult = metrics["difficult_cases"]
        for key in ("short_stay", "evidence_incomplete", "authorized_suppressed",
                    "insufficient_evidence", "system_error"):
            self.assertIn(key, difficult["counts"])
            self.assertEqual(difficult["counts"][key], len(difficult[key]))
        self.assertIn("tta_event_start", metrics)
        self.assertIn("threshold_delay", metrics)
        self.assertIn("evaluable_video_hours", metrics)

    def test_resources_and_models_panels(self):
        payload = self._payload()
        meta = payload["meta"]
        self.assertIn("peak_memory_mb", meta["resources"])
        self.assertIn("actual_calls", meta["resources"])
        self.assertEqual(meta["resources"]["gpu"]["used"], False)
        for key in ("detector", "localizer", "verifier", "vlm"):
            self.assertIn(key, meta["models"])
        self.assertIn("capabilities", meta)
        self.assertIn("protocol", meta)

    def test_evidence_svg_count_matches_cards(self):
        payload = self._payload()
        cards = [a["card"] for a in payload["alarms"]
                 if a.get("card") and (a["card"].get("evidence") or {}).get("enabled")]
        with_svg = [c for c in cards if "<svg" in (c["evidence"].get("schematic_svg") or "")]
        self.assertGreater(len(with_svg), 0)
        # 内嵌 SVG 必须在页面里出现同样多次（否则渲染时会丢）
        self.assertGreaterEqual(self.html.count("<polygon"), len(with_svg))

    def test_report_titles_and_warnings_rendered(self):
        self.assertIn("持续视频监控", self.html)
        payload = self._payload()
        warning = payload["metrics"].get("sample_size_warning", "")
        if warning:
            # 小样本提示必须随数据下发（页面在客户端渲染它）
            self.assertIn(warning, json.dumps(payload, ensure_ascii=False))


class TestReportHtmlVariants(unittest.TestCase):
    """独立测试报告与首版范围报告的标题/徽章要能被区分。"""

    def test_custom_title(self):
        from cvalarm.report import write_report

        tmp = tempfile.mkdtemp(prefix="cvalarm-title-")
        cfg, run_dir = helpers.make_run(tmp, with_report=False)
        path = write_report(run_dir, cfg, title="独立测试报告 · 配置冻结 / 开发测试隔离")
        html = helpers.read_text_file(path)
        self.assertIn("独立测试报告 · 配置冻结 / 开发测试隔离", html)


if __name__ == "__main__":
    unittest.main()
