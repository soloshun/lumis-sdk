# Recording a resolution

This cookbook continues a project-owned incident after the simple log diagnosis has produced an incident ID.

```bash
uv run openaria resolve <incident-id> \
  --resolution "Describe the human-confirmed resolution." \
  --config ../simple-log-diagnosis/openaria/openaria.yml

uv run openaria report <incident-id> \
  --config ../simple-log-diagnosis/openaria/openaria.yml
```

The OpenARIA framework currently stores the resolution in the cookbook project's configured local SQLite memory. It does not infer or execute the resolution.
