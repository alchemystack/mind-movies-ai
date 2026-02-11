"""Main Typer application for Mind Movie Generator CLI."""

import typer

from mindmovie import __version__
from mindmovie.cli.commands.clean import clean
from mindmovie.cli.commands.compile_cmd import compile_video
from mindmovie.cli.commands.config_cmd import config
from mindmovie.cli.commands.generate import generate
from mindmovie.cli.commands.questionnaire import questionnaire
from mindmovie.cli.commands.render import render
from mindmovie.cli.ui.console import console

app = typer.Typer(
    name="mindmovie",
    help="Generate personalized mind movie visualization videos using AI.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"mindmovie version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Mind Movie Generator — AI-powered visualization videos.

    Generate personalized 3-minute visualization videos combining
    aspirational imagery, text affirmations, and uplifting music.

    Quick start: run [bold]mindmovie generate[/bold] for the full pipeline,
    or use individual commands for more control.

    Setup: run [bold]mindmovie config --check[/bold] to verify API keys
    and system dependencies are configured.
    """


# Register commands from individual modules
app.command()(generate)
app.command()(questionnaire)
app.command()(render)
app.command(name="compile")(compile_video)
app.command()(config)
app.command()(clean)
