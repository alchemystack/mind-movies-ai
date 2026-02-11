"""Video transition effects for Mind Movie composition.

Provides fade-in, fade-out, and crossfade functionality using MoviePy v2's
effects API. MoviePy v2 uses `with_effects([vfx.FadeIn(...)])` instead of
v1's `fadein(...)` method.
"""

from __future__ import annotations

import logging

from moviepy import AudioFileClip, CompositeAudioClip, VideoClip, concatenate_videoclips, vfx

logger = logging.getLogger(__name__)


def apply_fade(
    clip: VideoClip,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
) -> VideoClip:
    """Apply fade-in and/or fade-out effects to a video clip.

    Args:
        clip: The video clip to apply fades to.
        fade_in: Fade-in duration in seconds (0 to disable).
        fade_out: Fade-out duration in seconds (0 to disable).

    Returns:
        The clip with fade effects applied.
    """
    effects: list[vfx.FadeIn | vfx.FadeOut] = []
    if fade_in > 0:
        effects.append(vfx.FadeIn(fade_in))
    if fade_out > 0:
        effects.append(vfx.FadeOut(fade_out))

    if effects:
        return clip.with_effects(effects)
    return clip


def crossfade_concatenate(
    clips: list[VideoClip],
    crossfade_duration: float = 0.5,
) -> VideoClip:
    """Concatenate clips with crossfade transitions between them.

    Each clip gets a fade-in at its start and a fade-out at its end.
    Clips are overlapped by ``crossfade_duration`` seconds using
    MoviePy's ``method="compose"`` concatenation with padding.

    When crossfade_duration is 0, clips are concatenated with no overlap.

    Args:
        clips: List of video clips to concatenate.
        crossfade_duration: Duration of crossfade transitions in seconds.

    Returns:
        A single concatenated clip with crossfade transitions.

    Raises:
        ValueError: If clips list is empty.
    """
    if not clips:
        raise ValueError("Cannot concatenate an empty list of clips.")

    if len(clips) == 1:
        return clips[0]

    if crossfade_duration <= 0:
        return concatenate_videoclips(clips, method="compose")

    # Apply fade effects for crossfade overlap
    faded_clips: list[VideoClip] = []
    for i, clip in enumerate(clips):
        fade_in = crossfade_duration if i > 0 else 0
        fade_out = crossfade_duration if i < len(clips) - 1 else 0
        faded_clips.append(apply_fade(clip, fade_in=fade_in, fade_out=fade_out))

    # Use negative padding to overlap clips by crossfade_duration
    return concatenate_videoclips(
        faded_clips,
        method="compose",
        padding=-crossfade_duration,
    )


def mix_audio(
    video_audio: AudioFileClip | None,
    music: AudioFileClip,
    music_volume: float = 0.20,
    duration: float | None = None,
) -> CompositeAudioClip | AudioFileClip:
    """Mix video audio with background music at the specified volume.

    If the video has no audio, returns just the background music. If it does,
    layers the music underneath the video audio.

    Args:
        video_audio: Audio from the video clips (may be None).
        music: Background music audio clip.
        music_volume: Volume multiplier for the music (0.0–1.0).
        duration: Target duration in seconds; music is trimmed/padded to fit.

    Returns:
        Mixed audio clip ready for the final video.
    """
    # Scale music volume
    scaled_music = music.with_volume_scaled(music_volume)

    # Trim or extend music to match target duration
    if duration is not None and scaled_music.duration > duration:
        scaled_music = scaled_music.subclipped(0, duration)

    if video_audio is None:
        return scaled_music

    return CompositeAudioClip([scaled_music, video_audio])
