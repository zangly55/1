"""命令行冒烟测试：每个子命令都真跑一次，校验退出码与产物。

原则：
  * 全部使用临时目录（`--state-dir` / `--out`），绝不污染工程的 `state/` 与 `runs/`；
  * 场景时长压到最小，保证整套 CLI 测试在几秒内跑完；
  * 只验证"命令能跑通、产物对得上、退出码符合预期"，指标细节由其它测试文件覆盖。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

import helpers

from cvalarm.cli import main as cli_main


def run_cli(*argv: str) -> tuple[int, str]:
    """进程内调用 CLI，返回 (退出码, 合并输出)。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = cli_main(list(argv))
    return code, buf.getvalue()


class CliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cvalarm-cli-")
        self.state = os.path.join(self.tmp, "state")
        self.out = os.path.join(self.tmp, "run")

    def cli(self, *argv: str) -> tuple[int, str]:
        return run_cli(*argv)


class TestSetupAndRun(CliCase):
    def test_init(self):
        code, out = self.cli("init", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("生效规则集", out)
        self.assertTrue(os.path.exists(os.path.join(self.state, "rules_active.json")))

    def test_demo_small(self):
        code, out = self.cli("demo", "--hours", "0.05", "--out", self.out,
                             "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        for name in ("report.html", "metrics.json", "cost.json", "run_meta.json",
                     "alarms.jsonl", "resources.json", "models.json",
                     "difficult_cases.json"):
            self.assertTrue(os.path.exists(os.path.join(self.out, name)), name)
        self.assertIn("产物目录", out)

    def test_demo_profile_v1(self):
        code, out = self.cli("demo", "--profile", "v1", "--hours", "0.4",
                             "--out", self.out, "--no-report", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        meta = helpers.read_json_file(os.path.join(self.out, "run_meta.json"))
        self.assertEqual(meta["capabilities"]["single_camera_pipeline"]["status"], "implemented")
        # v1 场景是单机位
        source = meta["source"]
        self.assertEqual(len(source["cameras"]), 1)

    def test_run_jsonl_replay(self):
        # 先导出一小段逐帧检测，再用 jsonl 数据源回放
        frames = os.path.join(self.tmp, "frames.jsonl")
        cams = os.path.join(self.tmp, "cameras.json")
        gt = os.path.join(self.tmp, "gt.jsonl")
        code, out = self.cli("export-frames", "--hours", "0.05", "--out", frames,
                             "--cameras-out", cams, "--gt-out", gt)
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.getsize(frames) > 0)
        code, out = self.cli("run", "--source", "jsonl", "--frames", frames,
                             "--cameras", cams, "--gt", gt, "--out", self.out,
                             "--no-calibrate", "--no-report", "--state-dir", self.state)
        self.assertEqual(code, 0, out)

    def test_metrics_and_cost(self):
        self.cli("demo", "--hours", "0.05", "--out", self.out, "--no-report",
                 "--state-dir", self.state)
        code, out = self.cli("metrics", "--run", self.out)
        self.assertEqual(code, 0, out)
        self.assertIn("event_recall", out)
        code, out = self.cli("cost", "--run", self.out)
        self.assertEqual(code, 0, out)
        self.assertIn("edge-only", out)
        self.assertIn("edge-cloud-api", out)

    def test_report_and_missing_run(self):
        self.cli("demo", "--hours", "0.05", "--out", self.out, "--no-report",
                 "--state-dir", self.state)
        code, out = self.cli("report", "--run", self.out)
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(os.path.join(self.out, "report.html")))
        code, out = self.cli("metrics", "--run", os.path.join(self.tmp, "nope"))
        self.assertEqual(code, 2)  # 缺产物要明确报错而不是崩栈


