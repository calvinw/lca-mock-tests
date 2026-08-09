"""Rebuild and verify every hand-computable case study.

Each case is copied to a temporary directory so UUID-generating builds cannot
rewrite the checked-in JSON-LD. The actual check runs in its own process because
bw2data reads BRIGHTWAY2_DIR only once per process; this preserves isolation
between case studies while reusing the production check script and its precise
expected-value comparisons.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CASE_STUDIES_DIR = ROOT / "case_studies"


def discover_case_studies() -> list[str]:
    return sorted(
        path.name
        for path in CASE_STUDIES_DIR.iterdir()
        if path.is_dir()
        and (path / "build.py").exists()
        and (path / "expected.json").exists()
    )


@pytest.mark.parametrize("case_name", discover_case_studies())
def test_case_study(case_name, tmp_path):
    case_dir = tmp_path / "case_studies" / case_name
    scripts_dir = tmp_path / "scripts"
    shutil.copytree(CASE_STUDIES_DIR / case_name, case_dir)
    shutil.copytree(ROOT / "scripts", scripts_dir)

    commands = [
        ("build", [sys.executable, str(case_dir / "build.py")]),
        (
            "release",
            [sys.executable, str(scripts_dir / "make_release.py"), str(case_dir)],
        ),
        (
            "check",
            [
                sys.executable,
                str(scripts_dir / "check_case_study.py"),
                str(case_dir),
            ],
        ),
    ]

    for stage, command in commands:
        result = subprocess.run(
            command,
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(
                f"{case_name}: {stage} failed (exit {result.returncode})\n"
                f"--- stdout ---\n{result.stdout}\n"
                f"--- stderr ---\n{result.stderr}",
                pytrace=False,
            )
