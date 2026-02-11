"""Generate command — runs the full mind movie generation pipeline."""

import asyncio
from pathlib import Path

import typer

from mindmovie.cli.ui.console import (
    console,
    print_error,
    print_header,
    print_info,
    print_muted,
    print_success,
    print_warning,
)
from mindmovie.cli.ui.progress import create_progress
from mindmovie.cli.ui.prompts import confirm_action, prompt_user_input
from mindmovie.cli.ui.setup import run_setup_check
from mindmovie.config import load_settings
from mindmovie.core.cost_estimator import CostBreakdown
from mindmovie.core.pipeline import PipelineError, PipelineOrchestrator
from mindmovie.state import PipelineStage, StateManager
from mindmovie.video import CompositionError


def _display_assistant(message: str) -> None:
    """Display a questionnaire assistant message."""
    console.print(f"\n[bright_cyan]Coach:[/bright_cyan] {message}\n")


def _display_cost_and_confirm(breakdown: CostBreakdown) -> bool:
    """Show cost breakdown and ask for confirmation."""
    console.print()
    print_header("Generation Estimate")
    console.print(breakdown.format_summary())
    console.print()
    return confirm_action("Proceed with generation?", default=True)


def generate(
    output: str = typer.Option(
        "mind_movie.mp4",
        "--output",
        "-o",
        help="Output file path for the generated mind movie MP4.",
    ),
    resume: bool = typer.Option(
        True,
        "--resume/--no-resume",
        help="Resume from saved state if available. Use --no-resume to start fresh.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run questionnaire and scene generation, show cost estimate, then stop.",
    ),
    music: str | None = typer.Option(
        None,
        "--music",
        "-m",
        help="Path to a background music file (MP3/WAV). Overrides config.",
    ),
    config_file: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration YAML file.",
    ),
) -> None:
    """Run the complete mind movie generation pipeline.

    Executes all stages end-to-end: interactive questionnaire, AI scene
    generation, video clip generation via Veo API, and final video
    composition with MoviePy.

    The pipeline saves progress after each stage, so you can safely
    interrupt with Ctrl+C and resume later. Use --dry-run to see cost
    estimates before committing to video generation.

    Requires: ANTHROPIC_API_KEY and GEMINI_API_KEY set in .env or
    environment variables.
    """
    settings = load_settings(config_file)
    state_manager = StateManager(settings.build_dir)

    # --- Handle existing state ---
    if state_manager.exists():
        state = state_manager.load_or_create()
        if state.current_stage == PipelineStage.COMPLETE:
            if state.output_path:
                print_success(f"Mind movie already complete: {state.output_path}")
            else:
                print_success("Mind movie already complete.")
            print_info("Use 'mindmovie clean' to start fresh.")
            return

        if resume:
            print_info(f"Resuming from stage: {state.current_stage.value}")
        else:
            if not confirm_action(
                "Existing pipeline state found. Start fresh?", default=False
            ):
                print_muted("Cancelled.")
                raise typer.Exit(code=0)
            state_manager.clear()
            print_info("Cleared previous state. Starting fresh.")
    elif not resume:
        # No state exists and --no-resume was given — that's fine, just start
        pass

    # --- Validate API keys with setup wizard ---
    if not run_setup_check(settings):
        raise typer.Exit(code=1)

    # --- Validate music file if provided ---
    music_path: Path | None = None
    if music:
        music_path = Path(music)
        if not music_path.exists():
            print_error(f"Music file not found: {music_path}")
            raise typer.Exit(code=1)

    # --- Pipeline header ---
    print_header("Mind Movie Generator")
    state = state_manager.load_or_create()
    if state.current_stage == PipelineStage.QUESTIONNAIRE:
        print_info(
            "I'll guide you through 6 life areas to create your personalized mind movie."
        )
        print_info('Type "skip" to skip a category, or "done" to finish early.\n')

    # --- Build progress tracking for video generation ---
    progress = create_progress()
    progress_task_id = None

    def on_video_complete() -> None:
        if progress_task_id is not None:
            progress.advance(progress_task_id)

    # --- Create and run the pipeline ---
    orchestrator = PipelineOrchestrator(
        settings=settings,
        state_manager=state_manager,
        input_fn=prompt_user_input,
        output_fn=_display_assistant,
        cost_confirm_fn=_display_cost_and_confirm,
        progress_callback=on_video_complete,
    )

    try:
        result = asyncio.run(
            orchestrator.run(
                output_path=Path(output),
                music_path=music_path,
                dry_run=dry_run,
            )
        )
    except (PipelineError, CompositionError) as exc:
        print_error(str(exc))
        print_info("Run 'mindmovie generate' to retry from the last checkpoint.")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n")
        print_warning("Pipeline interrupted. State has been saved.")
        print_info("Run 'mindmovie generate' to resume.")
        raise typer.Exit(code=0)

    # --- Report result ---
    if result is None:
        if dry_run:
            print_info("Dry run complete. No assets were generated.")
        else:
            print_muted("Pipeline did not produce output.")
    else:
        print_success(f"Mind movie created: {result}")
