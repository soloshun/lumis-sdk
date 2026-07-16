# Structured deterministic rules

Structured rules implement the v0.2 Diagnosis-as-Code contract for incidents that contain
fields and evidence beyond one log string. Evaluation is local, deterministic, model-free,
and independent of the Lumis hosted product.

## Rule document

Each file contains one strict `DiagnosisRule`:

```yaml
apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRule
metadata:
  name: missing-required-column
  version: "1"
spec:
  priority: 100
  match:
    all:
      - field: log.text
        contains: KeyError
      - field: schema.diff.removed_count
        greaterThan: 0
    any:
      - field: component.type
        equals: transformation
      - field: labels.pipeline_domain
        equals: data
    not:
      - field: incident.status
        equals: resolved
  diagnosis:
    classification: schema_change
    severity: high
    summary: A required field was unavailable.
    hypothesis: The upstream schema or normalization mapping changed.
    confidence: 0.8
    confirmedFacts:
      - The current schema contains at least one removed field.
  evidence:
    required: [schema_diff]
  recommendedNextSteps:
    - Compare the current and previous successful schemas.
  suggestedPlaybook: investigate_schema_contract
```

Unknown fields fail validation. Every condition defines exactly one operator:

- `contains`: case-insensitive substring comparison;
- `equals`: exact string, number, or boolean comparison;
- `prefix`: case-sensitive string prefix;
- `matchesRegex`: Python regular expression search, validated when the rule loads;
- `greaterThan`, `greaterThanOrEqual`, `lessThan`, `lessThanOrEqual`: numeric comparison.

Fields use dot paths. Callers may supply nested mappings or literal dotted keys. `all` requires
every condition, `any` requires at least one when present, and `not` requires every listed
condition to be false.

## Python API

```python
from pathlib import Path

from lumis_sdk.adapters.deterministic import diagnose_structured
from lumis_sdk.config import load_diagnosis_rule
from lumis_sdk.domain import EvidenceItem

rule = load_diagnosis_rule(Path("rules/missing-required-column.yml"))
result = diagnose_structured(
    fields={
        "log": {"text": "ERROR KeyError: customer_id"},
        "schema": {"diff": {"removed_count": 1}},
        "component": {"type": "transformation"},
        "labels": {"pipeline_domain": "data"},
        "incident": {"status": "open"},
    },
    rules=[rule],
    evidence=[
        EvidenceItem(
            id="schema-diff-1",
            source="schema-registry",
            kind="schema_diff",
            detail="customer_id was removed",
            confidence=1.0,
            reference="schema://orders/current-vs-previous",
        )
    ],
)

if result.winner:
    print(result.winner.rule_id)
    print(result.selection_reason)
    print(result.winner.matched_conditions)
    print(result.winner.evidence_references)
else:
    print(result.candidates[0].failed_conditions)
    print(result.candidates[0].missing_evidence)
```

Every candidate includes rule ID/version, priority, specificity, matched and failed conditions,
missing evidence, and evidence references. Matching candidates are ranked by descending priority,
then descending specificity, then stable input order. Specificity weights `all` conditions twice,
then counts `any`, `not`, and required-evidence entries.

## CLI validation and fixture testing

The project `spec.rules.files` list may point either to legacy `DiagnosisRuleSet` files or to
single `DiagnosisRule` files. A project must migrate the complete collection together; mixing
both formats is rejected to avoid ambiguous cross-engine ordering.

```bash
lumis rules validate --config lumis.yml
lumis rules test --rule rules/schema-change.yml --input fixtures/schema-change.json
```

Fixture input contains a `fields` object and an optional `evidence` array of `EvidenceItem`
objects. The command emits JSON suitable for CI assertions and editor integrations. Input is
bounded to one MiB and no network or model call is made.

## Migration from `all_contains`

Existing `DeterministicRule` and `diagnose_text_with_explanation` behavior remains available.
Migrate one complete project rule collection at a time:

1. Create one `DiagnosisRule` file per legacy rule.
2. Use `metadata.name` as the old `id` and `metadata.version` as the old `version`.
3. Replace every `all_contains` term with an `all` condition on `log.text`.
4. Move diagnosis fields under `spec.diagnosis`.
5. Add required evidence and structured conditions where reliable signals exist.
6. Test matching, non-matching, missing-evidence, and tie fixtures with `lumis rules test`.
7. Replace the project rule file list only after the complete collection passes.

Confidence remains human-authored diagnostic calibration. It does not grant execution authority.