class TestProbeAndCalibration(CliCase):
    def test_probe(self):
        code, out = self.cli("probe", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("接口与数据就绪度探测", out)
        self.assertIn("vlm_endpoint", out)
        record = helpers.read_json_file(os.path.join(self.state, "model_probe.json"))
        self.assertIn("rows", record)
        self.assertFalse(record["ok"] is False)

    def test_calibrate_from_negatives(self):
        neg = os.path.join(self.tmp, "neg.json")
        with open(neg, "w", encoding="utf-8") as fh:
            json.dump([0.01, 0.02, 0.03, 0.05] * 10, fh)
        code, out = self.cli("calibrate", "--negatives-file", neg,
                             "--min-negatives", "20", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        cal = helpers.read_json_file(os.path.join(self.state, "calibration.json"))
        self.assertTrue(cal["is_ok"])
        self.assertLess(cal["tau_reject"], cal["tau_confirm"])


class TestTestReportWorkflow(CliCase):
    def _seed_calibration(self):
        neg = os.path.join(self.tmp, "neg.json")
        with open(neg, "w", encoding="utf-8") as fh:
            json.dump([0.01, 0.02, 0.03] * 20, fh)
        self.cli("calibrate", "--negatives-file", neg, "--min-negatives", "20",
                 "--state-dir", self.state)

    def test_holdout_report(self):
        code, out = self.cli("test-report", "--hours", "3",
                             "--out", self.out, "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("holdout", out)
        payload = helpers.read_json_file(os.path.join(self.out, "test_report.json"))
        self.assertEqual(payload["protocol"]["mode"], "holdout")
        self.assertTrue(payload["protocol"]["applied"])
        self.assertIn("questions", payload)
        self.assertTrue(os.path.exists(os.path.join(self.state, "test_freeze.json")))
        html = helpers.read_text_file(os.path.join(self.out, "report.html"))
        self.assertIn("独立测试报告", html)

    def test_refuses_without_calibration(self):
        code, out = self.cli("test-report", "--hours", "3", "--no-dev-calibrate",
                             "--out", self.out, "--state-dir", self.state)
        self.assertEqual(code, 2)
        self.assertIn("标定", out)


class TestRulesLifecycle(CliCase):
    def test_list_validate_bench_promote_rollback(self):
        self.cli("init", "--state-dir", self.state)
        code, out = self.cli("rules", "list", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("ACTIVE", out)

        code, out = self.cli("rules", "validate", "--path", "config/rules/rules_v1.json",
                             "--state-dir", self.state)
        self.assertEqual(code, 0, out)

        # 反例规则集必须被门禁拦住
        code, out = self.cli("bench", "--rules", "config/rules/rules_v3_overbroad.json",
                             "--hours", "0.4", "--state-dir", self.state)
        self.assertEqual(code, 1, out)
        self.assertIn("passed", out)

        # 候选规则集应通过并允许干跑
        code, out = self.cli("rules", "promote", "config/rules/rules_v2_candidate.json",
                             "--dry-run", "--hours", "0.4", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("干跑模式", out)

        # 真正发布后再回滚
        code, out = self.cli("rules", "promote", "config/rules/rules_v2_candidate.json",
                             "--hours", "0.4", "--reason", "冒烟测试", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        ledger = [json.loads(l) for l in
                  helpers.read_text_file(os.path.join(self.state, "rule_ledger.jsonl")).splitlines()
                  if l.strip()]
        hashes = [item["ruleset_hash"] for item in ledger if item["action"] == "bootstrap"]
        self.assertTrue(hashes)
        code, out = self.cli("rules", "rollback", hashes[0], "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("已原子回滚", out)

        code, out = self.cli("rules", "ledger", "--limit", "10", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("bootstrap", out)

    def test_stage_and_invalid_promote(self):
        self.cli("init", "--state-dir", self.state)
        code, out = self.cli("rules", "stage", "config/rules/rules_v2_candidate.json",
                             "--reason", "待审", "--state-dir", self.state)
        self.assertEqual(code, 0, out)
        self.assertIn("待审区", out)
        code, out = self.cli("rules", "rollback", "deadbeefdead", "--state-dir", self.state)
        self.assertEqual(code, 1)
        self.assertIn("回滚失败", out)


class TestFeedbackAndServe(CliCase):
    def test_feedback_flow(self):
        env = ("--state-dir", self.state)
        code, out = self.cli("feedback", "add", "--alarm-id", "A1", "--verdict", "confirm", *env)
        self.assertEqual(code, 0, out)
        code, out = self.cli("feedback", "add", "--alarm-id", "A2", "--verdict", "dismiss",
                             "--reason-code", "REFLECTION_OR_SHADOW", *env)
        self.assertEqual(code, 0, out)
        code, out = self.cli("feedback", "add", "--alarm-id", "A3", "--verdict", "dismiss", *env)
        self.assertEqual(code, 1)  # 驳回必须给理由
        code, out = self.cli("feedback", "summary", *env)
        self.assertEqual(code, 0, out)
        self.assertIn("选择偏差", out)
        code, out = self.cli("feedback", "reflect", *env)
        self.assertEqual(code, 0, out)
        self.assertIn("候选规则集", out)
        self.assertTrue(os.path.isdir(os.path.join(self.state, "rules_staged")))

    def test_serve_command_help_only(self):
        # 真正起服务由 test_server 覆盖；这里只确认命令入口存在且缺目录时报错
        code, out = self.cli("serve", "--run", os.path.join(self.tmp, "missing"))
        self.assertEqual(code, 2)
        self.assertIn("运行目录不存在", out)


class TestParserSurface(CliCase):
    def test_help_lists_all_commands(self):
        """子命令入口齐全（不执行 selftest，避免递归跑测试）。"""
        import argparse

        from cvalarm.cli import build_parser

        parser = build_parser()
        actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        self.assertTrue(actions)
        names = set(actions[0].choices)
        for expected in ("init", "demo", "run", "probe", "test-report", "calibrate",
                         "report", "serve", "metrics", "cost", "rules", "bench",
                         "feedback", "export-frames", "selftest"):
            self.assertIn(expected, names)

    def test_bad_option_returns_error(self):
        with self.assertRaises(SystemExit) as ctx:
            self.cli("demo", "--not-an-option")
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
