"""Command-line interface for OpenARIA."""

import typer

from openaria import __version__

app = typer.Typer(
    name="openaria",
    help="Turn pipeline failures into structured incident reports.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print the package version when requested."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def openaria(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the OpenARIA version and exit.",
    ),
) -> None:
    """OpenARIA command-line interface."""


def main() -> None:
    """Run the OpenARIA CLI."""
    app()
