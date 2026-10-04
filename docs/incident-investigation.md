# Incident investigation: public proof of concept

This development interface is experimental. It demonstrates evidence-backed investigation,
not autonomous recovery or validated production root-cause accuracy.

## Flow and authority

Incident → prepared operational graph → registered observations → deterministic findings →
sufficient terminal signature or one bounded investigator → mechanical assessments →
human-review report → optional audit storage → separately recorded human resolution.

The public investigator uses Pydantic AI, not LangGraph or a multi-agent scheduler. It has two
tool families, inspect and probe. Applications can replace it through the Investigator
protocol without changing evidence validation. The default configured provider is OpenRouter;
native OpenAI, Anthropic and Gemini are also available. No model runs unless explicitly enabled
or injected by the caller.

### Deterministic triage

The checks field holds diagnostic signatures expressed as hypotheses with predictions and
falsifiers. Each finding is match, no_match or unknown. Missing, conflicting, failed or degraded
observations never become a clean match. A failed tool call is not a false measurement.

A signature may end triage only when:

1. The operator explicitly sets terminal: true and declares explains_entities.
2. It predicts at least two distinct entity/key observables with independently supplied evidence.
3. Its predictions are supported and no falsifier matches.
4. It covers every affected entity, and all other in-scope signatures are contradicted.
5. Any caller-owned TriageGuard.allows(rule, context) also accepts.

Two observables are a conservative minimum, **not statistical independence or causal proof**.
Operators must choose appropriate evidence and may add a stricter guard. For example, an
observed OOM termination can be nonterminal: it explains the termination but does not establish
whether a leak, workload spike or memory limit caused it.

Nonterminal matches, unknown findings and competing matches go to the investigator when
enabled, otherwise to a human. Findings and collected evidence accompany escalation.
Terminal triage does not instantiate a provider, read code or run a sandbox.

### Tools and investigation

The agent discovers available operations with inspect(operation="catalog").
Only these operations are supported:

| Operation | Authority |
| --- | --- |
| catalog | Scoped query IDs/descriptions, approved files and enabled capabilities |
| graph | One-hop neighborhood within the already scoped incident graph |
| evidence | Operator-registered query ID; never model-authored PromQL |
| code.read, code.search | Read/literal-search an explicit text-file allowlist |
| git.log, git.diff | Fixed local read-only commands; full SHA diff, approved paths only |
| changes | Recent commits/rollouts touching scoped entities (`sources.changes`), newest first |
| hypothesis.register | Validate and bind a falsifiable candidate before probing |
| probe | Generated Python experiment in an explicitly enabled, resource-limited container |

