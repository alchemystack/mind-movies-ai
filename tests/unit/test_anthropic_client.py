"""Unit tests for Anthropic API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from mindmovie.api import AnthropicClient
from mindmovie.models import MindMovieSpec


def _text_block(text: str) -> MagicMock:
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _tool_block(name: str, data: dict) -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = data
    return b


def _response(blocks: list, stop: str = "end_turn") -> MagicMock:
    r = MagicMock()
    r.content = blocks
    r.stop_reason = stop
    return r


class TestChat:
    @pytest.fixture
    def client(self) -> AnthropicClient:
        return AnthropicClient(api_key="test")

    async def test_returns_text(self, client: AnthropicClient) -> None:
        with patch.object(
            client.client.messages, "create",
            new_callable=AsyncMock, return_value=_response([_text_block("Hi")]),
        ):
            assert await client.chat(messages=[{"role": "user", "content": "x"}]) == "Hi"

    async def test_passes_system_prompt(self, client: AnthropicClient) -> None:
        create = AsyncMock(return_value=_response([_text_block("R")]))
        with patch.object(client.client.messages, "create", create):
            await client.chat(messages=[{"role": "user", "content": "x"}], system_prompt="S")
            assert create.call_args.kwargs["system"] == "S"


class TestStructured:
    @pytest.fixture
    def client(self) -> AnthropicClient:
        return AnthropicClient(api_key="test")

    async def test_returns_dict(self, client: AnthropicClient) -> None:
        with patch.object(
            client.client.messages, "create",
            new_callable=AsyncMock,
            return_value=_response([_tool_block("structured_output", {"title": "T"})], "tool_use"),
        ):
            r = await client.generate_structured(
                messages=[{"role": "user", "content": "g"}], schema=MindMovieSpec,
            )
            assert r["title"] == "T"

    async def test_raises_on_no_tool_use(self, client: AnthropicClient) -> None:
        with patch.object(
            client.client.messages, "create",
            new_callable=AsyncMock, return_value=_response([_text_block("text")]),
        ), pytest.raises(ValueError, match="No structured output"):
            await client.generate_structured(
                messages=[{"role": "user", "content": "g"}], schema=MindMovieSpec,
            )


class TestRetry:
    @pytest.fixture
    def client(self) -> AnthropicClient:
        return AnthropicClient(api_key="test")

    async def test_retries_rate_limit(self, client: AnthropicClient) -> None:
        create = AsyncMock(side_effect=[
            anthropic.RateLimitError(
                message="x", response=MagicMock(status_code=429, headers={}), body=None,
            ),
            _response([_text_block("ok")]),
        ])
        with patch.object(client.client.messages, "create", create):
            assert await client.chat(messages=[{"role": "user", "content": "x"}]) == "ok"
            assert create.call_count == 2

    async def test_no_retry_auth_error(self, client: AnthropicClient) -> None:
        create = AsyncMock(side_effect=anthropic.AuthenticationError(
            message="x", response=MagicMock(status_code=401, headers={}), body=None,
        ))
        with patch.object(client.client.messages, "create", create), pytest.raises(anthropic.AuthenticationError):
            await client.chat(messages=[{"role": "user", "content": "x"}])
        assert create.call_count == 1
