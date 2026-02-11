"""Text rendering utilities for video overlays and title cards.

Uses Pillow for text rendering to avoid the ImageMagick system dependency
that MoviePy's TextClip requires. Generates PIL Images that can be converted
to MoviePy ImageClip objects for compositing.
"""

from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Default resolution for 1080p 16:9 output
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080

# Text style defaults matching spec requirements
DEFAULT_FONT_SIZE = 50
TITLE_FONT_SIZE = 90
CLOSING_FONT_SIZE = 60
STROKE_WIDTH = 2
MAX_LINE_WIDTH_RATIO = 0.85  # Max text width as fraction of frame width


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font at the given size, falling back to the Pillow default.

    Attempts to load Arial (or DejaVu Sans on Linux) at the requested size.
    Falls back gracefully to Pillow's built-in bitmap font if no TrueType
    fonts are found.

    Args:
        size: Font size in points.
        bold: Whether to prefer a bold variant.

    Returns:
        A Pillow font object.
    """
    # Common sans-serif fonts across platforms
    candidates: list[str] = []
    if bold:
        candidates.extend([
            "arialbd.ttf", "Arial Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    candidates.extend([
        "arial.ttf", "Arial.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ])

    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue

    logger.warning("No TrueType font found; falling back to Pillow default bitmap font.")
    return ImageFont.load_default(size)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within a pixel width.

    Args:
        text: The text to wrap.
        font: Font used for width measurement.
        max_width: Maximum line width in pixels.

    Returns:
        List of wrapped lines.
    """
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current_line = words[0]

    for word in words[1:]:
        test_line = f"{current_line} {word}"
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def render_title_card(
    title: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    bg_color: tuple[int, int, int] = (0, 0, 0),
    text_color: tuple[int, int, int] = (255, 255, 255),
    font_size: int = TITLE_FONT_SIZE,
) -> Image.Image:
    """Render a title card as a PIL Image.

    Creates a solid-color background with centered title text.

    Args:
        title: Title text to display.
        width: Image width in pixels.
        height: Image height in pixels.
        bg_color: Background color RGB tuple.
        text_color: Text color RGB tuple.
        font_size: Title font size in points.

    Returns:
        PIL Image of the title card.
    """
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    font = _load_font(font_size, bold=True)

    max_text_width = int(width * MAX_LINE_WIDTH_RATIO)
    lines = _wrap_text(title, font, max_text_width)

    # Calculate total text block height
    line_heights: list[int] = []
    for line in lines:
        bbox = font.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = int(font_size * 0.4)
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    y_start = (height - total_height) // 2

    y = y_start
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        draw.text((x, y), line, fill=text_color, font=font)
        y += line_heights[i] + line_spacing

    return image


def render_closing_card(
    affirmation: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    bg_color: tuple[int, int, int] = (0, 0, 0),
    text_color: tuple[int, int, int] = (255, 215, 0),  # Gold
    font_size: int = CLOSING_FONT_SIZE,
) -> Image.Image:
    """Render a closing gratitude card as a PIL Image.

    Similar to the title card but with gold text by default, matching
    the spec's closing card style.

    Args:
        affirmation: Closing affirmation text.
        width: Image width in pixels.
        height: Image height in pixels.
        bg_color: Background color RGB tuple.
        text_color: Text color RGB tuple (default: gold).
        font_size: Font size in points.

    Returns:
        PIL Image of the closing card.
    """
    return render_title_card(
        title=affirmation,
        width=width,
        height=height,
        bg_color=bg_color,
        text_color=text_color,
        font_size=font_size,
    )


def render_affirmation_overlay(
    text: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    font_size: int = DEFAULT_FONT_SIZE,
    text_color: tuple[int, int, int] = (255, 255, 255),
    stroke_color: tuple[int, int, int] = (0, 0, 0),
    stroke_width: int = STROKE_WIDTH,
    y_position: float = 0.85,
) -> Image.Image:
    """Render an affirmation text overlay as a transparent PNG.

    Creates an RGBA image with transparent background and white text with
    black stroke, positioned near the bottom of the frame. This is designed
    to be composited over a video clip.

    Args:
        text: Affirmation text to render.
        width: Image width in pixels.
        height: Image height in pixels.
        font_size: Font size in points.
        text_color: Text color RGB tuple.
        stroke_color: Stroke/outline color RGB tuple.
        stroke_width: Stroke width in pixels.
        y_position: Vertical position as fraction of height (0.0 = top, 1.0 = bottom).

    Returns:
        PIL RGBA Image with transparent background and rendered text.
    """
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _load_font(font_size, bold=True)

    max_text_width = int(width * MAX_LINE_WIDTH_RATIO)
    lines = _wrap_text(text, font, max_text_width)

    # Calculate line dimensions
    line_heights: list[int] = []
    for line in lines:
        bbox = font.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = int(font_size * 0.3)
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)

    # Position text block at y_position, adjusting so the center of the
    # text block lands at the target y coordinate
    y_center = int(height * y_position)
    y = y_center - total_height // 2

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2

        # Draw stroke (outline) by rendering text offset in each direction
        if stroke_width > 0:
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text(
                        (x + dx, y + dy),
                        line,
                        fill=(*stroke_color, 255),
                        font=font,
                    )

        # Draw main text
        draw.text((x, y), line, fill=(*text_color, 255), font=font)
        y += line_heights[i] + line_spacing

    return image


def get_resolution(
    resolution: str, aspect_ratio: str = "16:9"
) -> tuple[int, int]:
    """Convert resolution string to pixel dimensions.

    Args:
        resolution: Resolution identifier ("720p", "1080p", or "4K").
        aspect_ratio: Aspect ratio ("16:9" or "9:16").

    Returns:
        Tuple of (width, height) in pixels.

    Raises:
        ValueError: If resolution is not recognized.
    """
    resolutions_16_9: dict[str, tuple[int, int]] = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "4K": (3840, 2160),
    }

    if resolution not in resolutions_16_9:
        raise ValueError(
            f"Unknown resolution '{resolution}'. Supported: {', '.join(resolutions_16_9)}"
        )

    w, h = resolutions_16_9[resolution]
    if aspect_ratio == "9:16":
        return (h, w)
    return (w, h)
