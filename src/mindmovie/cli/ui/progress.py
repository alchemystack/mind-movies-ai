"""Progress bar and spinner wrappers for Mind Movie Generator CLI."""

from collections.abc import Generator
from contextlib import contextmanager

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .console import console


@contextmanager
def spinner(message: str) -> Generator[None, None, None]:
    """Display a spinner with a message while a block executes.

    Usage::

        with spinner("Generating scenes..."):
            do_slow_work()
    """
    with console.status(f"[bright_cyan]{message}[/bright_cyan]"):
        yield


def create_progress() -> Progress:
    """Create a Rich progress bar configured for asset generation tracking.

    Returns a Progress instance with spinner, description, bar, percentage,
    and estimated time remaining columns.

    Usage::

        progress = create_progress()
        with progress:
            task = progress.add_task("Generating videos", total=15)
            for i in range(15):
                do_work(i)
                progress.advance(task)
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )
