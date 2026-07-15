# Recording a resolution

This cookbook continues a project-owned incident after the simple log diagnosis has produced an incident ID.

```bash
uv run lumis resolve <incident-id> \
  --resolution "Describe the human-confirmed resolution." \
  --config ../simple-log-diagnosis/lumis/lumis.yml

uv run lumis report <incident-id> \
  --config ../simple-log-diagnosis/lumis/lumis.yml
```

The Lumis SDK framework currently stores the resolution in the cookbook project's configured local SQLite memory. It does not infer or execute the resolution.
