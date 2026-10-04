# Lessons from the GridCast integration

**Date:** 2026-10-03. **SDK under test:** `dev` at c757a74.
**Estate:** the GridCast reference estate in `lumis-cookbooks/gridcast`: ten services on
kind, Prometheus, Loki, Tempo, Prefect and PostgreSQL, with ten injected failure scenarios
(A–J).

**What was run:**
- deterministic triage only;
- triage followed by the reference agent;
- a single-pass model baseline.

The models were DeepSeek v4 (flash and pro) through OpenRouter, with reasoning enabled.

This note records what the integration taught us and what changed in the SDK because of it.
Each change below came from something observed on the live estate, not from a hypothetical.

## Fixes and features that came out of it

| # | Observed on GridCast | Root cause in the SDK | Change | Commit |
|---|---|---|---|---|
| 1 | Agent reported a metric "could not be confirmed": its value showed as `[REDACTED_PHONE]` | PII patterns matched decimals, epochs, ISO dates and IPv4 | Phone redaction needs a phone shape; card candidates cannot be inside a decimal | 20ab503 |
| 2 | Two drills lost all 14 Prometheus facts | Prometheus echoes the evaluation time rounded to ms, which can land after a µs `ended_at` | `observed_at = min(echo, ended_at)` | 1f9c069 |
| 3 | Completed `db-migrate` / `model-train` Job pods appeared as services | No pod-phase filter | `Succeeded` pods skipped; failed pods kept | 1f9c069 |
| 4 | Single-pass baseline lost valid candidates; 2 of 4 runs failed with a byte-budget error | Whole batch rejected for one bad candidate; 100 KB response cap too small for reasoning models | Per-candidate validation with traced reasons, `last_response`, `max_response_bytes` (1 MB) | 8394ae4 |
| 5 | Agent could not run on DeepSeek at all (HTTP 404) | `parallel_tool_calls` + OpenRouter `require_parameters` filtered out every endpoint | Parameter no longer sent (tools are sequential anyway) | 8009c9a |
| 6 | One empty tool argument ended an investigation | `retries=0` | `validation_retries` (default 2) | 8009c9a |
| 7 | Correct diagnoses thrown away twice on scenario A | All-or-nothing output: a revised hypothesis reusing its ID, or a receipt in `evidence_needed`, discarded everything | Output validator returns problems to the model; the handler accepts per candidate | 8009c9a |
| 8 | Budget exhaustion reported as "rejected or unavailable" | Exceptions not distinguished | `agent_budget_exhausted`, `agent_output_invalid`; registered candidates still assessed | 8009c9a |
| 9 | Agent walked `git.diff` commit by commit (about 25k tokens each) to find a release | `git.log` returned IDs and timestamps only | Opt-in `include_commit_subjects` | a0042a1 |
| 10 | Model-registry fact (scenario E) had to be queried by the cookbook and passed in as a snapshot | No SQL provider | `sources.sql` / `provider: sql`, read-only transaction | c54500e |
| 11 | Agent's correct answer on F was scored wrong; it put a GitOps file, then a Deployment, at the head of its causal path | The graph has no notion of "this entity changed recently" | Typed change records (below) | d777046 |
| 12 | Scenario E: two supported candidates with different root causes (pipeline-internal SQL; the model change) were reported as one `supported_diagnosis` | Conclusion only required every viable candidate to be supported; supported candidates are not ranked | Competing supported roots give `insufficient_evidence` with the roots listed; the agent returns causes only (exclusions go to unresolved questions) | this change |
| 13 | Validation drill K: ingestion error entries read only "ingestion batch failed"; the cause (`ReadTimeout`) was in the log's structured metadata | The Loki connector deliberately dropped all structured metadata | An operator allowlist (`fields`) exports named fields only, bounded and redacted | this change |

Also added in these commits: `models.reasoning`, `PydanticInvestigator.messages` (the run
transcript, for evaluation) and suppression of pydantic-ai's first-run banner.

## Change records

### What happened

In scenario F, feature-service release 1.7.0 introduced an N+1 query pattern. A decoy
planning-api release landed 45 seconds earlier. On run 2 the agent:

1. Found the release with `git.log` / `git.diff` and wanted to say "the cause is that change".
2. Returned `causal_path: ["gitops:kustomization.yaml", "service:gridcast:feature-service", ...]`,
   which Lumis rejected because a file is not a graph node.
3. Replaced it with the nearest graph node, `k8s:gridcast:deployment:feature-service`.
4. Kept the change details (commit, versions, the N+1 pattern) only in free-text `statement`.

The diagnosis was right, but the change itself was **not checkable**: Lumis verified the
symptoms (SQL per build, build p95, rows scanned) and could not verify "a release happened
here". The path also no longer started at the logical service.

### Options considered

