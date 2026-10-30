"""Copy the project, reproduce stable metrics, then reuse a relocated frozen state."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(project, cwd, *arguments):
    result = subprocess.run([sys.executable, str(project / "run.py"), *arguments], cwd=cwd,
                            env={**os.environ,"PYTHONIOENCODING":"utf-8"},
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def main():
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="cvalarm relocation ") as tmp:
        root = Path(tmp)
        first, second = root / "first copy", root / "第二份 copy"
        ignore = shutil.ignore_patterns(".git",".venv","venv","__pycache__","*.pyc","*.log",
                                        "*.egg-info","build","dist","runs","state","data")
        shutil.copytree(source, first, ignore=ignore)
        shutil.copytree(source, second, ignore=ignore)
        for project in (first,second):
            run(project, root, "demo","--profile","v1","--hours","2","--out","runs/demo")
        stable = ["events","event_recall","event_recall_incl_deferred",
                  "false_alarms_per_camera_hour","frame_roc_auc","triage_counts"]
        metrics = [json.loads((p/"runs/demo/metrics.json").read_text(encoding="utf-8")) for p in (first,second)]
        assert {k:metrics[0][k] for k in stable} == {k:metrics[1][k] for k in stable}
        run(first,root,"test-report","--no-report","--out","runs/test","--state-dir","state/holdout")
        shutil.copytree(first/"state/holdout",second/"state/holdout")
        run(second,root,"test-report","--no-report","--out","runs/test","--state-dir","state/holdout")
        print("PASS: two relocated source trees, Unicode/space paths, different cwd, matching metrics, reused frozen state")


if __name__ == "__main__":
    main()
