# Phase 1 tutorial and video script

This written script is the versioned source for a future walkthrough video. The written commands
remain authoritative when video UI or package versions become stale.

## 1. What Lumis SDK is (2 minutes)

- Explain deterministic-first, evidence-grounded, model-optional incident diagnosis.
- Separate the open SDK from the Loomis/Lumis product.
- Show [core concepts](../concepts/core-concepts.md) and the ports-and-adapters diagram.

## 2. Install and diagnose locally (5 minutes)

Run the [simple log cookbook](../../cookbook/simple-log-diagnosis/README.md). Open the project YAML,
rule file, synthetic log, generated report, and SQLite-backed incident ID. Emphasize that the run
uses no credential, network call, model, or executor.

## 3. Explain Diagnosis-as-Code (5 minutes)

Use the [structured rule walkthrough](../../cookbook/structured-rule-evaluation/README.md). Explain
stable IDs, versions, `all`/`any`/`not`, evidence preconditions, priority, specificity, and complete
candidate explanations. Change only a fixture or project rule—not SDK core.

## 4. Add bounded evidence and a plugin (6 minutes)

Run the [offline webhook/HTTP connector](../../cookbook/webhook-http-evidence/README.md). Show the
static manifest before module import, declared authorities, HMAC/replay boundary, HTTPS origin
allowlist, environment secret reference, response cap, and mock transport limitation.

## 5. Relate it to production systems (6 minutes)

- Map Alertmanager alerts and Prometheus evidence using the
  [Prometheus walkthrough](../../cookbook/prometheus-alertmanager/README.md).
- Show process-shared memory and adopter-owned schema names with the
  [PostgreSQL walkthrough](../../cookbook/postgres-memory/README.md).
- Point to data-pipeline, ML-quality, and software-delivery examples.

## 6. Govern recovery without pretending to execute (5 minutes)

Run guarded proposal and verification replay cookbooks. Show playbook/policy revision pinning,
evidence digests, high-risk approval rules, explicit verification states, and why no core executor
exists.

## 7. Build your own integration (4 minutes)

Choose a stable port, implement an adapter in an independent package, declare compatibility and
authorities, run the testkit contract, and test offline. End with the public API inventory,
compatibility policy, security review, contribution guide, and roadmap.

## Recording checklist

- Pin the SDK/plugin versions shown on screen.
- Use synthetic fixtures and test credentials only.
- Display commands and expected output in captions or description.
- State every network, model, database, and execution boundary.
- Link this written script and the exact release tag.
- Never describe roadmap capability as implemented.
