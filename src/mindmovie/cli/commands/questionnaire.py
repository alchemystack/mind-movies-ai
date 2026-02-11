"""Questionnaire command — interactive goal extraction."""

import asyncio

import anthropic
import typer

from mindmovie.api.anthropic_client import AnthropicClient
from mindmovie.cli.ui.console import (
    console,
    print_error,
    print_header,
    print_info,
    print_success,
)
from mindmovie.cli.ui.prompts import prompt_user_input
from mindmovie.cli.ui.setup import validate_api_keys_for_command
from mindmovie.config import load_settings
from mindmovie.core.questionnaire import QuestionnaireEngine
from mindmovie.state.manager import StateManager


def questionnaire(
    config_file: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration YAML file.",
    ),
) -> None:
    """Run the interactive goal extraction questionnaire.

    An AI life vision coach guides you through 6 life categories
    (Health, Wealth, Career, Relationships, Growth, Lifestyle) to
    extract your personal vision and goals. These are used to generate
    the scenes for your mind movie.

    Type "skip" to skip a category, or "done" to finish early.
    Goals are saved to the build directory for use by subsequent
    pipeline stages.
    """
    settings = load_settings(config_file)

    # Validate Anthropic API key with helpful guidance
    if not validate_api_keys_for_command(settings, require_anthropic=True):
        raise typer.Exit(code=1)

    print_header("Mind Movie Questionnaire")
    print_info(
        "I'll guide you through 6 life areas to create your personalized mind movie."
    )
    print_info('Type "skip" to skip a category, or "done" to finish early.\n')

    client = AnthropicClient(
        api_key=settings.api.anthropic_api_key.get_secret_value(),
        model=settings.api.anthropic_model,
    )
    state_mgr = StateManager(build_dir=settings.build_dir)

    def _display_assistant(message: str) -> None:
        console.print(f"\n[bright_cyan]Coach:[/bright_cyan] {message}\n")

    engine = QuestionnaireEngine(
        client=client,
        input_fn=prompt_user_input,
        output_fn=_display_assistant,
    )

    try:
        goals = asyncio.run(engine.run())
    except KeyboardInterrupt:
        console.print("\n")
        print_info("Questionnaire interrupted. No goals were saved.")
        raise typer.Exit(code=0)
    except anthropic.NotFoundError as exc:
        print_error(
            f"Anthropic model not found: {exc}. "
            "Check the configured model name (ANTHROPIC_MODEL or config.yaml)."
        )
        raise typer.Exit(code=1)
    except anthropic.AuthenticationError:
        print_error(
            "Invalid ANTHROPIC_API_KEY. "
            "Check your key at https://console.anthropic.com/settings/keys"
        )
        raise typer.Exit(code=1)
    except anthropic.RateLimitError:
        print_error(
            "Anthropic API rate limit reached. "
            "Wait a moment and try again, or check your plan limits."
        )
        raise typer.Exit(code=1)
    except (anthropic.APIConnectionError, anthropic.APITimeoutError):
        print_error(
            "Could not connect to the Anthropic API. "
            "Check your internet connection and try again."
        )
        raise typer.Exit(code=1)
    except ValueError as e:
        print_error(f"Failed to parse questionnaire results: {e}")
        print_info("This can happen if the AI response was malformed. Try again.")
        raise typer.Exit(code=1)

    # Save goals via state manager
    state_mgr.complete_questionnaire(goals)
    print_success(
        f"Goals saved! {goals.category_count} categories extracted."
    )
    print_info(f"Title: {goals.title}")
    print_info(f"Build directory: {settings.build_dir}")
    print_info("Run 'mindmovie generate' to continue with the full pipeline.")
