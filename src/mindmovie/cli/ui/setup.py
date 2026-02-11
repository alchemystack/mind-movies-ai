"""Setup wizard for first-run API key detection and configuration guidance."""

import shutil
from pathlib import Path

from mindmovie.config.settings import Settings

from .console import (
    console,
    print_error,
    print_info,
    print_muted,
    print_success,
    print_warning,
)


def check_system_dependencies() -> list[str]:
    """Check for required system dependencies (ffmpeg).

    Note: ImageMagick is NOT required — Pillow handles all text
    rendering, avoiding the ImageMagick dependency that MoviePy's
    TextClip would otherwise need.

    Returns:
        List of missing dependency names.
    """
    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    return missing


def run_setup_check(settings: Settings) -> bool:
    """Check API keys and system dependencies, printing guidance for anything missing.

    Args:
        settings: The loaded application settings.

    Returns:
        True if all required configuration is present, False otherwise.
    """
    all_ok = True

    # --- Check API keys ---
    missing_keys = settings.get_missing_api_keys()
    if missing_keys:
        all_ok = False
        print_error("Missing required API keys:")
        console.print()
        for key in missing_keys:
            _print_key_help(key)
        console.print()
        print_info("Set keys using one of these methods:")
        print_muted("  1. Create a .env file:  cp .env.example .env  (then edit)")
        print_muted("  2. Export in your shell: export ANTHROPIC_API_KEY=sk-ant-...")
        print_muted("  3. Use a config.yaml:   mindmovie config --help")
        console.print()

    # --- Check system dependencies ---
    missing_deps = check_system_dependencies()
    if missing_deps:
        all_ok = False
        print_warning(f"Missing system dependencies: {', '.join(missing_deps)}")
        print_muted("  Install with:")
        print_muted("    macOS:  brew install ffmpeg")
        print_muted("    Linux:  apt install ffmpeg")
        print_muted("    Windows: choco install ffmpeg")
        console.print()

    # --- Check for .env file ---
    if not Path(".env").exists() and missing_keys:
        env_example = Path(".env.example")
        if env_example.exists():
            print_info(
                "Tip: Copy .env.example to .env and fill in your API keys:"
            )
            print_muted("  cp .env.example .env")
            console.print()

    if all_ok:
        print_success("All required configuration is present.")

    return all_ok


def validate_api_keys_for_command(
    settings: Settings,
    *,
    require_anthropic: bool = False,
    require_gemini: bool = False,
) -> bool:
    """Validate that specific API keys are set, with actionable error messages.

    Args:
        settings: The loaded application settings.
        require_anthropic: Whether ANTHROPIC_API_KEY is required.
        require_gemini: Whether GEMINI_API_KEY is required.

    Returns:
        True if all required keys are present, False otherwise.
    """
    ok = True

    if require_anthropic:
        key = settings.api.anthropic_api_key.get_secret_value()
        if not key:
            _print_key_help("ANTHROPIC_API_KEY")
            ok = False

    if require_gemini:
        key = settings.api.gemini_api_key.get_secret_value()
        if not key:
            _print_key_help("GEMINI_API_KEY")
            ok = False

    if not ok:
        console.print()
        print_info("Set keys in your .env file or as environment variables.")
        print_muted("  See: mindmovie config")

    return ok


def _print_key_help(key_name: str) -> None:
    """Print help text for a specific missing API key."""
    help_text = _KEY_HELP.get(key_name, f"  {key_name} is not set.")
    print_error(help_text)


_KEY_HELP: dict[str, str] = {
    "ANTHROPIC_API_KEY": (
        "ANTHROPIC_API_KEY is not set. "
        "Get one at https://console.anthropic.com/settings/keys"
    ),
    "GEMINI_API_KEY": (
        "GEMINI_API_KEY is not set. "
        "Get one at https://aistudio.google.com/apikey"
    ),
}
