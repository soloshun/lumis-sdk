# Simple log diagnosis

This cookbook uses OpenARIA as an installed framework. The cookbook owns the synthetic log and the project-specific deterministic rule; OpenARIA provides configuration loading, rule evaluation, reporting, and local memory.

From this repository root:

```bash
uv run openaria diagnose \
  --config cookbook/simple-log-diagnosis/openaria/openaria.yml
```

The `openaria/` directory keeps framework configuration separate from example data: `openaria.yml` declares project-local paths, while `rules.yml` defines the project's deterministic diagnosis rules. Replace those values with the details of another project without changing OpenARIA source code. Add `--log path/to/other.log` to override the configured log for one run.
