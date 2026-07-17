"""Generate or verify checked Lumis SDK JSON Schemas."""

import argparse
import json
from pathlib import Path

from lumis_sdk.adapters.reports import (
    diagnosis_report_json_schema,
    legacy_diagnosis_report_json_schema,
)
from lumis_sdk.config import (
    diagnosis_rule_json_schema,
    legacy_diagnosis_rule_json_schema,
    legacy_project_json_schema,
    legacy_rules_json_schema,
    project_json_schema,
    rules_json_schema,
)
from lumis_sdk.domain import (
    legacy_playbook_json_schema,
    legacy_plugin_manifest_json_schema,
    legacy_policy_json_schema,
    playbook_json_schema,
    plugin_manifest_json_schema,
    policy_json_schema,
    proposal_json_schema,
)

SCHEMA_DIR = Path(__file__).parents[1] / "schemas"
SCHEMAS = {
    SCHEMA_DIR / "lumis-project-v1.schema.json": project_json_schema,
    SCHEMA_DIR / "lumis-rules-v1.schema.json": rules_json_schema,
    SCHEMA_DIR / "lumis-diagnosis-rule-v1.schema.json": diagnosis_rule_json_schema,
    SCHEMA_DIR / "lumis-project-v1alpha1.schema.json": legacy_project_json_schema,
    SCHEMA_DIR / "lumis-rules-v1alpha1.schema.json": legacy_rules_json_schema,
    SCHEMA_DIR / "lumis-diagnosis-rule-v1alpha1.schema.json": legacy_diagnosis_rule_json_schema,
    SCHEMA_DIR / "lumis-diagnosis-report-v1.schema.json": diagnosis_report_json_schema,
    SCHEMA_DIR / "lumis-plugin-manifest-v1.schema.json": plugin_manifest_json_schema,
    SCHEMA_DIR / "lumis-playbook-v1.schema.json": playbook_json_schema,
    SCHEMA_DIR / "lumis-policy-v1.schema.json": policy_json_schema,
    SCHEMA_DIR / "lumis-diagnosis-report-v1alpha1.schema.json": legacy_diagnosis_report_json_schema,
    SCHEMA_DIR / "lumis-plugin-manifest-v1alpha1.schema.json": legacy_plugin_manifest_json_schema,
    SCHEMA_DIR / "lumis-playbook-v1alpha1.schema.json": legacy_playbook_json_schema,
    SCHEMA_DIR / "lumis-policy-v1alpha1.schema.json": legacy_policy_json_schema,
    SCHEMA_DIR / "lumis-action-proposal-v1alpha1.schema.json": proposal_json_schema,
}


def main() -> None:
    """Write the schema or fail when the checked file is stale."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        for path, factory in SCHEMAS.items():
            content = json.dumps(factory(), indent=2, sort_keys=True) + "\n"
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Lumis SDK JSON Schema is missing or stale: {path}")
            print(f"Schema is current: {path}")
        return
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for path, factory in SCHEMAS.items():
        content = json.dumps(factory(), indent=2, sort_keys=True) + "\n"
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
