"""Clean command — remove generated assets and pipeline state."""

import typer

from mindmovie.cli.ui.console import print_info, print_success, print_warning
from mindmovie.config import load_settings
from mindmovie.state import StateManager


def clean(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt and remove immediately.",
    ),
    config_file: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration YAML file.",
    ),
) -> None:
    """Remove all generated assets and pipeline state.

    Deletes the build directory containing intermediate video clips,
    voiceover audio, pipeline state, and other generated artifacts.
    Use this to start a fresh mind movie generation from scratch.
    """
    settings = load_settings(config_file)
    manager = StateManager(build_dir=settings.build_dir)

    if not manager.exists():
        print_info("Build directory is already clean. Nothing to remove.")
        return

    if not force:
        print_warning(f"This will remove all files in '{settings.build_dir}/'.")
        confirmed = typer.confirm("Are you sure?", default=False)
        if not confirmed:
            print_info("Aborted.")
            raise typer.Exit()

    manager.clear()
    print_success(f"Build directory '{settings.build_dir}/' has been cleared.")
