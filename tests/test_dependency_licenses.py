"""Tests for release dependency-license policy checks."""

import json
import subprocess
import sys
from pathlib import Path


def test_lgpl_does_not_match_gpl_prefix(tmp_path: Path) -> None:
    """An allowed LGPL identifier is not confused with the denied GPL family."""
    result = _run_review(tmp_path, [{"Name": "psycopg", "License": "LGPL-3.0-only"}])

    assert result.returncode == 0


def test_denied_copyleft_families_are_reported(tmp_path: Path) -> None:
    """Denied SPDX variants are identified without relying on one exact suffix."""
    result = _run_review(
        tmp_path,
        [
            {"Name": "fixture-gpl", "License": "GPL-3.0-only"},
            {"Name": "fixture-agpl", "License": "AGPL-3.0-or-later"},
        ],
    )

    assert result.returncode != 0
    assert "fixture-gpl: GPL-3.0-only" in result.stderr
    assert "fixture-agpl: AGPL-3.0-or-later" in result.stderr


def _run_review(tmp_path: Path, payload: list[dict[str, str]]) -> subprocess.CompletedProcess[str]:
    report = tmp_path / "licenses.json"
    report.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "scripts/check_dependency_licenses.py", str(report)],
        check=False,
        capture_output=True,
        text=True,
    )
