"""Windows DeepSeek runner: child-only credentials, incremental logs, hard deadline.

Use Python 3.11+ and PyYAML, both bundled with GoldenEyesV4.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Deadline must include timezone")
    return parsed.astimezone(timezone.utc)


def save_state(path, state):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


@contextmanager
def output_lock(output):
    """An OS-owned lock survives stale files and releases on process death."""
    import msvcrt
    with (output / "runner.lock").open("a+b") as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("Another launcher owns this output directory") from None
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def get_key(credential_path):
    value = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if value:
        return value, "inherited_environment"
    try:
        import yaml
        document = yaml.safe_load(credential_path.read_text(encoding="utf-8-sig"))
        value = document.get("refs", {}).get("DEEPSEEK_API_KEY")
    except Exception:
        # Parser exceptions can quote the secret; never forward their text.
        raise RuntimeError("Cannot safely read saved credentials; check format or PyYAML") from None
    if not isinstance(value, str) or not re.fullmatch(r"sk-[A-Za-z0-9_-]+", value):
        raise RuntimeError("No direct API key under refs.DEEPSEEK_API_KEY; configure Models")
    return value, "saved_refs"


def launch_command(dsh):
    if not dsh.is_file():
        raise RuntimeError("DSH launcher does not exist")
    if dsh.suffix.lower() == ".cmd":
        # The exact Electron-as-Node launch in the verified dsh.cmd, without
        # cmd quoting or credentials in command arguments.
        root = dsh.parents[4]
        electron = root / "DeepSeek Harness.exe"
        asar = root / "resources" / "app.asar"
        cli = asar / "dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js"
        if not electron.is_file() or not asar.is_file():
            raise RuntimeError("Unknown DSH layout; inspect dsh.cmd before adapting")
        return [str(electron), "--expose-internals", str(cli), "headless", "--json", "-"], True
    if dsh.suffix.lower() == ".exe":
        return [str(dsh), "headless", "--json", "-"], False
    raise RuntimeError("Expected the verified dsh.cmd or a native dsh executable")


class ProcessJob:
    """Own descendants even after their parent exits; close-on-owner-death."""
    def __init__(self):
        class BasicLimits(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", wintypes.DWORD), ("min_working", ctypes.c_size_t),
                        ("max_working", ctypes.c_size_t), ("active_limit", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                        ("scheduling", wintypes.DWORD)]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("basic", BasicLimits), ("io", ctypes.c_uint64 * 6),
                        ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                        ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                        wintypes.DWORD, ctypes.c_void_p]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise RuntimeError("Cannot create process job")
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.kernel.CloseHandle(self.handle)
            self.handle = None
            raise RuntimeError("Cannot configure process job")

    def attach_and_resume(self, process):
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise RuntimeError("Cannot contain child process; refusing unbounded launch")
        # Popen closes the primary thread handle. NtResumeProcess resumes the
        # CREATE_SUSPENDED child only after assignment, eliminating spawn races.
        native = ctypes.WinDLL("ntdll")
        native.NtResumeProcess.argtypes = [wintypes.HANDLE]
        native.NtResumeProcess.restype = ctypes.c_long
        if native.NtResumeProcess(int(process._handle)) < 0:
            raise RuntimeError("Cannot resume contained child process")

    def close(self):
        if not self.handle:
            return True

        class Accounting(ctypes.Structure):
            _fields_ = [("times", ctypes.c_int64 * 4), ("page_faults", wintypes.DWORD),
                        ("total", wintypes.DWORD), ("active", wintypes.DWORD),
                        ("terminated", wintypes.DWORD)]

        confirmed = False
        try:
            self.kernel.TerminateJobObject(self.handle, 124)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                accounting = Accounting()
                ok = self.kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(accounting),
                                                          ctypes.sizeof(accounting), None)
                if ok and accounting.active == 0:
                    confirmed = True
                    break
                time.sleep(0.05)
        finally:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
        return confirmed


def execute(command, environment, prompt, cwd, output, state, key, stop_event=None):
    """Start watchdog before feeding stdin so hung input cannot extend time."""
    remaining = (timestamp(state["deadline_utc"]) - utcnow()).total_seconds()
    if remaining <= 0:
        state.update(status="timed_out", reason="deadline_already_passed")
        save_state(output / "state.json", state)
        return 124
    started = time.monotonic()
    job = ProcessJob()
    process = None
    try:
        process = subprocess.Popen(
            command, cwd=cwd, env=environment, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP | 0x4,
        )  # CREATE_SUSPENDED: child cannot spawn outside the job before assignment.
        state.update(pid=process.pid, attempt_started_utc=utcnow().isoformat())
        job.attach_and_resume(process)
    except BaseException:
        if process is not None:
            process.kill()
            process.wait(timeout=5)
        job.close()
        raise
    stream_errors = []

    def drain(stream, destination):
        try:
            with destination.open("w", encoding="utf-8", buffering=1) as log:
                for line in iter(stream.readline, b""):
                    log.write(line.decode("utf-8", errors="replace").replace(key, "[REDACTED]"))
        except Exception:
            stream_errors.append("log_write_failed")
        finally:
            stream.close()

    def feed():
        try:
            process.stdin.write(prompt.encode("utf-8"))
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    readers = []
    code = 2
    try:
        state.update(status="running")
        for name in ("stdout", "stderr"):
            path = output / f"attempt-{state['attempt']:02d}.{name}.jsonl"
            state[f"{name}_log"] = str(path)
            thread = threading.Thread(target=drain, args=(getattr(process, name), path), daemon=True)
            thread.start()
            readers.append(thread)
        save_state(output / "state.json", state)
        threading.Thread(target=feed, daemon=True).start()
        while True:
            if stop_event is not None and stop_event.is_set():
                raise KeyboardInterrupt
            budget = remaining - (time.monotonic() - started)
            if budget <= 0:
                raise subprocess.TimeoutExpired(command, remaining)
            try:
                code = process.wait(timeout=min(0.5, budget))
                break
            except subprocess.TimeoutExpired:
                continue
        state.update(status="completed" if code == 0 else "failed", exit_code=code)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        timed_out = isinstance(error, subprocess.TimeoutExpired)
        state.update(status="timed_out" if timed_out else "interrupted")
        code = 124 if timed_out else 130
    finally:
        # Also terminate orphaned tools after a normal root exit, before GPT takes over.
        stopped = job.close()
        state.update(cleanup_required=not stopped, tree_stop_confirmed=stopped)
        if stopped:
            process.wait(timeout=5)
        for reader in readers:
            reader.join(timeout=2)
        state.update(ended_utc=utcnow().isoformat(),
                     log_incomplete=bool(stream_errors) or any(t.is_alive() for t in readers))
        save_state(output / "state.json", state)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit-seconds", type=int, default=2700)
    parser.add_argument("--deadline-utc", help="Reuse original deadline on retry")
    parser.add_argument("--dsh", type=Path, default=Path(os.environ.get("LOCALAPPDATA", "")) /
                        "Programs/DeepSeek Harness/resources/runtime/cli/bin/dsh.cmd")
    parser.add_argument("--credentials", type=Path, default=Path(os.environ.get(
        "DSH_HOME", str(Path.home() / ".dsh"))) / ".credentials.yaml")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This launcher targets the verified Windows installation")
    if not 1 <= args.limit_seconds <= 2700:
        parser.error("--limit-seconds must be between 1 and 2700")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with output_lock(output):
        return run_locked(args, output)


def run_locked(args, output):
    state_path = output / "state.json"
    old = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if old.get("status") in ("starting", "running") or old.get("cleanup_required"):
        raise RuntimeError("Previous run may still be active; inspect its PID and start time before retrying")
    now = utcnow()
    deadlines = [now + timedelta(seconds=args.limit_seconds)]
    if args.deadline_utc:
        deadlines.append(timestamp(args.deadline_utc))
    if old.get("deadline_utc"):
        deadlines.append(timestamp(old["deadline_utc"]))
    if min(deadlines) <= now:
        old.update(deadline_utc=min(deadlines).isoformat(), status="timed_out",
                   reason="deadline_already_passed", ended_utc=now.isoformat())
        save_state(state_path, old)
        print(json.dumps({"status": old["status"], "state_file": str(state_path)}))
        return 124
    if old.get("attempt", 0) >= 2:
        raise RuntimeError("One recovery retry is already used; hand off to GPT")
    key, source = get_key(args.credentials)
    command, electron = launch_command(args.dsh.resolve())
    prompt = args.prompt_file.read_text(encoding="utf-8-sig")
    if key in prompt:
        raise RuntimeError("Prompt contains the API key; remove it before running")
    environment = os.environ.copy()
    environment["DEEPSEEK_API_KEY"] = key
    if electron:
        environment["ELECTRON_RUN_AS_NODE"] = "1"
    state = dict(started_utc=old.get("started_utc", now.isoformat()),
                 deadline_utc=min(deadlines).isoformat(), attempt=old.get("attempt", 0) + 1,
                 credential_source=source, status="starting")
    save_state(state_path, state)
    try:
        code = execute(command, environment, prompt, args.workdir.resolve(), output, state, key,
                       getattr(args, "stop_event", None))
    except Exception:
        state.update(status="failed", reason="launcher_error", cleanup_required=bool(state.get("pid")))
        save_state(state_path, state)
        raise RuntimeError("Launcher failed; inspect state.json and its PID without dumping environment") from None
    print(json.dumps({"status": state["status"], "state_file": str(state_path)}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
    except Exception:
        print("Launch setup failed; check input paths and configuration without printing secrets", file=sys.stderr)
        sys.exit(2)
