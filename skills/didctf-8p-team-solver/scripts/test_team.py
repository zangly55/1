"""Offline eight-process integration tests; no API or real evidence access."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import run_deepseek as single
import run_deepseek_team as team
from test_runner import exited


@unittest.skipUnless(os.name == "nt", "Windows Job Object required")
class TeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dsh-eight-test-")
        self.root = Path(self.tmp.name)
        self.questions = [{"question_id": f"Q{i}", "question": f"offline {i}"} for i in range(8)]
        self.plan = {"members": [dict(id=mid, kind="solver", role="offline solver",
                                    owns=[f"Q{q}" for q in range(8) if q % 6 == i])
                                  for i, mid in enumerate(team.IDS[:6])] + [
                                      dict(id="P07", kind="wp", role="WP", owns=[]),
                                      dict(id="P08", kind="knowledge", role="KB", owns=[])]}
        for name, data in (("questions.json", self.questions), ("plan.json", self.plan)):
            (self.root / name).write_text(json.dumps(data), encoding="utf-8")
        (self.root / "prompt.txt").write_text("offline test only", encoding="utf-8")
        self.args = SimpleNamespace(workdir=self.root, output_dir=self.root / "out",
            questions_file=self.root / "questions.json", team_file=self.root / "plan.json",
            prompt_file=self.root / "prompt.txt", limit_seconds=15, deadline_utc=None,
            credentials=self.root / "unused", dsh=self.root / "unused.exe")
        self.key = "sk-offline-team-only"

    def tearDown(self):
        self.tmp.cleanup()

    def run_fake(self, seconds, output_tokens=1):
        code = ("import json,os,sys,time; sys.stdin.read(); "
                f"print(json.dumps({{'type':'status','usage':{{'outputTokens':{output_tokens}}}}}),flush=True); "
                "print(os.environ['DEEPSEEK_API_KEY'],flush=True); "
                f"time.sleep({seconds})")
        with patch.object(single, "get_key", return_value=(self.key, "offline")), \
             patch.object(single, "launch_command", return_value=([sys.executable, "-c", code], False)), \
             contextlib.redirect_stdout(io.StringIO()):
            return team.run_team(self.args)

    def test_eight_distinct_processes_and_recovery_keeps_deadline(self):
        self.assertEqual(self.run_fake(0.3), 0)
        state = team.read_json(self.args.output_dir / "team-state.json")
        self.assertTrue(state["eight_sessions_verified"])
        self.assertEqual(state["responding_count"], 8)
        deadline = state["deadline_utc"]
        for member in state["members"]:
            data = team.read_json(Path(member["state_file"]))
            self.assertEqual(data["deadline_utc"], deadline)
            self.assertTrue(data["tree_stop_confirmed"])
            self.assertTrue(exited(data["pid"]))
            self.assertNotIn(self.key, Path(data["stdout_log"]).read_text())
        self.assertEqual(self.run_fake(0), 0)
        after = team.read_json(self.args.output_dir / "team-state.json")
        self.assertEqual(after["deadline_utc"], deadline)
        self.assertEqual([m["pid"] for m in after["members"]], [m["pid"] for m in state["members"]])

    def test_deadline_stops_all_eight(self):
        self.args.limit_seconds = 4
        self.assertEqual(self.run_fake(60), 124)
        state = team.read_json(self.args.output_dir / "team-state.json")
        self.assertEqual(state["launched_count"], 8)
        for member in state["members"]:
            self.assertTrue(exited(member["pid"]))
            self.assertEqual(member["status"], "timed_out")
            self.assertFalse(member["cleanup_required"])

    def test_stop_request_cleans_all_members(self):
        self.args.output_dir.mkdir()
        (self.args.output_dir / "stop.request").touch()
        self.assertNotEqual(self.run_fake(60), 0)
        state = team.read_json(self.args.output_dir / "team-state.json")
        for member in state["members"]:
            self.assertTrue(exited(member["pid"]))
            self.assertFalse(member["cleanup_required"])

    def test_invalid_assignments_rejected_before_credentials(self):
        self.plan["members"][0]["reviews"] = ["Q0"]
        self.args.team_file.write_text(json.dumps(self.plan), encoding="utf-8")
        with patch.object(single, "get_key") as key:
            with self.assertRaises(ValueError):
                team.run_team(self.args)
            key.assert_not_called()
        with self.assertRaises(ValueError):
            team.validate_plan({"members": self.plan["members"][:7]}, self.questions)

    def test_eight_processes_without_model_output_are_not_verified(self):
        self.assertEqual(self.run_fake(0, output_tokens=0), 0)
        state = team.read_json(self.args.output_dir / "team-state.json")
        self.assertTrue(state["eight_distinct_processes"])
        self.assertFalse(state["eight_sessions_verified"])

    def test_single_question_still_assigns_all_eight_members(self):
        plan = {"members": [dict(id=mid, kind="solver", role=f"analysis angle {i}",
                                 owns=["Q0"] if i == 0 else [],
                                 support="Check distinct evidence sources" if i else "")
                               for i, mid in enumerate(team.IDS[:6])] + [
                                   dict(id="P07", kind="wp", role="WP"),
                                   dict(id="P08", kind="knowledge", role="KB")]}
        self.assertEqual(len(team.validate_plan(plan, self.questions[:1])), 8)

    def test_eight_solvers_or_writer_owning_question_are_rejected(self):
        self.plan["members"][6]["kind"] = "solver"
        with self.assertRaises(ValueError):
            team.validate_plan(self.plan, self.questions)
        self.plan["members"][6]["kind"] = "wp"
        self.plan["members"][7]["owns"] = ["Q0"]
        with self.assertRaises(ValueError):
            team.validate_plan(self.plan, self.questions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
