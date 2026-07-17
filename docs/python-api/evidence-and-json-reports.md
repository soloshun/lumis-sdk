# Evidence providers and JSON reports

Lumis SDK evidence collection is provider-neutral, bounded, and local-first. The core contract
does not require an observability vendor, model provider, hosted service, or Lumis account.

## Evidence-provider contract

An evidence provider implements one asynchronous method:

```python
from typing import Protocol

from lumis_sdk.domain import EvidenceCollection, EvidenceRequest


class EvidenceProvider(Protocol):
    name: str

    async def collect(self, request: EvidenceRequest) -> EvidenceCollection: ...
```

`EvidenceRequest` carries the incident, requested evidence kinds, item and character budgets,
and an explicit redaction flag. `EvidenceCollection` carries evidence, safe structured failures,
and a `truncated` signal.

Use `EvidenceService` at an application boundary so provider output receives consistent timeout,
kind filtering, duplicate-ID handling, redaction, per-item limits, and total-size limits:

```python
import asyncio

from lumis_sdk.application import EvidenceService
from lumis_sdk.domain import EvidenceCollection, EvidenceRequest
from lumis_sdk.testkit import FakeEvidenceProvider, make_test_evidence, make_test_incident

request = EvidenceRequest(
    incident=make_test_incident(),
    kinds=["log_window", "schema_diff"],
    max_items=20,
    max_total_characters=100_000,
    max_item_characters=8_000,
    redact=True,
)
provider = FakeEvidenceProvider(
    EvidenceCollection(provider="fixture", items=[make_test_evidence()])
)
collection = asyncio.run(EvidenceService(provider).collect(request))
```

Provider exceptions and timeouts are represented as `EvidenceFailure`; they are not silently
treated as empty successful evidence.

## Local JSON reference adapter

The reference CLI composes `LocalJsonEvidenceProvider` for synthetic fixtures and project-owned
local context:

```yaml
spec:
  evidenceProviders:
    - provider: local-json
      path: evidence/schema-diff.json
      kinds: [schema_diff]
      maxItems: 10
      maxTotalCharacters: 100000
      maxItemCharacters: 8000
      timeoutSeconds: 5
      redact: true
```

The file may contain an evidence array or an object with an `items` array:

```json
{
  "items": [
    {
      "id": "schema-diff-1",
      "source": "schema-registry",
      "kind": "schema_diff",
      "detail": "customer_id was removed",
      "confidence": 1.0,
      "reference": "schema://orders/current-vs-previous"
    }
  ]
}
```

The adapter reads at most one MiB and makes no network call. Relative paths resolve from
`lumis.yml`; they are local authority granted by the user running the SDK.

## Versioned JSON diagnosis report

Set the project report provider to `json`:

```yaml
spec:
  reports:
    provider: json
    outputDir: .lumis/reports
```

`lumis diagnose` then writes `incident-report.json`. The strict
`lumis.dev/v1` `DiagnosisReport` contains:

- normalized incident input;
- structured diagnosis and triage;
- facts, evidence, hypothesis, confidence, and missing evidence;
- recommended next steps and suggested playbook;
- explicit truth state;
- an optional human-confirmed resolution.

Python applications can use:

```python
from lumis_sdk.adapters.reports import (
    JsonReportWriter,
    parse_json_report,
    render_json_report,
)
```

The checked schema is
[`schemas/lumis-diagnosis-report-v1.schema.json`](../../schemas/lumis-diagnosis-report-v1.schema.json).

## Reusable testkit

Third-party adapters can import:

```python
from lumis_sdk.testkit import (
    FakeEvidenceProvider,
    assert_evidence_collection_contract,
    assert_json_report_round_trip,
    make_test_evidence,
    make_test_incident,
)
```

These helpers depend only on Lumis SDK and Python. They require no live service, credentials,
model call, or pytest runtime dependency.

## Safety boundary

Evidence remains untrusted data even after collection. Redaction is a conservative baseline, not
a substitute for provider-side minimization and access control. Evidence providers do not gain
execution authority, and JSON reports do not authorize a suggested playbook.
