# SDK glossary

These names describe read-only observations and candidate explanations, not recovery authority.

| Public term | What it is | Small example |
|---|---|---|
| `Entity` | An operational identity with normalized metadata | `service:forecast` |
| `Relationship` | A directed observed/declared connection, not causal proof | features serves forecast |
| `GraphSnapshot` | Validated entities and relationships | An incident's service neighborhood |
| `Incident` | Affected entities, caller symptoms and an observation window | Investigate 12:00–12:10 UTC |
| `EvidenceQuery` | Operator-registered query, target and observable key | Query `retry-count` observes db/retries |
| `Evidence` | A typed observation with provenance and observation timestamp | retries = 8 from Prometheus |
| `Check` | A comparison used as a prediction or falsifier | retries greater than 5 |
| `Hypothesis` | A falsifiable candidate, never a confirmed cause | Retry pressure may explain slow requests |
| `IncidentContext` | The bounded incident, graph, query catalog and collected facts | Inputs shared with each source |
| `InvestigationBudget` | Hard scope, query, candidate, token and deadline limits | At most 8 evidence queries |
| `HypothesisAssessment` | Mechanical result of testing checks against facts | supported, ruled out, or can't tell |
| `TraceStep` | Lower-level source/query/stop audit event | Query timeout recorded without secrets |
| `Investigation` | Lower-level candidate/evaluation baseline result | Supported candidates or abstention |
| `DiagnosticRule` / rule | Operator-authored signature with a hypothesis and optional terminal scope | A known retry signature |
| `Finding` | A signature's match, no-match or unknown result | matched, did not match (ruled out), can't tell |
| `ToolReceipt` / receipt | Redacted inspection result, status, digests and visibility metadata | A truncated approved file read |
| `CandidateState` | Provisional mechanical state in a tool receipt | h2 ruled out by evidence e4 |
| `IncidentReport` / report | Context, findings, candidates, receipts and human-review result | `report.markdown()` or JSON |
| `Suggestion` | Tentative, cited review advice; patch text is never applied | Review batching after measurement |
| `HumanResolution` | Separate human attestation in append-only audit storage | Inconclusive; no change applied |
| `quality: observed` | Usable independently supplied observation, not proof of accuracy or completeness | Bounded complete query result |
| `quality: degraded` | Partial, capped, uncertain or synthetic-probe observation; cannot cleanly certify a check | Capped logs or sandbox output |

The JSON enum values remain stable: `supported` means the fetched usable observations satisfy
the predictions and falsifiers, **not confirmed causality**; `contradicted` reads as **ruled out**;
`unresolved` reads as **can't tell**. Python `assessment.display_state` and
`finding.display_status` provide those plain labels without changing serialization.

`insufficient_evidence` is an investigation conclusion: the agent could not establish a unique
supported explanation (including ambiguity or a stopped run). `requires_human_expert` is the
no-agent human route after inconclusive triage. Every report still requires human review,
including `supported_diagnosis`. Neither is permission to execute a fix.

An observation window is not measured onset/recovery. A proposed path is not validated as a
connected causal chain. See [incident investigation](incident-investigation.md) for those limits.
