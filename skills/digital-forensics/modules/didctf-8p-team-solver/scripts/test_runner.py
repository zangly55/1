"""Offline tests: fake credentials and disposable subprocesses; no real cases/API."""
import contextlib
import ctypes
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import run_deepseek as runner


def exited(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        return True
    try:
        return kernel.WaitForSingleObject(handle, 0) == 0
    finally:
        kernel.CloseHandle(handle)


@unittest.skipUnless(os.name == "nt", "Windows subprocess-tree behavior")
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="dsh-runner-test-")
        self.output = Path(self.directory.name)
        self.key = "sk-unit-test-not-a-real-key"

    def tearDown(self):
        self.directory.cleanup()

    def state(self, seconds):
        now = runner.utcnow()
        return dict(started_utc=now.isoformat(),
                    deadline_utc=(now + runner.timedelta(seconds=seconds)).isoformat(),
                    attempt=1, status="starting")

    def test_normal_exit_stdin_redaction_and_parent_environment(self):
        before = os.environ.get("DEEPSEEK_API_KEY")
        environment = os.environ.copy()
        environment["DEEPSEEK_API_KEY"] = self.key
        program = "import os,sys; print(sys.stdin.read()); print(os.environ['DEEPSEEK_API_KEY'])"
        state = self.state(15)
        code = runner.execute([sys.executable, "-X", "utf8", "-c", program], environment,
                              "中文输入", self.output, self.output, state, self.key)
        log = Path(state["stdout_log"]).read_text(encoding="utf-8")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "completed")
        self.assertIn("中文输入", log)
        self.assertIn("[REDACTED]", log)
        self.assertNotIn(self.key, log)
        self.assertEqual(before, os.environ.get("DEEPSEEK_API_KEY"))

    def test_timeout_stops_descendant_and_preserves_checkpoint(self):
        program = (
            "import subprocess,sys,time; from pathlib import Path; "
            "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],"
            "creationflags=subprocess.CREATE_NO_WINDOW); "
            "Path('child.pid').write_text(str(p.pid)); "
            "Path('checkpoint.json').write_text('{\"Q1\":\"ready\"}'); "
            "print('checkpoint_saved',flush=True); time.sleep(60)"
        )
        state = self.state(3)
        started = time.monotonic()
        try:
            code = runner.execute([sys.executable, "-c", program], os.environ.copy(), "",
                                  self.output, self.output, state, self.key)
            child = int((self.output / "child.pid").read_text())
            self.assertEqual(code, 124)
            self.assertEqual(state["status"], "timed_out")
            self.assertTrue(state["tree_stop_confirmed"])
            self.assertFalse(state["cleanup_required"])
            self.assertTrue(exited(state["pid"]))
            self.assertTrue(exited(child))
            self.assertEqual(json.loads((self.output / "checkpoint.json").read_text()), {"Q1": "ready"})
            self.assertIn("checkpoint_saved", Path(state["stdout_log"]).read_text())
            self.assertLess(time.monotonic() - started, 12)
        finally:
            # Only PIDs recorded by these disposable test children.
            candidates = [state.get("pid")]
            child_file = self.output / "child.pid"
            if child_file.exists():
                candidates.append(int(child_file.read_text()))
            for pid in candidates:
                if pid and not exited(pid):
                    subprocess.run(["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_expired_retry_never_launches_and_keeps_deadline(self):
        prompt = self.output / "prompt.txt"
        prompt.write_text("offline only", encoding="utf-8")
        state = self.state(-1)
        state["status"] = "failed"
        runner.save_state(self.output / "state.json", state)
        argv = ["runner", "--prompt-file", str(prompt), "--workdir", str(self.output),
                "--output-dir", str(self.output)]
        with patch.object(sys, "argv", argv), patch.object(runner, "get_key") as get_key, \
             patch.object(runner, "launch_command", return_value=([sys.executable], False)), \
             patch.object(runner.subprocess, "Popen") as popen, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(), 124)
            popen.assert_not_called()
            get_key.assert_not_called()
        after = json.loads((self.output / "state.json").read_text())
        self.assertEqual(after["deadline_utc"], state["deadline_utc"])
        self.assertEqual(after["attempt"], 1)

    def test_output_lock_rejects_another_process_and_releases(self):
        program = (
            "import sys; from pathlib import Path; "
            "sys.path.insert(0,sys.argv[1]); import run_deepseek as r; "
            "\nwith r.output_lock(Path(sys.argv[2])): print('acquired')"
        )
        command = [sys.executable, "-B", "-X", "utf8", "-c", program,
                   str(Path(runner.__file__).parent), str(self.output)]
        with runner.output_lock(self.output):
            blocked = subprocess.run(command, capture_output=True, text=True, timeout=10,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Another launcher", blocked.stderr)
        released = subprocess.run(command, capture_output=True, text=True, timeout=10,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertIn("acquired", released.stdout)

    def test_third_attempt_is_rejected_before_loading_credentials(self):
        state = self.state(60)
        state.update(status="failed", attempt=2)
        runner.save_state(self.output / "state.json", state)
        argv = ["runner", "--prompt-file", str(self.output / "missing.txt"),
                "--workdir", str(self.output), "--output-dir", str(self.output)]
        with patch.object(sys, "argv", argv), patch.object(runner, "get_key") as get_key:
            with self.assertRaisesRegex(RuntimeError, "retry is already used"):
                runner.main()
            get_key.assert_not_called()
        self.assertEqual(json.loads((self.output / "state.json").read_text()), state)

    def test_normal_root_exit_also_stops_orphaned_tool(self):
        program = (
            "import subprocess,sys; from pathlib import Path; "
            "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],"
            "creationflags=subprocess.CREATE_NO_WINDOW); "
            "Path('orphan.pid').write_text(str(p.pid)); print('root_done',flush=True)"
        )
        state = self.state(15)
        try:
            code = runner.execute([sys.executable, "-c", program], os.environ.copy(), "",
                                  self.output, self.output, state, self.key)
            child = int((self.output / "orphan.pid").read_text())
            self.assertEqual(code, 0)
            self.assertEqual(state["status"], "completed")
            self.assertTrue(exited(child))
            self.assertTrue(state["tree_stop_confirmed"])
            self.assertFalse(state["log_incomplete"])
        finally:
            child_file = self.output / "orphan.pid"
            if child_file.exists():
                pid = int(child_file.read_text())
                if not exited(pid):
                    subprocess.run(["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_credentials_parser_fails_without_echoing_secret(self):
        credentials = self.output / "credentials.yaml"
        credentials.write_text('refs: ["' + self.key, encoding="utf-8")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            with self.assertRaises(RuntimeError) as raised:
                runner.get_key(credentials)
            self.assertNotIn(self.key, str(raised.exception))
            credentials.write_text('refs:\n  DEEPSEEK_API_KEY: "' + self.key + '"\n', encoding="utf-8")
            self.assertEqual(runner.get_key(credentials), (self.key, "saved_refs"))
            credentials.write_text('refs:\n  DEEPSEEK_API_KEY: record-id\n', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                runner.get_key(credentials)


if __name__ == "__main__":
    unittest.main(verbosity=2)