**A. Changes as evidence about entities (implemented).** The graph stays the estate's current
structure. A change is a time-bounded fact about an entity:

```text
Evidence(entity_id="service:gridcast:feature-service", key="release_changes_30m", value=1,
         observed_at=<incident end>, source="changes")
```

A hypothesis then predicts it like any other observable, and the causal path stays in graph IDs:

```yaml
causal_path: ['service:gridcast:feature-service', 'service:gridcast:postgres', 'service:gridcast:forecast-pipeline']
predictions:
  - {entity_id: 'service:gridcast:feature-service', key: release_changes_30m, operator: gt, value: 0}
  - {entity_id: 'service:gridcast:feature-service', key: sql_statements_per_build, operator: gt, value: 100}
falsifiers:
  - {entity_id: 'service:gridcast:feature-service', key: release_changes_30m, operator: eq, value: 0}
```

The agent sees the same records through `inspect(changes)`. This fits the existing design:
- the graph is structure and evidence is time-bounded;
- `assess()` already handles counts, so nothing new is needed in the reasoning core;
- a zero count is a real observation, so a "bad release" hypothesis can be **contradicted**,
  which makes this a strong falsifier for triage.

**B. Changes as graph nodes (future consideration).** For example
`change:gitops:8514f199 --changed--> k8s:...:deployment:feature-service`, with a timestamp. A
causal path could then start at the commit itself. This was not done now because it breaks the
graph's "current structure" contract:
- the graph would need time, expiry and per-incident filtering;
- it would grow with every commit;
- prepared-graph caching and scope budgets would have to account for it;
- it adds no checking power that A lacks.

B becomes worth building when one of these is needed:
- **Display.** An incident or graph viewer that draws the change next to the nodes it touched.
  It can be built from change records at render time, without storing changes in the graph.
- **Blast radius.** Questions like "what does this change touch?" for one change that
  configures many entities (a shared ConfigMap, a base image, a feature flag), where the change
  is the natural pivot.
- **Change-centric memory.** Correlating the same change, or the same kind of change, across many
  incidents ("every incident after a pool-size change"), where a change needs a stable identity
  and relationships.
- **Causal paths that start at a change.** Scoring or reporting that requires the path to begin
  at the change rather than the entity, as in research comparisons with change-aware baselines.

If B is built, change nodes should be a **separate, time-indexed layer** joined to the
structural graph at query or render time, not merged into `GraphSnapshot`.

### What we learned building A

* **Shared files hide attribution.** GridCast keeps every image tag in one `kustomization.yaml`,
  so path mapping blamed every service for every release, including the F decoy. Conventional-
  commit scopes (`deploy(feature-service): 1.6.0 -> 1.7.0`) fix this. A future option is
  reading Argo CD / Flux / image-automation records that already name the image.
* **Kubernetes does not durably record re-activations.** Re-applying a previous release re-uses
  the old ReplicaSet. Its creation time is old and its managed-field times are overwritten by
  later scaling, so only a `ScalingReplicaSet` event (kept about an hour by default) says when it
  became active. The Git source is the durable record; Kubernetes confirms the change reached
  the cluster.
* **Changes need their own lookback.** An incident window starts shortly before the first alert,
  but the change that caused it can be older. Queries count back from the incident end over
  their own `lookback_seconds`.

## Practices for integrators (confirmed on GridCast)

* **One identity convention everywhere.** Kubernetes `app.kubernetes.io/name` = OTel
  `service.name` = alert `entity` label = Lumis ID `service:<namespace>:<name>`. Use aliases
  only for explicit exceptions (Tempo named the database after `db.name`).
* **One fact per query, and never turn "not observed" into zero.** `or vector(0)` is safe only
  when the series is guaranteed to exist whenever its subject exists (application counters
  pre-initialised at start-up). It is unsafe for infrastructure metrics of short-lived subjects.
  In scenario D, cAdvisor never scraped the crash-looping container, so
  `container_oom_events_total ... or vector(0)` reported 0 OOM kills. That false zero contradicted
  the correct OOM signature and made the agent's "not OOM" mechanism look supported. The proof
  is only as good as the telemetry.
* **Decide important mechanisms from two independent sources.** For OOM, use the container's
  termination reason (kube-state-metrics `kube_pod_container_status_last_terminated_reason` or
  pod status) plus working set vs. limit, so one blind source cannot falsify a signature alone.
* **Loki counts can support but never falsify.** Zero matches produce no fact. Pair every
  log-based prediction with a Prometheus or change falsifier, or a healthy estate leaves the
  signature `unknown`.
* **Terminal signatures need two or more independent observables** and must cover every
  affected entity. GridCast's scale-to-zero signature concludes in about 60 ms with no model;
  everything else escalates.
* **Let alerts settle (60–120 s) before opening an incident.** Slower evidence and related
  alerts then arrive first.
