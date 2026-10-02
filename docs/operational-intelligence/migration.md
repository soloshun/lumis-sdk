# Reset compatibility and migration

The operational-intelligence APIs are additive and provisional. They do not replace released
types by reusing an import name with incompatible meaning.

| Existing surface | New direction | Transition |
| --- | --- | --- |
| `domain.IncidentInput` | `core.Incident` with entities/window | Explicit mapping with genuine timestamps/identity |
| `domain.EvidenceItem` | `core.Evidence` with query/target/key/value | Normalize observations; don't invent missing provenance |
| `domain.Hypothesis` | `core.Hypothesis` with predictions/falsifiers | Author testable checks; old free-text confidence is not enough |
| `application.DiagnosisService` | `runtime.InvestigationRuntime` | New composition; old deterministic classification remains available |
| `ports.ModelGateway` | `reasoning.sources.HypothesisModel` | Provider proposes candidates, no direct final diagnosis |
| `lumis diagnose` | `lumis investigate` | Different input/output contracts; no implicit migration |
| v1 Project/Rule documents | operational-v1alpha1 Project | Maintain separate files; validation rejects mixed meanings |
| Old cookbook directory | active `examples/gridcast-readonly` | Legacy examples kept for regression; no deletion of consumer references |

Existing proposal, high-risk approval, verification and confirmed-memory rules are retained.
The read-only runtime does not issue actions or promote investigation records to confirmed truth.
Plugins still follow their independent releases and declared compatibility ranges; new connectors
are not silently registered as legacy plugin factories.

No automatic converter can create valid falsifiers, topology or provenance from free text. An
operator must supply those semantics. Breaking removals need a documented migration decision and
evidence from consumers/paper regressions, not just a new folder layout.

Pre-reset branch: `legacy/pre-operational-intelligence-2026-10-02`, commit `8a371d1`.
The original checkout's local files remain untouched. New development branches from `dev`.
PyPI `0.1.0rc1` is immutable; this branch remains unreleased until a new candidate is qualified.
