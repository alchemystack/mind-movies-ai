"""Render command — generate video assets from saved scenes."""

import asyncio

import typer

from mindmovie.assets import AssetGenerator
from mindmovie.cli.ui.console import (
    console,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)
from mindmovie.cli.ui.progress import create_progress
from mindmovie.cli.ui.setup import validate_api_keys_for_command
from mindmovie.config import load_settings
from mindmovie.core.cost_estimator import CostEstimator
from mindmovie.state import PipelineStage, StateManager


def render(
    config_file: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration YAML file.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show cost estimate for pending videos without generating.",
    ),
) -> None:
    """Generate video clips from saved scene descriptions.

    Reads the scene specification produced by the questionnaire and scene
    generation stages, then generates a video clip for each scene using the
    configured video provider (default: BytePlus Seedance 1.5 Pro).

    Videos are generated in parallel (up to --max-concurrent) with automatic
    retry on transient failures. Progress is saved after each clip, so you
    can safely interrupt and resume later.

    Requires: completed questionnaire and scene generation (run
    'mindmovie generate' or 'mindmovie questionnaire' first).
    """
    settings = load_settings(config_file)
    state_manager = StateManager(settings.build_dir)

    # --- Verify pipeline state ---
    if not state_manager.exists():
        print_error(
            "No pipeline state found. "
            "Run 'mindmovie generate' to start the full pipeline, "
            "or 'mindmovie questionnaire' to begin with goal extraction."
        )
        raise typer.Exit(code=1)

    state = state_manager.load_or_create()

    if state.current_stage == PipelineStage.QUESTIONNAIRE:
        print_error(
            "Questionnaire not complete. "
            "Run 'mindmovie questionnaire' first."
        )
        raise typer.Exit(code=1)

    if state.current_stage == PipelineStage.SCENE_GENERATION:
        print_error(
            "Scene generation not complete. "
            "Run 'mindmovie generate' to complete scene generation first."
        )
        raise typer.Exit(code=1)

    if state.current_stage in (PipelineStage.COMPOSITION, PipelineStage.COMPLETE):
        print_warning("All videos already generated. Nothing to render.")
        print_info("Run 'mindmovie compile' to assemble the final video.")
        return

    # --- Load scenes ---
    try:
        spec = state_manager.load_scenes()
    except FileNotFoundError:
        print_error(
            "Scenes file not found in build directory. "
            "Run 'mindmovie clean' and start over with 'mindmovie generate'."
        )
        raise typer.Exit(code=1)

    pending_count = len(state.pending_videos())
    total_count = len(spec.scenes)

    if pending_count == 0:
        print_success("All scene videos already generated.")
        print_info("Run 'mindmovie compile' to assemble the final video.")
        return

    # --- Cost estimate ---
    estimator = CostEstimator(settings)
    breakdown = estimator.estimate(spec)

    print_header("Video Generation")
    print_info(f"Generating {pending_count} of {total_count} scene videos")
    print_info(f"Provider: {settings.video.provider}")
    print_info(f"Model: {settings.video.model}")
    print_info(f"Resolution: {settings.video.resolution}")
    print_info(f"Max concurrent: {settings.video.max_concurrent}")
    console.print()
    console.print(breakdown.format_summary())

    if dry_run:
        console.print()
        print_info("Dry run complete. No videos were generated.")
        return

    # --- Validate API key (after showing cost so user sees what they'd pay) ---
    if not validate_api_keys_for_command(settings, require_video_provider=True):
        raise typer.Exit(code=1)

    # --- Create video client ---
    from mindmovie.api.factory import create_video_client

    video_client = create_video_client(settings)

    # --- Create orchestrator ---
    asset_generator = AssetGenerator(
        video_client=video_client,
        state_manager=state_manager,
        settings=settings,
    )

    # --- Run generation with progress bar ---
    try:
        progress = create_progress()
        with progress:
            task_id = progress.add_task("Generating videos", total=pending_count)

            def on_scene_complete() -> None:
                progress.advance(task_id)

            summary = asyncio.run(
                asset_generator.generate_all(spec, progress_callback=on_scene_complete)
            )
    except KeyboardInterrupt:
        console.print("\n")
        print_warning("Video generation interrupted. Progress has been saved.")
        print_info("Run 'mindmovie render' to resume from where you left off.")
        raise typer.Exit(code=0)

    # --- Display results ---
    if summary.all_succeeded:
        print_success(f"All {summary.total} videos generated successfully!")
        print_info("Run 'mindmovie compile' to assemble the final video.")
    else:
        print_warning(summary.format_summary())
        if summary.failed:
            print_info("Run 'mindmovie render' again to retry failed scenes.")
