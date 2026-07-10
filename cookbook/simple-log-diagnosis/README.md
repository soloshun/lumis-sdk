# Simple log diagnosis

This cookbook uses OpenARIA as an installed framework. The cookbook owns the synthetic log and the project-specific deterministic rule; OpenARIA provides configuration loading, rule evaluation, reporting, and local memory.

From this repository root:

```bash
uv run openaria diagnose \
  --config cookbook/simple-log-diagnosis/openaria.yml \
  --log cookbook/simple-log-diagnosis/failure.log
```

The configuration determines the project name, local memory path, report output location, and diagnosis rule. Replace those values with the details of another project without changing OpenARIA source code.
