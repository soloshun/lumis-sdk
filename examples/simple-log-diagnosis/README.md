# Simple log diagnosis

This synthetic example demonstrates the first OpenARIA proof: a local pipeline log becomes a structured Markdown incident report.

```bash
uv run openaria diagnose --log examples/simple-log-diagnosis/failure.log
```

The report is written to `.openaria/reports/incident-report.md`, and the incident is saved to `.openaria/incidents.db`. It is based entirely on the supplied log, labels the cause as a hypothesis, and suggests safe investigation steps. It does not call an LLM, contact an external system, or execute remediation.

Use the incident ID printed by the command to retrieve the report, save a resolution, and search local history:

```bash
uv run openaria report <incident-id>
uv run openaria resolve <incident-id> --resolution "The source renamed Close to closing_price."
uv run openaria memory search "KeyError Close"
```
