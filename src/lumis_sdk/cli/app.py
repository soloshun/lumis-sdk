"""Lumis SDK command-line composition root."""

import asyncio
import json
from pathlib import Path

import typer
from pydantic import ValidationError

from lumis_sdk import __version__
from lumis_sdk.adapters.deterministic import diagnose_structured, diagnose_text
from lumis_sdk.adapters.evidence import LocalJsonEvidenceProvider
from lumis_sdk.adapters.incidents import incident_from_log
from lumis_sdk.adapters.reports import (
    append_resolution,
    render_json_report,
    render_markdown_report,
)
from lumis_sdk.adapters.sqlite import IncidentNotFoundError, SQLiteIncidentStore, search_incidents
from lumis_sdk.application import EvidenceService
from lumis_sdk.config import (
    MAX_CONFIG_BYTES,
    LumisConfig,
    load_config,
    load_diagnosis_rule,
    resolve_project_path,
)
from lumis_sdk.domain import DiagnosisResult, EvidenceItem, EvidenceRequest, IncidentInput

MAX_LOG_BYTES = 10 * 1024 * 1024
DEFAULT_CONFIG_PATH = Path("lumis.yml")

app = typer.Typer(
    name="lumis",
    help="Turn pipeline failures into structured incident reports.",
    no_args_is_help=True,
)
memory_app = typer.Typer(help="Search local Lumis SDK incident memory.")
rules_app = typer.Typer(help="Validate and test deterministic diagnosis rules.")
app.add_typer(memory_app, name="memory")
app.add_typer(rules_app, name="rules")


