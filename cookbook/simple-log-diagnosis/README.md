# Simple log diagnosis

This cookbook uses Lumis SDK as an installed framework. The cookbook owns the synthetic log and project rule; the CLI composes strict configuration with the canonical local-log, deterministic-rule, Markdown, and SQLite adapters. It is the smallest example of the same structure used by the agentic cookbooks.

From this repository root:

```bash
uv run lumis diagnose \
  --config cookbook/simple-log-diagnosis/lumis/lumis.yml
```

The `lumis/` directory keeps framework configuration separate from example data: `lumis.yml` declares project-local paths, while `rules.yml` defines the project's deterministic diagnosis rules. Replace those values with the details of another project without changing Lumis SDK source code. Add `--log path/to/other.log` to override the configured log for one run.
