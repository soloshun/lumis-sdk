"""Human-facing incident workflow and append-only manual resolution recording."""

import asyncio
from pathlib import Path

import typer
from pydantic import TypeAdapter
from rich.console import Console

from lumis_sdk.core import Evidence, Incident
from lumis_sdk.investigation.contracts import HumanResolution
from lumis_sdk.runtime import IncidentStore, YamlProject
from lumis_sdk.runtime.documents import read_document


def incident(
    project: Path = typer.Option(Path("lumis.yaml"), "--project", exists=True, readable=True),
    event: Path = typer.Option(..., "--incident", exists=True, readable=True),
    observations: Path | None = typer.Option(None, "--observations", exists=True, readable=True),
    use_agent: bool = typer.Option(
        False, "--use-agent", help="Allow bounded paid agent calls only if triage escalates."
    ),
    store: Path | None = typer.Option(None, "--store", help="Append-only SQLite audit sink."),
) -> None:
    """Triage and optional tool-using investigation; never execute recovery."""
    try:
        configured = YamlProject.from_file(project)
        incident = Incident.model_validate_json(read_document(event))
        facts = (
            TypeAdapter(tuple[Evidence, ...]).validate_json(read_document(observations))
            if observations
            else None
        )
        result = asyncio.run(
            configured.handle_incident(incident, observations=facts, use_agent=use_agent)
        )
        if store is not None:
            IncidentStore(store).save(result)
    except Exception as error:
        raise typer.BadParameter(
            "Incident handling failed; check configuration, source access and schema references."
        ) from error
    typer.echo(result.model_dump_json(indent=2))


def record_resolution(
    store: Path = typer.Option(..., "--store", exists=True, readable=True),
    resolution: Path = typer.Option(..., "--resolution", exists=True, readable=True),
    confirm: bool = typer.Option(
        False, "--confirm", help="Attest this is your manual resolution record, not agent output."
    ),
) -> None:
    """Append a human attestation to an existing incident without changing the diagnosis."""
    if not confirm:
        raise typer.BadParameter("Review your manual record and pass --confirm explicitly.")
    try:
        document = HumanResolution.model_validate_json(read_document(resolution))
        IncidentStore(store).record_resolution(document)
    except Exception as error:
        raise typer.BadParameter(
            "Resolution rejected; verify incident ID, schema and unique resolution ID."
        ) from error
    typer.echo("Human resolution recorded; no operational change or rule promotion was executed.")


def console(
    project: Path = typer.Option(Path("lumis.yaml"), "--project", exists=True, readable=True),
) -> None:
    """Interactive local explorer. JSON commands stay undecorated for scripts."""
    from lumis_sdk.cli.operational import discover, doctor, graph

    view = Console(markup=False, highlight=False)
    view.print("\n  L U M I S\n  evidence before explanation / human review before recovery\n")
    while True:
        choice = typer.prompt("1 doctor | 2 sources | 3 graph | 4 incident | q exit", default="q")
        if choice == "q":
            return
        try:
            if choice == "1":
                doctor(project=project)
            elif choice == "2":
                discover(project=project, report=True)
            elif choice == "3":
                graph(project=project, entity=None, hops=3, format="terminal", output=None)
            elif choice == "4":
                event = Path(typer.prompt("Incident JSON path"))
                facts_text = typer.prompt(
                    "Observations JSON path (blank uses YAML)", default="", show_default=False
                )
                facts = Path(facts_text) if facts_text else None
                allow = typer.confirm("Allow paid agent calls if triage escalates?", default=False)
                incident(
                    project=project, event=event, observations=facts, use_agent=allow, store=None
                )
            else:
                view.print("Choose 1, 2, 3, 4 or q.")
        except (typer.BadParameter, typer.Exit) as error:
            view.print(str(error) or "Operation incomplete; inspect source status.")