def version_callback(value: bool) -> None:
    """Print the package version when requested."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def lumis(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the Lumis SDK version and exit.",
    ),
) -> None:
    """Lumis SDK command-line interface."""


@app.command("init")
def initialize(
    destination: Path = typer.Option(Path("."), "--destination", help="Project directory."),
) -> None:
    """Create a minimal versioned local project and rule set."""
    destination.mkdir(parents=True, exist_ok=True)
    config_path = destination / "lumis.yml"
    rules_path = destination / "rules.yml"
    existing = [path for path in (config_path, rules_path) if path.exists()]
    if existing:
        raise typer.BadParameter(
            f"Refusing to overwrite: {', '.join(str(path) for path in existing)}"
        )
    config_path.write_text(_INITIAL_PROJECT, encoding="utf-8")
    rules_path.write_text(_INITIAL_RULES, encoding="utf-8")
    typer.echo(f"Created {config_path}")
    typer.echo(f"Created {rules_path}")


@app.command()
def doctor(
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", exists=True, readable=True),
) -> None:
    """Validate configuration, rules, paths, and safe local defaults without writing state."""
    project_config = _load_or_exit(config)
    checks = [
        ("configuration", "ok"),
        ("api version", project_config.source_api_version),
        ("deterministic rules", str(len(project_config.rules))),
        ("model assistance", "enabled" if project_config.model.enabled else "disabled"),
        ("memory provider", project_config.memory.provider),
        ("report provider", project_config.reports.provider),
    ]
    if project_config.incident_sources:
        log_path = resolve_project_path(config, project_config.incident_sources[0].path)
        checks.append(("local log", "readable" if log_path.is_file() else f"missing: {log_path}"))
    for index, provider in enumerate(project_config.evidence_providers, start=1):
        evidence_path = resolve_project_path(config, provider.path)
        state = "readable" if evidence_path.is_file() else f"missing: {evidence_path}"
        checks.append((f"evidence provider {index} ({provider.provider})", state))
    for name, value in checks:
        typer.echo(f"{name}: {value}")
    if project_config.model.enabled:
        typer.echo(
            "warning: model assistance is enabled; provider adapters remain explicit and opt-in"
        )


@app.command()
def diagnose(
    log: Path | None = typer.Option(None, "--log", help="Override the configured local log."),
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", exists=True, readable=True),
    output: Path | None = typer.Option(None, "--output", help="Override Markdown report path."),
) -> None:
    """Diagnose a bounded local log using configured deterministic rules."""
    project_config = _load_or_exit(config)
    log_path = log or _telemetry_log_path(config, project_config)
    log_text = _read_bounded_log(log_path)
    incident = incident_from_log(log_text, str(log_path), project_config.project)
    configured_evidence = asyncio.run(
        _collect_configured_evidence(config, project_config, incident)
    )
    if project_config.structured_rules:
        supplied_evidence = [
            EvidenceItem(
                id="provided-log-1",
                source="provided_log",
                detail=next(
                    (line.strip() for line in log_text.splitlines() if line.strip()),
                    "No log content",
                ),
                confidence=1.0,
                kind="log_window",
                reference=str(log_path),
            ),
            *configured_evidence,
        ]
        diagnosis = diagnose_structured(
            {
                "log": {"text": log_text},
                "source": {"tool": "local-log"},
                "pipeline": {"name": project_config.project},
                "environment": project_config.environment,
            },
            project_config.structured_rules,
            supplied_evidence,
        ).diagnosis
    else:
        diagnosis = diagnose_text(log_text, project_config.rules)
        if configured_evidence:
            diagnosis = diagnosis.model_copy(
                update={"evidence": [*diagnosis.evidence, *configured_evidence]}
            )
    report_text = _render_report(project_config, incident, diagnosis)
    extension = "json" if project_config.reports.provider == "json" else "md"
    report_path = output or resolve_project_path(
        config, f"{project_config.reports.output_dir}/incident-report.{extension}"
    )
    memory_path = resolve_project_path(config, project_config.memory.path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    stored = SQLiteIncidentStore(memory_path).save(incident, diagnosis, report_text, report_path)
    typer.echo(f"Incident report written to {report_path}")
    typer.echo(f"Incident ID: {stored.id}")


@app.command()
def report(
    incident_id: str,
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", exists=True),
) -> None:
    """Print a stored incident report and any human-confirmed resolution."""
    try:
        stored = SQLiteIncidentStore(_memory_path(config)).get(incident_id)
    except IncidentNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    if Path(stored.report_path).suffix.lower() == ".json":
        typer.echo(
            render_json_report(
                stored.incident,
                stored.diagnosis,
                truth_state=stored.truth_state,
                confirmed_resolution=stored.resolution,
            )
        )
    else:
        typer.echo(append_resolution(stored.report_markdown, stored.resolution))


@app.command()
def resolve(
    incident_id: str,
    resolution: str = typer.Option(..., "--resolution", help="Human-confirmed resolution."),
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", exists=True),
) -> None:
    """Store a human-confirmed resolution; never infer one from model output."""
    try:
        stored = SQLiteIncidentStore(_memory_path(config)).set_resolution(incident_id, resolution)
    except IncidentNotFoundError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Resolution saved for incident {stored.id}; truth_state={stored.truth_state.value}")


@memory_app.command("search")
def memory_search(
    query: str,
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", exists=True),
) -> None:
    """Find similar incidents using transparent local keyword matching."""
    results = search_incidents(SQLiteIncidentStore(_memory_path(config)).list_all(), query)
    if not results:
        typer.echo("No matching incidents found.")
        return
    typer.echo("Matching incidents (keyword score):")
    for result in results:
        stored = result.incident
        pipeline_name = stored.incident.pipeline_name or "not provided"
        typer.echo(
            "- "
            f"{stored.id} | score={result.score} | {stored.diagnosis.triage.classification} | "
            f"{pipeline_name} | {stored.truth_state.value}"
        )


@rules_app.command("validate")
def rules_validate(
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", exists=True, readable=True),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable output."),
) -> None:
    """Validate configured rule files and show stable IDs, versions, and priorities."""
    project_config = _load_or_exit(config)
    rows = [
        {
            "id": rule.stable_id,
            "version": rule.version,
            "priority": rule.priority,
            "classification": rule.classification,
            "kind": "DiagnosisRuleSet rule",
        }
        for rule in project_config.rules
    ]
    rows.extend(
        {
            "id": rule.stable_id,
            "version": rule.metadata.version,
            "priority": rule.spec.priority,
            "classification": rule.spec.diagnosis.classification,
            "kind": "DiagnosisRule",
        }
        for rule in project_config.structured_rules
    )
    if as_json:
        typer.echo(json.dumps({"valid": True, "rules": rows}, indent=2))
        return
    typer.echo(f"Valid rules: {len(rows)}")
    for row in rows:
        typer.echo(
            f"- {row['id']}@{row['version']} | priority={row['priority']} | "
            f"{row['classification']} | {row['kind']}"
        )


@rules_app.command("test")
def rules_test(
    rule: Path = typer.Option(..., "--rule", exists=True, readable=True),
    input_path: Path = typer.Option(..., "--input", exists=True, readable=True),
) -> None:
    """Evaluate one DiagnosisRule against bounded JSON fields and evidence."""
    try:
        document = load_diagnosis_rule(rule)
    except (OSError, ValueError, ValidationError) as error:
        raise typer.BadParameter(f"Rule validation failed: {error}") from error
    payload = _read_bounded_json(input_path)
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        raise typer.BadParameter("Rule test input must contain an object at `fields`.")
    evidence_raw = payload.get("evidence", [])
    if not isinstance(evidence_raw, list):
        raise typer.BadParameter("Rule test input `evidence` must be an array.")
    try:
        evidence = [EvidenceItem.model_validate(item) for item in evidence_raw]
    except ValidationError as error:
        raise typer.BadParameter(f"Invalid evidence: {error}") from error
    result = diagnose_structured(fields, [document], evidence)
    output = {
        "matched": result.winner is not None,
        "winner": result.winner.rule_id if result.winner else None,
        "selectionReason": result.selection_reason,
        "diagnosis": {
            "classification": result.diagnosis.triage.classification,
            "missingEvidence": result.diagnosis.missing_evidence,
        },
        "candidates": [
            {
                "ruleId": candidate.rule_id,
                "ruleVersion": candidate.rule_version,
                "priority": candidate.priority,
                "specificity": candidate.specificity,
                "matched": candidate.matched,
                "matchedConditions": [
                    _condition_row(condition) for condition in candidate.matched_conditions
                ],
                "failedConditions": [
                    _condition_row(condition) for condition in candidate.failed_conditions
                ],
                "missingEvidence": list(candidate.missing_evidence),
                "evidenceReferences": list(candidate.evidence_references),
            }
            for candidate in result.candidates
        ],
    }
    typer.echo(json.dumps(output, indent=2, default=str))


def main() -> None:
    """Run the Lumis SDK CLI."""
    app()


def _load_or_exit(config_path: Path) -> LumisConfig:
    try:
        return load_config(config_path)
    except (OSError, ValueError, ValidationError) as error:
        typer.echo(f"Configuration validation failed: {error}", err=True)
        raise typer.Exit(code=2) from error


def _read_bounded_log(path: Path) -> str:
    if not path.is_file():
        raise typer.BadParameter(f"Telemetry log does not exist or is not a file: {path}")
    size = path.stat().st_size
    if size > MAX_LOG_BYTES:
        raise typer.BadParameter(f"Telemetry log exceeds {MAX_LOG_BYTES} bytes: {path}")
    return path.read_text(encoding="utf-8")


def _condition_row(condition: object) -> dict[str, object]:
    values: dict[str, object] = dict(vars(condition))
    indexes = values.pop("matched_element_indexes", ())
    values["matchedElementIndexes"] = list(indexes) if isinstance(indexes, tuple) else []
    return values


def _read_bounded_json(path: Path) -> dict[str, object]:
    size = path.stat().st_size
    if size > MAX_CONFIG_BYTES:
        raise typer.BadParameter(f"Rule test input exceeds {MAX_CONFIG_BYTES} bytes: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"Rule test input is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise typer.BadParameter("Rule test input must be a JSON object.")
    return payload


async def _collect_configured_evidence(
    config_path: Path,
    project_config: LumisConfig,
    incident: IncidentInput,
) -> list[EvidenceItem]:
    collected: list[EvidenceItem] = []
    seen_ids: set[str] = set()
    for provider_config in project_config.evidence_providers:
        provider = LocalJsonEvidenceProvider(
            resolve_project_path(config_path, provider_config.path)
        )
        service = EvidenceService(
            provider=provider,
            timeout_seconds=provider_config.timeout_seconds,
        )
        collection = await service.collect(
            EvidenceRequest(
                incident=incident,
                kinds=provider_config.kinds,
                max_items=provider_config.max_items,
                max_total_characters=provider_config.max_total_characters,
                max_item_characters=provider_config.max_item_characters,
                redact=provider_config.redact,
            )
        )
        for failure in collection.failures:
            typer.echo(
                f"warning: evidence provider {failure.provider}: {failure.code}: {failure.message}",
                err=True,
            )
        if collection.truncated:
            typer.echo(
                f"warning: evidence provider {collection.provider} reached a configured bound",
                err=True,
            )
        for item in collection.items:
            if item.id in seen_ids:
                typer.echo(
                    f"warning: duplicate evidence ID ignored: {item.id}",
                    err=True,
                )
                continue
            seen_ids.add(item.id)
            collected.append(item)
    return collected


def _render_report(
    project_config: LumisConfig,
    incident: IncidentInput,
    diagnosis: DiagnosisResult,
) -> str:
    if project_config.reports.provider == "json":
        return render_json_report(incident, diagnosis)
    return render_markdown_report(incident, diagnosis)


def _memory_path(config_path: Path) -> Path:
    project_config = _load_or_exit(config_path)
    return resolve_project_path(config_path, project_config.memory.path)


def _telemetry_log_path(config_path: Path, project_config: LumisConfig) -> Path:
    if not project_config.incident_sources:
        raise typer.BadParameter("Provide --log or configure one local-log incident source.")
    return resolve_project_path(config_path, project_config.incident_sources[0].path)


_INITIAL_PROJECT = """apiVersion: lumis.dev/v1alpha1
kind: Project
metadata:
  name: my-pipeline
spec:
  environment: local
  memory:
    provider: sqlite
    path: .lumis/incidents.db
  reports:
    provider: markdown
    outputDir: .lumis/reports
  incidentSources:
    - provider: local-log
      path: logs/latest-failure.log
  rules:
    files: [rules.yml]
  model:
    enabled: false
"""

_INITIAL_RULES = """apiVersion: lumis.dev/v1alpha1
kind: DiagnosisRuleSet
metadata:
  name: project-rules
spec:
  rules: []
"""
