"""The `fundlens` command line: one entry point for every pipeline step and service (spec §5.1).

Each step arrives with its own ticket as a subcommand on `app`; this module only owns the shared
callback, which handles `--version` and configures logging before any subcommand runs.
"""

from typing import Annotated

import typer

from fundlens import __version__
from fundlens.logging import configure_logging
from fundlens.settings import get_settings

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Print the fundlens version and exit.",
        ),
    ] = False,
) -> None:
    """fundlens: federal campaign finance, by race, with resolved donors."""
    # Eager, so `--version` exits before this body reads settings; every subcommand gets
    # logging configured from the environment.
    configure_logging(get_settings().log_level)
