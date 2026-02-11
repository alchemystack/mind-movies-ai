"""CLI commands for Mind Movie Generator."""

from .clean import clean
from .compile_cmd import compile_video
from .config_cmd import config
from .generate import generate
from .questionnaire import questionnaire
from .render import render

__all__ = [
    "clean",
    "compile_video",
    "config",
    "generate",
    "questionnaire",
    "render",
]
