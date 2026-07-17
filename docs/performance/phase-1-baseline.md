# Phase 1 bounded performance baseline

This is a reproducible microbenchmark baseline for catching large regressions in the stable
Python foundation. It is not a throughput promise, capacity plan, production SLO, or comparison
with another product.

## Run it

From a clean checkout with the locked development environment:

```bash
uv sync --frozen --all-groups
uv run python scripts/run_phase1_benchmarks.py
```

The command emits schema-versioned JSON containing the SDK/Python/platform identity, clock,
workload sizes, sample count, calls per sample, median, and observed p95 nanoseconds per call.
Keep raw output with release-candidate evidence instead of treating one maintainer machine as a
universal threshold.

## Fixed workloads

| Workload | Bounded fixture | What is included |
|---|---:|---|
| Deterministic rules | 25 rules; final rule matches | sorting, matching, evidence and diagnosis models |
| Report round trip | one synthetic v1 report | model construction, JSON serialization, and validation |
| SQLite retrieval | one row by primary key | connection, schema check, query, and model validation |
| Plugin discovery | 25 static manifests | metadata enumeration, manifest validation, compatibility, sorting; no plugin imports |
| Replay evaluation | 1,000 synthetic cases | exact diagnosis, escalation, verification, and mismatch aggregation |

The fixtures use only synthetic SDK testkit data. The harness warms each operation twice, then
records independent samples with `time.perf_counter_ns`. SQLite uses a temporary local database.
Plugin discovery replaces entry-point enumeration with 25 deterministic in-memory distribution
manifests, so the count does not depend on whatever plugins happen to be installed.

## Comparing runs

Compare runs only when Python implementation/version, operating system, hardware/power mode,
SDK revision, sample count, and calls per sample are recorded. Run at least twice on an otherwise
idle host. Investigate sustained material changes, then profile before changing code. Do not fail
a release solely because a shared CI runner or laptop produced a slower single run.

A future dedicated benchmark runner may establish alert bands after enough history exists. Until
then, release review records observations and judgment; it does not manufacture precision.
