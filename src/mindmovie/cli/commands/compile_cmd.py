"""Compile command — assemble final video from generated assets."""

from pathlib import Path

import typer

from mindmovie.cli.ui.console import (
    console,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)
from mindmovie.cli.ui.progress import spinner
from mindmovie.config import load_settings
from mindmovie.state import PipelineStage, StateManager
from mindmovie.video import CompositionError, VideoComposer


def compile_video(
    output: str = typer.Option(
        "",
        "--output",
        "-o",
        help="Output file path for the compiled mind movie MP4.",
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
    """Assemble the final mind movie from generated video clips.

    Combines title card, scene clips with affirmation text overlays,
    optional background music, and a closing gratitude card into a
    single MP4 video.

    Requires: all scene videos to be generated first (run
    'mindmovie render' or 'mindmovie generate').

    The composition runs locally using MoviePy and FFmpeg — no API
    calls or costs involved.
    """
    settings = load_settings(config_file)
    state_manager = StateManager(settings.build_dir)

    # --- Validate pipeline state ---
    if not state_manager.exists():
        print_error(
            "No pipeline state found. "
            "Run 'mindmovie generate' to start the full pipeline."
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

    if state.current_stage == PipelineStage.VIDEO_GENERATION:
        # Videos might be done but stage not yet advanced — check assets
        if not state.all_videos_complete():
            pending = state.pending_videos()
            print_error(
                f"{len(pending)} video(s) still pending. "
                "Run 'mindmovie render' to complete them."
            )
            raise typer.Exit(code=1)
        # All videos done, advance to COMPOSITION stage
        state = state_manager.advance_stage(PipelineStage.COMPOSITION)

    if state.current_stage == PipelineStage.COMPLETE:
        print_warning("Mind movie already compiled.")
        if state.output_path:
            print_info(f"Output: {state.output_path}")
        print_info("Run 'mindmovie clean' to start fresh.")
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

    # --- Resolve output path ---
    output_path = Path(output) if output else Path(settings.output_path)

    # --- Resolve music path ---
    music_path: Path | None = None
    if music:
        music_path = Path(music)
        if not music_path.exists():
            print_error(f"Music file not found: {music_path}")
            raise typer.Exit(code=1)

    # --- Display composition summary ---
    print_header("Video Composition")
    print_info(f"Scenes: {len(spec.scenes)}")
    print_info(f"Resolution: {settings.video.resolution}")
    print_info(f"Output: {output_path}")
    if music_path:
        print_info(f"Music: {music_path}")
    elif settings.music.file_path:
        print_info(f"Music: {settings.music.file_path} (from config)")
    else:
        print_info("Music: none (video audio only)")

    total_duration = spec.total_duration(
        scene_duration=settings.movie.scene_duration,
        title_duration=settings.movie.title_duration,
        closing_duration=settings.movie.closing_duration,
    )
    print_info(f"Estimated duration: {total_duration}s")

    # --- Compose ---
    composer = VideoComposer(
        movie_settings=settings.movie,
        music_settings=settings.music,
        resolution=settings.video.resolution,
        aspect_ratio=settings.video.aspect_ratio,
    )

    try:
        with spinner("Composing mind movie..."):
            result_path = composer.compose(
                spec=spec,
                state=state,
                output_path=output_path,
                music_path=music_path,
            )
    except CompositionError as exc:
        print_error(f"Composition failed: {exc}")
        print_info(
            "Check that FFmpeg and ImageMagick are installed, "
            "and that all video files in the build directory are valid."
        )
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("\n")
        print_warning("Composition interrupted.")
        print_info("Run 'mindmovie compile' to try again.")
        raise typer.Exit(code=0)

    # --- Update state ---
    state = state_manager.load_or_create()
    state.output_path = str(result_path)
    state.current_stage = PipelineStage.COMPLETE
    state_manager.save(state)

    print_success(f"Mind movie compiled: {result_path}")
