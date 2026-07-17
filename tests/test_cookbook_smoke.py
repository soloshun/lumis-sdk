"""Offline smoke tests for adopter-facing cookbook entry points."""

import subprocess
import sys


def test_prometheus_alertmanager_walkthrough_runs_offline() -> None:
    """The provider mapping and deterministic diagnosis require no live service."""
    result = subprocess.run(
        [sys.executable, "cookbook/prometheus-alertmanager/demo.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "pipeline=orders-etl" in result.stdout
    assert "rule=orders-etl-failure-rate" in result.stdout
    assert "evidence=prometheus-orders-failure-rate" in result.stdout
