"""Anthropic Claude API client for conversational and structured output interactions."""

import json
import logging
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Transient errors worth retrying (rate limits, server errors, connection issues)
_RETRYABLE_ERRORS = (
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

# Default model for all interactions
DEFAULT_MODEL = "claude-opus-4-20250514"


class AnthropicClient:
    """Claude API client with retry logic for chat and structured output.

    Implements LLMClientProtocol with two interaction modes:
    - chat(): Multi-turn conversation returning free-form text
    - generate_structured(): Single-shot JSON generation validated against a Pydantic schema
    """

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        max_tokens: int = 2048,
    ) -> str:
        """Send chat messages and get a text response.

        Args:
            messages: Conversation history in Anthropic message format
                      (list of {"role": "user"|"assistant", "content": str}).
            system_prompt: Optional system prompt for behaviour control.
            max_tokens: Maximum tokens in the response.

        Returns:
            The assistant's text response.

        Raises:
            anthropic.APIError: On non-retryable API errors.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system_prompt is not None:
            kwargs["system"] = system_prompt

        logger.debug("Sending chat request with %d messages", len(messages))
        response = await self.client.messages.create(**kwargs)

        # Extract text from the first text content block
        for block in response.content:
            if block.type == "text":
                return str(block.text)

        return ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        reraise=True,
    )
    async def generate_structured(
        self,
        messages: list[dict[str, Any]],
        schema: type[Any],
        system_prompt: str | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate structured JSON output matching a Pydantic schema.

        Uses Anthropic's tool-use mechanism to guarantee valid JSON output.
        The schema's JSON Schema representation is passed as a tool definition,
        and Claude is forced to call that tool, producing schema-conformant output.

        Args:
            messages: Conversation history.
            schema: A Pydantic model class whose JSON schema defines the output shape.
            system_prompt: Optional system prompt.
            max_tokens: Maximum tokens in the response.

        Returns:
            Parsed dictionary matching the provided schema.

        Raises:
            ValueError: If the response contains no valid structured output.
            anthropic.APIError: On non-retryable API errors.
        """
        # Build a tool definition from the Pydantic schema
        json_schema = schema.model_json_schema()
        tool_name = "structured_output"
        tool = {
            "name": tool_name,
            "description": f"Output data matching the {schema.__name__} schema.",
            "input_schema": json_schema,
        }

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": tool_name},
        }
        if system_prompt is not None:
            kwargs["system"] = system_prompt

        logger.debug(
            "Sending structured output request for schema %s",
            schema.__name__,
        )
        response = await self.client.messages.create(**kwargs)

        # Extract the tool-use block
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                result: Any = block.input
                if isinstance(result, str):
                    parsed: dict[str, Any] = json.loads(result)
                    return parsed
                return dict(result)

        raise ValueError(
            f"No structured output found in response. "
            f"Expected tool_use block with name '{tool_name}'."
        )
