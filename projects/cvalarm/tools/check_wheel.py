"""Exercise a built wheel in isolation, without the source tree on sys.path."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def check(wheel):
    with tempfile.TemporaryDirectory(prefix="cvalarm portable ") as tmp:
        root = Path(tmp)
        installed, work = root / "installed", root / "different working directory"
        work.mkdir()
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(installed)
        code = (
            "import sys; sys.path.insert(0," + repr(str(installed)) + ");"
            "from cvalarm.cli import main;"
            "raise SystemExit(main(['demo','--profile','v1','--hours','0.01',"
            "'--no-calibrate','--out','runs/smoke']))"
        )
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", "-c", code], cwd=work,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        meta = json.loads((work / "runs/smoke/run_meta.json").read_text(encoding="utf-8"))
        assert meta["frames"] > 0
        assert (work / "runs/smoke/report.html").is_file()
        assert not (installed / "state").exists()
        assert not (installed / "runs").exists()
        print("PASS: wheel resources, isolated import, different cwd, writable state and HTML report")


if __name__ == "__main__":
    check(Path(sys.argv[1]).resolve())
