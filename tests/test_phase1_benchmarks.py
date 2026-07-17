"""Smoke tests for the reproducible Phase 1 benchmark harness."""

import json
import subprocess
import sys


def test_phase1_benchmark_harness_reports_every_required_workload() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_phase1_benchmarks.py",
            "--samples",
            "1",
            "--calls",
            "1",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert report["schema_version"] == 1
    assert {item["name"] for item in report["results"]} == {
        "deterministic_rule_match_25",
        "diagnosis_report_round_trip",
        "sqlite_incident_get",
        "plugin_discovery_25_manifests",
        "replay_evaluation_1000_cases",
    }
    assert all(item["median_ns_per_call"] > 0 for item in report["results"])
    assert report["note"] == "Microbenchmark observations are not production SLOs."
