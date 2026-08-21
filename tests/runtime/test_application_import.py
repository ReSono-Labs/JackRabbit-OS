from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_application_imports_in_a_fresh_python_process() -> None:
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "runtime")
    result = subprocess.run(
        [sys.executable, "-c", "import resono_runtime.application"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
