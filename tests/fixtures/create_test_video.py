"""Utility to create minimal test video files for integration tests.

Generates tiny synthetic MP4 clips using MoviePy so that tests don't
need to ship binary fixtures. Each video is a solid-color frame with
optional audio tone.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from moviepy import AudioClip, ColorClip


def create_test_video(
    output_path: Path,
    duration: float = 2.0,
    size: tuple[int, int] = (320, 180),
    fps: int = 24,
    color: tuple[int, int, int] = (100, 150, 200),
    with_audio: bool = True,
) -> Path:
    """Create a minimal test video file.

    Args:
        output_path: Where to write the MP4 file.
        duration: Video duration in seconds.
        size: Video dimensions (width, height).
        fps: Frame rate.
        color: Solid fill color (R, G, B).
        with_audio: Whether to include a silent audio track.

    Returns:
        Path to the created video file.
    """
    clip = ColorClip(size, color=color).with_duration(duration).with_fps(fps)

    if with_audio:
        # Generate a silent audio track (tiny amplitude sine wave)
        audio = AudioClip(
            lambda t: np.sin(2 * np.pi * 440 * t)[:, np.newaxis] * 0.01
            if isinstance(t, np.ndarray)
            else [[np.sin(2 * np.pi * 440 * t) * 0.01]],
            duration=duration,
            fps=44100,
        )
        clip = clip.with_audio(audio)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clip.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=fps,
        logger=None,
    )
    return output_path


def create_test_audio(
    output_path: Path,
    duration: float = 10.0,
) -> Path:
    """Create a minimal test audio file (MP3).

    Generates a quiet sine-wave tone for use as background music in tests.

    Args:
        output_path: Where to write the audio file.
        duration: Audio duration in seconds.

    Returns:
        Path to the created audio file.
    """
    audio = AudioClip(
        lambda t: np.sin(2 * np.pi * 440 * t)[:, np.newaxis] * 0.01
        if isinstance(t, np.ndarray)
        else [[np.sin(2 * np.pi * 440 * t) * 0.01]],
        duration=duration,
        fps=44100,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio.write_audiofile(str(output_path), logger=None)
    return output_path
