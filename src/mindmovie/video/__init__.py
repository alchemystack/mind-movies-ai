"""Video composition module for Mind Movie Generator."""

from .composer import CompositionError, VideoComposer
from .effects import apply_fade, crossfade_concatenate, mix_audio
from .text_overlay import (
    get_resolution,
    render_affirmation_overlay,
    render_closing_card,
    render_title_card,
)

__all__ = [
    "CompositionError",
    "VideoComposer",
    "apply_fade",
    "crossfade_concatenate",
    "get_resolution",
    "mix_audio",
    "render_affirmation_overlay",
    "render_closing_card",
    "render_title_card",
]
