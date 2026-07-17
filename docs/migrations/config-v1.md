# Migrate versioned documents to `lumis.dev/v1`

The stable v1 envelopes preserve the released alpha field shapes and change the version marker.
Migration validates the complete document before producing output; unknown fields and invalid
values fail closed.

## Migrate one file

Preview stable YAML on standard output:

```bash
lumis config migrate lumis.yml
```

Write to a new path:

```bash
lumis config migrate lumis.yml --output lumis.v1.yml
```

Existing output is never replaced unless `--force` is supplied. JSON input is accepted, and the
canonical migration output is YAML. Running migration on an already-v1 file validates it and is
idempotent.

Supported kinds are `Project`, `DiagnosisRuleSet`, `DiagnosisRule`, `DiagnosisReport`,
`PluginManifest`, `Playbook`, and `RecoveryPolicy`.

## Migrate a project collection

Migrate the project and every referenced rule file before switching paths:

```bash
lumis config migrate lumis.yml -o lumis.v1.yml
lumis config migrate rules.yml -o rules.v1.yml
lumis doctor --config lumis.v1.yml
lumis rules validate --config lumis.v1.yml
```

Update `spec.rules.files` if output filenames change. The loader rejects a v1 project that
references v1alpha1 rules, preventing a partially migrated collection from appearing valid.

For an in-place change under source control, first review the preview and diff, then use a
temporary output or `--force` only after the file is tracked and recoverable.

## Python API

```python
from pathlib import Path

from lumis_sdk.config import migrate_config_file, render_migrated_yaml

result = migrate_config_file(Path("lumis.yml"))
print(result.kind, result.changed, result.target_api_version)
print(render_migrated_yaml(result))
```

`migrate_config_document` accepts an in-memory mapping. Both APIs return a frozen
`ConfigMigrationResult` and never write files themselves.

## Compatibility window

Project/rule v1alpha1 reading remains available through `1.x` and is planned for removal in
`2.0`. Treat the warning as upgrade work, not as a diagnosis failure. Historical alpha schemas
remain under `schemas/`; new integrations should target the corresponding `*-v1.schema.json`.
