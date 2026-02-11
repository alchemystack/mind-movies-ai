"""Rich console singleton and styled output helpers for Mind Movie Generator CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Singleton console instance used throughout the CLI
console = Console()

# Style constants
BRAND_COLOR = "bright_cyan"
SUCCESS_COLOR = "green"
WARNING_COLOR = "yellow"
ERROR_COLOR = "red"
MUTED_COLOR = "dim"


def print_header(title: str) -> None:
    """Print a styled header panel for a CLI section."""
    console.print(
        Panel(
            Text(title, style=f"bold {BRAND_COLOR}", justify="center"),
            border_style=BRAND_COLOR,
            padding=(1, 2),
        )
    )


def print_success(message: str) -> None:
    """Print a success message with a prefix."""
    console.print(f"[{SUCCESS_COLOR}]\\[+][/{SUCCESS_COLOR}] {message}")


def print_warning(message: str) -> None:
    """Print a warning message with a prefix."""
    console.print(f"[{WARNING_COLOR}]\\[!][/{WARNING_COLOR}] {message}")


def print_error(message: str) -> None:
    """Print an error message with a prefix."""
    console.print(f"[{ERROR_COLOR}]\\[x][/{ERROR_COLOR}] {message}")


def print_info(message: str) -> None:
    """Print an informational message with a prefix."""
    console.print(f"[{BRAND_COLOR}]\\[*][/{BRAND_COLOR}] {message}")


def print_muted(message: str) -> None:
    """Print muted/secondary text."""
    console.print(f"[{MUTED_COLOR}]{message}[/{MUTED_COLOR}]")


def print_key_value_table(
    title: str, data: dict[str, str], title_style: str = BRAND_COLOR
) -> None:
    """Print a two-column key-value table.

    Args:
        title: Table title.
        data: Dictionary of key-value pairs to display.
        title_style: Rich style for the table title.
    """
    table = Table(title=title, title_style=title_style, show_header=False)
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(key, value)
    console.print(table)
