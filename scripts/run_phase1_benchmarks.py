#!/usr/bin/env python3
"""Run bounded, dependency-free Phase 1 microbenchmarks."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import lumis_sdk.adapters.plugins.importlib_catalog as plugin_catalog_module
from lumis_sdk import __version__
from lumis_sdk.adapters.deterministic import diagnose_text
from lumis_sdk.adapters.plugins import ImportlibPluginCatalog
from lumis_sdk.adapters.reports import parse_json_report, render_json_report
from lumis_sdk.adapters.sqlite import SQLiteIncidentStore
from lumis_sdk.config import DeterministicRule
from lumis_sdk.evaluation import ReplayCase, evaluate_replay
from lumis_sdk.testkit import make_test_incident, make_test_plugin_manifest


@dataclass(frozen=True)
class BenchmarkResult:
    """Machine-readable timings for one fixed workload."""

    name: str
    samples: int
    calls_per_sample: int
    workload_units_per_call: int
    median_ns_per_call: int
    p95_ns_per_call: int


class _FakeDistribution:
    def __init__(self, name: str, manifest: str) -> None:
        self.metadata = {"Name": name}
        self.version = "1.0.0"
        self.files: None = None
        self._manifest = manifest

    def read_text(self, filename: str) -> str | None:
        return self._manifest if filename == "lumis-plugin.json" else None


class _FakeEntryPoint:
    def __init__(self, name: str, distribution: _FakeDistribution) -> None:
        self.name = name
        self.dist = distribution


class _FakeEntryPoints(list[_FakeEntryPoint]):
    def select(self, *, group: str) -> _FakeEntryPoints:
        return self if group == "lumis_sdk.plugins" else _FakeEntryPoints()


def _measure(
    name: str,
    operation: Callable[[], object],
    *,
    samples: int,
    calls: int,
    workload_units: int = 1,
) -> BenchmarkResult:
    for _ in range(2):
        operation()
    durations: list[int] = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        for _ in range(calls):
            operation()
        durations.append((time.perf_counter_ns() - started) // calls)
    ordered = sorted(durations)
    p95_index = min(len(ordered) - 1, max(0, round(0.95 * len(ordered) + 0.5) - 1))
    return BenchmarkResult(
        name=name,
        samples=samples,
        calls_per_sample=calls,
        workload_units_per_call=workload_units,
        median_ns_per_call=round(statistics.median(durations)),
        p95_ns_per_call=ordered[p95_index],
    )


def _rules() -> list[DeterministicRule]:
    rules = [
        DeterministicRule(
            id=f"non-match-{index}",
            name=f"non-match-{index}",
            all_contains=[f"ABSENT_{index}"],
            classification="not_selected",
            severity="low",
            summary="Synthetic non-matching rule.",
            root_cause_hypothesis="Synthetic non-match.",
            confidence=0.1,
            priority=100 - index,
        )
        for index in range(24)
    ]
    rules.append(
        DeterministicRule(
            id="match",
            name="match",
            all_contains=["TESTKIT_SIGNATURE"],
            classification="fixture_failure",
            severity="medium",
            summary="Synthetic matching rule.",
            root_cause_hypothesis="Synthetic match.",
            confidence=0.8,
            priority=1,
        )
    )
    return rules


def _plugins(count: int = 25) -> _FakeEntryPoints:
    items = _FakeEntryPoints()
    for index in range(count):
        entry_point = f"fixture-{index:02d}"
        name = f"fixture-plugin-{index:02d}"
        manifest = make_test_plugin_manifest(name=name, entry_point=entry_point)
        distribution = _FakeDistribution(f"{name}-package", manifest.model_dump_json(by_alias=True))
        items.append(_FakeEntryPoint(entry_point, distribution))
    return items


def _replay_cases(count: int = 1_000) -> list[ReplayCase]:
    return [
        ReplayCase(
            id=f"case-{index:04d}",
            expected_diagnosis="fixture_failure",
            observed_diagnosis="fixture_failure" if index % 10 else "unknown",
            expected_escalation=False,
            observed_escalation=False,
            expected_verification="passed",
            observed_verification="passed",
        )
        for index in range(count)
    ]


def run_benchmarks(*, samples: int, calls: int) -> dict[str, Any]:
    """Run all fixed workloads and return a JSON-serializable report."""
    rules = _rules()
    incident = make_test_incident()
    diagnosis = diagnose_text("ERROR TESTKIT_SIGNATURE", rules)
    report = render_json_report(incident, diagnosis)
    replay_cases = _replay_cases()
    fake_plugins = _plugins()

    original_entry_points = plugin_catalog_module.metadata.entry_points
    with tempfile.TemporaryDirectory(prefix="lumis-benchmark-") as directory:
        store = SQLiteIncidentStore(Path(directory) / "incidents.db")
        stored = store.save(incident, diagnosis, "# Synthetic report\n", Path("report.md"))
        try:
            plugin_catalog_module.metadata.entry_points = lambda: fake_plugins
            results = [
                _measure(
                    "deterministic_rule_match_25",
                    lambda: diagnose_text("ERROR TESTKIT_SIGNATURE", rules),
                    samples=samples,
                    calls=calls,
                    workload_units=25,
                ),
                _measure(
                    "diagnosis_report_round_trip",
                    lambda: parse_json_report(render_json_report(incident, diagnosis)),
                    samples=samples,
                    calls=calls,
                ),
                _measure(
                    "sqlite_incident_get",
                    lambda: store.get(stored.id),
                    samples=samples,
                    calls=calls,
                ),
                _measure(
                    "plugin_discovery_25_manifests",
                    ImportlibPluginCatalog().discover,
                    samples=samples,
                    calls=calls,
                    workload_units=25,
                ),
                _measure(
                    "replay_evaluation_1000_cases",
                    lambda: evaluate_replay(replay_cases),
                    samples=samples,
                    calls=max(1, calls // 10),
                    workload_units=1_000,
                ),
            ]
        finally:
            plugin_catalog_module.metadata.entry_points = original_entry_points

    return {
        "schema_version": 1,
        "sdk_version": __version__,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "clock": "time.perf_counter_ns",
        "results": [asdict(result) for result in results],
        "note": "Microbenchmark observations are not production SLOs.",
        "fixture_check": {"report_bytes": len(report.encode("utf-8"))},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=9)
    parser.add_argument("--calls", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="Emit compact JSON")
    args = parser.parse_args(argv)
    if args.samples < 1 or args.calls < 1:
        parser.error("--samples and --calls must be positive")
    report = run_benchmarks(samples=args.samples, calls=args.calls)
    print(json.dumps(report, indent=None if args.json else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