Files are snapshotted once per repository per investigation, redacted and hashed. Absolute
file paths, traversal, symlinks, special files, binary/oversized files, secret/dot directories
and unapproved extensions are refused. Repository roots are explicitly operator-controlled.
Consumer modules are never imported. Git log returns commit IDs/timestamps; with the
repository's `include_commit_subjects: true` it also returns each commit's subject line, redacted
and truncated to 200 characters (untrusted text, like every tool result). Diffs disable external
diff/textconv and hooks. For "what changed, where and when" use typed change records instead:
`inspect(changes)` lists recent commits and rollouts already attributed to graph entities, and a
registered `provider: changes` query turns them into checkable facts (see
[recent changes](telemetry-connectors.md#recent-changes)). A change is evidence about an entity,
never a causal-path node: write the path in graph IDs and predict the change, for example
`release_changes_30m gt 0` on the service.

The model returns AgentOutput: candidates, tentative suggestions/patch text and unresolved
questions. It cannot author evidence, assessment state, confidence-as-authority or confirmed
causes. Generated patches are text only: never applied to the repository or an operational system.

Acceptance is per candidate. Before the run ends, the reference agent checks its final answer
against the same rules the handler applies (graph IDs, registered query IDs, a new ID for a revised
hypothesis, known evidence/receipt references) and returns any problem to the model to repair, up
to `validation_retries` times; malformed tool arguments are retried the same way, and every attempt
still counts toward the budgets. The handler then validates again: an invalid candidate, and any
suggestion that depends on it or cites unknown evidence/receipts, is dropped and the reason is
listed in `unresolved_questions`; valid candidates and suggestions are kept.

Stop reasons distinguish `agent_completed`, `agent_budget_exhausted` (request/tool/token limits
reached), `agent_output_invalid` (retries exhausted), `deadline_exceeded` and
`investigator_rejected_or_unavailable` (provider or other failure). Without a final answer there
are no suggestions, but candidates registered during the run and all collected evidence remain
and are assessed. The reference agent sends no `parallel_tool_calls` setting (tools run
sequentially), so OpenRouter's `require_parameters` routing also matches endpoints that do not
advertise it. `PydanticInvestigator.messages` holds the last run's provider messages in memory
for audit/evaluation by the caller; it is never written to the report.

## Python API

    from pathlib import Path
    from lumis_sdk.core import Incident
    from lumis_sdk.runtime import YamlProject, IncidentStore

    project = YamlProject.from_file("lumis.yaml")
    event = Incident.model_validate_json(Path("incident.json").read_text())
    report = await project.handle_incident(event)  # no model credentials needed
    # Explicit paid-model opt-in, only after inconclusive triage:
    # report = await project.handle_incident(event, use_agent=True)
    store = IncidentStore(Path("audit/incidents.sqlite"))
    store.save(report)
    assert report.requires_human_review
    assert report.truth_state == "unconfirmed_hypothesis"

Set observations_file in YAML or pass observations=tuple_of_Evidence. Sources use the same
discovery/binding path as graph inspection. Reuse prepared = await project.prepare(at=event.ended_at)
and await prepared.handle_incident(...) when appropriate. Preparation and investigation have
separate deadlines.

Optional injected arguments are investigator, guard, runner and the caller-owned Prometheus
client. These are **trusted application extension ports**, not tools the model can reconfigure.
Custom connectors must supply independent observations. Never wrap host Python execution as
a "sandbox runner"; production runner implementations require their own threat-model review.

YamlProject.investigate(...) and lumis investigate remain the lower-level reference
candidate/evaluation baseline. Their use_model / --use-model option is a single-completion
candidate source, not this tool-using agent.

## YAML additions

The existing project, topology, source, query and incident contracts remain. Add:

    observations_file: observations.json
    models:
      provider: openrouter
      model: your-provider/your-tool-capable-model
    checks:
      - id: service-health
        terminal: false
        hypothesis:
          id: unavailable
          statement: Service unavailability may explain the failure.
          causal_path: [service:demo]
          evidence_needed: [health]
          predictions:
            - {entity_id: "service:demo", key: healthy, operator: eq, value: false}
          falsifiers:
            - {entity_id: "service:demo", key: healthy, operator: eq, value: true}
    investigator:
      budget:
        request_limit: 8
        tool_calls_limit: 10
        max_probes: 2
        output_tokens_limit: 12000
        max_tool_characters: 8000
        max_total_tool_characters: 32000
        validation_retries: 2
      repositories:
        - id: application
          root: ./approved-source
          entity_ids: [service:demo]
          files: [src/handler.py, pyproject.toml]
          include_commit_subjects: false
      sandbox:
        enabled: false

Mapped entities and queries must exist in the prepared graph/catalog. A repository is usable
only when all its mapped entities belong to the incident scope. rule_hypotheses is the baseline
candidate-source configuration, not the new triage gate; put incident-handling signatures in checks.

To enable probes, approve/preload a digest-pinned Python image, enable sandbox, and register
a query with provider: probe, target entity/key and description. A candidate must request that
query. Probes cannot be triage evidence. See the [sandbox procedure](sandbox.md).

The existing budget limits graph/context/query/candidate sizes and query/source/total deadlines.
Triage and agent share the evidence-query budget. Repeated queries use cached evidence; failed
observations are not silently retried. All tool attempts, including denied calls, consume the
broker budget. Each run has independent state.

## Reports and human resolution

IncidentReport contains context, triage findings, mechanically evaluated candidates, redacted
tool receipts, tentative suggestions, unresolved questions, route, stop reason and
request/token/tool/query/probe counts. It does not store raw chain-of-thought or the full provider
conversation (callers that need it for evaluation read `PydanticInvestigator.messages`). No global tracing is enabled by Lumis. OpenAI response storage is explicitly
disabled; this does not override provider retention policies.

supported_diagnosis means checks support a candidate, not confirmed causality. It also requires
the supported candidates to agree on one root cause (a resource node that `hosts` a service
counts as that service): Lumis does not rank supported candidates, so competing supported
causes yield insufficient_evidence, with the competing roots listed in unresolved questions. Missing usable
evidence normally yields insufficient_evidence or requires_human_expert. Provider failures,
malformed output and deadline exhaustion preserve collected facts/receipts. Native SDK
transport retries are disabled; aggregate requests/output tokens are bounded. Native SDKs
manage provider response buffers, not a custom byte-limited transport; qualify resource/privacy
behavior before deployment.

IncidentStore.save(report) atomically saves immutable incident/evidence/receipt rows in SQLite.
Reusing an incident ID fails rather than overwriting it. Use a new incident ID for another run.
Applications can implement IncidentRecorder for their own database.

HumanResolution fields: id, incident_id, reviewer, timezone-aware recorded_at, summary,
applied_change, outcome (resolved / not_resolved / inconclusive) and optional evidence_references.
Only a human calls store.record_resolution(resolution); the incident must already exist.
The append-only attestation does not update diagnostic truth, execute changes or promote rules.
Protect the DB with filesystem/access/retention policies; this is not a multi-tenant service.

## Research artifact boundary

Implemented: contracts, graph/telemetry integration, conservative signatures, tool broker,
one basic investigator, isolated experiments, reports and manual audit records.
Multi-agent orchestration, calibrated ranking, automatic learning/rule promotion, advanced
policy-controlled execution and automatic remediation are **not implemented yet**.
They are deferred until after PoC evaluation.

For a conference artifact, record SDK commit, Python/dependency versions, image digest,
incident window, input hashes, independent telemetry provenance, checks/candidates, receipts,
request/token/probe counts and supported/contradicted/unresolved outcomes. Compare deterministic
and agent-enabled runs, including missing-data/contradiction cases. Withhold fault labels from
the agent. A scripted model verifies protocol behavior, not model quality or diagnosis accuracy.
Live consumer/provider evaluation remains a separate, versioned qualification activity.

Start with the [agent notebook](notebooks/incident-agent.ipynb). Application scenarios belong
in the external cookbooks project, not the SDK.
