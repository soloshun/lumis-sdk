"""Generate or verify schemas for the active operational contracts only."""

import argparse
import json
from pathlib import Path

from lumis_sdk.core import GraphSnapshot, Hypothesis, Incident, Investigation
from lumis_sdk.runtime.discovery import DiscoveryReport
from lumis_sdk.runtime.project import OperationalProject

SCHEMA_DIR = Path(__file__).parents[1] / "schemas"
SCHEMAS = {
    "lumis-operational-project-v1alpha1.schema.json": OperationalProject,
    "lumis-investigation-v1alpha1.schema.json": Investigation,
    "lumis-graph-v1alpha1.schema.json": GraphSnapshot,
    "lumis-hypothesis-v1alpha1.schema.json": Hypothesis,
    "lumis-incident-v1alpha1.schema.json": Incident,
    "lumis-discovery-v1alpha1.schema.json": DiscoveryReport,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        path = SCHEMA_DIR / name
        content = json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Schema is missing or stale: {path}")
        else:
            path.write_text(content, encoding="utf-8")
        print(f"Schema {'current' if args.check else 'written'}: {path}")


if __name__ == "__main__":
    main()
