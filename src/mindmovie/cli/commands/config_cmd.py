"""Config command — view current configuration settings."""

import typer

from mindmovie.cli.ui.console import (
    console,
    print_header,
    print_key_value_table,
    print_muted,
)
from mindmovie.cli.ui.setup import run_setup_check
from mindmovie.config import load_settings


def config(
    check: bool = typer.Option(
        False,
        "--check",
        help="Validate API keys and system dependencies.",
    ),
    config_file: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration YAML file.",
    ),
) -> None:
    """View current configuration and validate setup.

    Displays all configuration values loaded from environment
    variables and config files. API keys are masked for security.

    Use --check to verify that all required API keys are set and
    system dependencies (FFmpeg, ImageMagick) are installed.
    """
    settings = load_settings(config_file)

    if check:
        ok = run_setup_check(settings)
        if not ok:
            raise typer.Exit(code=1)
        return

    print_header("Mind Movie Configuration")

    # API Keys (masked)
    api_data: dict[str, str] = {}
    anthropic = settings.api.anthropic_api_key.get_secret_value()
    api_data["ANTHROPIC_API_KEY"] = _mask_key(anthropic) if anthropic else "[red]not set[/red]"
    gemini = settings.api.gemini_api_key.get_secret_value()
    api_data["GEMINI_API_KEY"] = _mask_key(gemini) if gemini else "[red]not set[/red]"
    byteplus = settings.api.byteplus_api_key.get_secret_value()
    api_data["BYTEPLUS_API_KEY"] = _mask_key(byteplus) if byteplus else "[red]not set[/red]"
    print_key_value_table("API Keys", api_data)
    console.print()

    # Video settings
    print_key_value_table(
        "Video Generation",
        {
            "Provider": settings.video.provider,
            "Model": settings.video.model,
            "Resolution": settings.video.resolution,
            "Aspect Ratio": settings.video.aspect_ratio,
            "Generate Audio": str(settings.video.generate_audio),
            "Max Concurrent": str(settings.video.max_concurrent),
            "Max Retries": str(settings.video.max_retries),
        },
    )
    console.print()

    # Music settings
    print_key_value_table(
        "Background Music",
        {
            "Source": settings.music.source,
            "File Path": settings.music.file_path or "[dim]none[/dim]",
            "Volume": str(settings.music.volume),
        },
    )
    console.print()

    # Movie structure
    print_key_value_table(
        "Movie Structure",
        {
            "Scene Duration": f"{settings.movie.scene_duration}s",
            "Number of Scenes": str(settings.movie.num_scenes),
            "Title Duration": f"{settings.movie.title_duration}s",
            "Closing Duration": f"{settings.movie.closing_duration}s",
            "Crossfade": f"{settings.movie.crossfade_duration}s",
            "FPS": str(settings.movie.fps),
        },
    )
    console.print()

    # Build settings
    print_key_value_table(
        "Build",
        {
            "Build Directory": settings.build_dir,
            "Output Path": settings.output_path,
        },
    )

    print_muted("\nTip: use 'mindmovie config --check' to validate your setup.")
    print_muted("Config file: use --config to specify a custom YAML config.")


def _mask_key(key: str) -> str:
    """Mask an API key, showing only the last 4 characters."""
    if len(key) <= 4:
        return "****"
    return f"{'*' * (len(key) - 4)}{key[-4:]}"
