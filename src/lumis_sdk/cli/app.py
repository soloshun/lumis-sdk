"""Standalone CLI composition for the read-only operational kernel."""

from typing import Annotated

import typer

from lumis_sdk import __version__
from lumis_sdk.cli.incident import console, incident, record_resolution
from lumis_sdk.cli.operational import discover, doctor, graph, init, investigate

app = typer.Typer(no_args_is_help=True, help="Experimental read-only operational intelligence.")


def version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def callback(
    show_version: Annotated[
        bool, typer.Option("--version", callback=version, is_eager=True)
    ] = False,
) -> None:
    """Lumis tests falsifiable candidates; it does not execute remediation."""


app.command()(init)
app.command()(doctor)
app.command()(discover)
app.command()(graph)
app.command()(investigate)
app.command()(incident)
app.command()(record_resolution)
app.command()(console)


def main() -> None:
    app()
