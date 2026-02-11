"""Video composition engine for Mind Movie Generator.

Assembles generated scene videos, text overlays, background music, and
title/closing cards into the final mind movie MP4. This is the core of
Phase 4 in the pipeline.

Composition structure:
    [Title Card] → [Scene 1] → [Scene 2] → ... → [Scene N] → [Closing Card]

Each scene clip has an affirmation text overlay. All clips are joined
with crossfade transitions. Background music is mixed at configurable
volume underneath the video's native audio track.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip

from mindmovie.config.settings import MovieSettings, MusicSettings
from mindmovie.models.scenes import MindMovieSpec, Scene
from mindmovie.state.models import PipelineState

from .effects import crossfade_concatenate, mix_audio
from .text_overlay import (
    get_resolution,
    render_affirmation_overlay,
    render_closing_card,
    render_title_card,
)

logger = logging.getLogger(__name__)


class CompositionError(Exception):
    """Raised when video composition fails."""


class VideoComposer:
    """Assembles the final mind movie from generated assets.

    Takes individual scene video files, overlays affirmation text, adds
    title and closing cards, mixes in background music, and encodes the
    result as an MP4 file.

    Args:
        movie_settings: Scene duration, FPS, crossfade, and card settings.
        music_settings: Music source, file path, and volume.
        resolution: Output resolution string ("720p", "1080p", or "4K").
        aspect_ratio: Output aspect ratio ("16:9" or "9:16").
    """

    def __init__(
        self,
        movie_settings: MovieSettings,
        music_settings: MusicSettings,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
    ) -> None:
        self.movie_settings = movie_settings
        self.music_settings = music_settings
        self.resolution = resolution
        self.aspect_ratio = aspect_ratio
        self._width, self._height = get_resolution(resolution, aspect_ratio)

    def _create_title_card(self, title: str) -> ImageClip:
        """Create the opening title card clip.

        Args:
            title: Title text to display.

        Returns:
            An ImageClip of the specified title duration.
        """
        image = render_title_card(
            title=title,
            width=self._width,
            height=self._height,
        )
        return (
            ImageClip(np.array(image))
            .with_duration(self.movie_settings.title_duration)
            .with_fps(self.movie_settings.fps)
        )

    def _create_closing_card(self, affirmation: str) -> ImageClip:
        """Create the closing gratitude card clip.

        Args:
            affirmation: Closing affirmation text.

        Returns:
            An ImageClip of the specified closing duration.
        """
        image = render_closing_card(
            affirmation=affirmation,
            width=self._width,
            height=self._height,
        )
        return (
            ImageClip(np.array(image))
            .with_duration(self.movie_settings.closing_duration)
            .with_fps(self.movie_settings.fps)
        )

    def _create_scene_clip(self, scene: Scene, video_path: Path) -> CompositeVideoClip:
        """Create a single scene clip with affirmation text overlay.

        Loads the generated video file, trims to the configured scene
        duration, and composites the affirmation text on top.

        Args:
            scene: Scene data with affirmation text.
            video_path: Path to the generated video file.

        Returns:
            CompositeVideoClip with text overlay.

        Raises:
            CompositionError: If the video file cannot be loaded.
        """
        if not video_path.exists():
            raise CompositionError(f"Video file not found: {video_path}")

        try:
            video = VideoFileClip(str(video_path))
        except Exception as exc:
            raise CompositionError(
                f"Failed to load video for scene {scene.index}: {exc}"
            ) from exc

        # Trim to configured scene duration (video may be longer or shorter)
        target_duration = self.movie_settings.scene_duration
        if video.duration > target_duration:
            video = video.subclipped(0, target_duration)
        actual_duration = min(video.duration, target_duration)

        # Render affirmation overlay
        overlay_image = render_affirmation_overlay(
            text=scene.affirmation,
            width=self._width,
            height=self._height,
        )
        overlay_clip = (
            ImageClip(np.array(overlay_image))
            .with_duration(actual_duration)
        )

        return CompositeVideoClip(
            [video, overlay_clip],
            size=(self._width, self._height),
        )

    def _resolve_video_paths(
        self, spec: MindMovieSpec, state: PipelineState
    ) -> dict[int, Path]:
        """Map scene indices to their video file paths from pipeline state.

        Args:
            spec: Mind movie specification.
            state: Current pipeline state with asset paths.

        Returns:
            Dictionary mapping scene index to video file Path.

        Raises:
            CompositionError: If any required video file is missing.
        """
        paths: dict[int, Path] = {}
        missing: list[int] = []

        for scene in spec.scenes:
            asset = state.get_asset(scene.index)
            if asset is None or asset.video_path is None:
                missing.append(scene.index)
                continue
            path = Path(asset.video_path)
            if not path.exists():
                missing.append(scene.index)
                continue
            paths[scene.index] = path

        if missing:
            raise CompositionError(
                f"Missing video files for scenes: {missing}. "
                "Run 'mindmovie render' to generate them."
            )

        return paths

    def compose(
        self,
        spec: MindMovieSpec,
        state: PipelineState,
        output_path: Path,
        music_path: Path | None = None,
    ) -> Path:
        """Compose the final mind movie from all assets.

        Assembles title card, scene clips with overlays, closing card,
        applies crossfade transitions, mixes background music, and
        encodes the final MP4.

        Args:
            spec: Mind movie specification with scenes and metadata.
            state: Pipeline state containing video file paths.
            output_path: Where to write the final MP4 file.
            music_path: Path to background music file (overrides settings).

        Returns:
            Path to the final composed video file.

        Raises:
            CompositionError: If composition fails at any step.
        """
        logger.info("Starting mind movie composition")

        # Resolve video file paths
        video_paths = self._resolve_video_paths(spec, state)

        # Build clip sequence
        clips = []

        # 1. Title card
        logger.info("Creating title card: %s", spec.title)
        title_clip = self._create_title_card(spec.title)
        clips.append(title_clip)

        # 2. Scene clips with overlays
        for scene in spec.scenes:
            logger.info(
                "Compositing scene %d: %s", scene.index, scene.affirmation
            )
            scene_clip = self._create_scene_clip(scene, video_paths[scene.index])
            clips.append(scene_clip)

        # 3. Closing card
        logger.info("Creating closing card: %s", spec.closing_affirmation)
        closing_clip = self._create_closing_card(spec.closing_affirmation)
        clips.append(closing_clip)

        # 4. Concatenate with crossfade transitions
        logger.info(
            "Concatenating %d clips with %.1fs crossfade",
            len(clips),
            self.movie_settings.crossfade_duration,
        )
        final = crossfade_concatenate(
            clips,
            crossfade_duration=self.movie_settings.crossfade_duration,
        )

        # 5. Mix background music if available
        effective_music_path = music_path
        if effective_music_path is None and self.music_settings.file_path:
            candidate = Path(self.music_settings.file_path)
            if candidate.exists():
                effective_music_path = candidate

        if effective_music_path is not None and effective_music_path.exists():
            logger.info("Mixing background music: %s", effective_music_path)
            try:
                music_audio = AudioFileClip(str(effective_music_path))
                mixed_audio = mix_audio(
                    video_audio=final.audio,
                    music=music_audio,
                    music_volume=self.music_settings.volume,
                    duration=final.duration,
                )
                final = final.with_audio(mixed_audio)
            except Exception as exc:
                logger.warning(
                    "Failed to load background music, continuing without it: %s",
                    exc,
                )
        else:
            logger.info("No background music configured; using video audio only.")

        # 6. Write final output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Encoding final video: %s (%d fps, %.1fs duration)",
            output_path,
            self.movie_settings.fps,
            final.duration,
        )

        try:
            final.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                fps=self.movie_settings.fps,
                threads=4,
                preset="medium",
                logger=None,  # Suppress moviepy progress bar (we use Rich)
            )
        except Exception as exc:
            raise CompositionError(f"Failed to encode final video: {exc}") from exc

        logger.info("Mind movie composed successfully: %s", output_path)
        return output_path
