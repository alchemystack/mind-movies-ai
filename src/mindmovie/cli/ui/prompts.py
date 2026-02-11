"""User input prompts and confirmation dialogs for Mind Movie Generator CLI."""

import typer
from rich.panel import Panel
from rich.text import Text

from .console import BRAND_COLOR, WARNING_COLOR, console


def prompt_user_input(message: str = "> ") -> str:
    """Prompt the user for text input.

    Args:
        message: The prompt string displayed to the user.

    Returns:
        The user's input string, stripped of leading/trailing whitespace.
    """
    return console.input(f"[bold]{message}[/bold]").strip()


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask the user to confirm an action.

    Args:
        message: The confirmation question.
        default: Default answer if user just presses Enter.

    Returns:
        True if user confirmed, False otherwise.
    """
    return typer.confirm(message, default=default)


def confirm_cost(estimated_cost: float, scene_count: int) -> bool:
    """Display a cost estimate panel and ask the user to confirm.

    Shows estimated cost, scene count, and generation time before
    proceeding with API calls that incur charges.

    Args:
        estimated_cost: Estimated total cost in USD.
        scene_count: Number of scenes to generate.

    Returns:
        True if user confirmed, False otherwise.
    """
    est_minutes_low = scene_count * 2
    est_minutes_high = scene_count * 6

    content = Text()
    content.append("Scenes: ", style="bold")
    content.append(f"{scene_count}\n")
    content.append("Estimated cost: ", style="bold")
    content.append(f"${estimated_cost:.2f}\n", style=WARNING_COLOR)
    content.append("Estimated time: ", style="bold")
    content.append(f"{est_minutes_low}-{est_minutes_high} minutes\n")

    console.print(
        Panel(
            content,
            title="Generation Estimate",
            title_align="left",
            border_style=BRAND_COLOR,
        )
    )

    return typer.confirm("Proceed with generation?", default=True)
