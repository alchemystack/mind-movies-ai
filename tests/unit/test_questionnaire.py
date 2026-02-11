"""Unit tests for the QuestionnaireEngine."""

import json
from collections import deque
from unittest.mock import AsyncMock

import pytest

from mindmovie.core.questionnaire import COMPLETION_MARKER, SYSTEM_PROMPT, QuestionnaireEngine
from mindmovie.models.goals import ExtractedGoals

SAMPLE_GOALS_JSON = json.dumps({
    "title": "My Dream Life",
    "appearance": {
        "description": "Tall athletic man with light skin, short brown hair, and blue eyes",
    },
    "initial_vision": "I want to live a life full of adventure and health.",
    "categories": [
        {"category": cat, "vision": "v", "visual_details": "d",
         "actions": "a", "emotions": "e", "skipped": False}
        for cat in ["health", "wealth", "career", "relationships", "growth", "lifestyle"]
    ],
})

SAMPLE_GOALS_JSON_NO_APPEARANCE = json.dumps({
    "title": "My Dream Life",
    "appearance": None,
    "initial_vision": None,
    "categories": [
        {"category": cat, "vision": "v", "visual_details": "d",
         "actions": "a", "emotions": "e", "skipped": False}
        for cat in ["health", "wealth", "career", "relationships", "growth", "lifestyle"]
    ],
})


def _completion(goals_json: str = SAMPLE_GOALS_JSON) -> str:
    return f"Summary!\n\n{COMPLETION_MARKER}\n{goals_json}"


def _make_engine(responses: list[str], inputs: list[str]) -> tuple[QuestionnaireEngine, list[str]]:
    client = AsyncMock()
    rq = deque(responses)
    client.chat = AsyncMock(side_effect=lambda **_: rq.popleft())
    iq = deque(inputs)
    displayed: list[str] = []
    engine = QuestionnaireEngine(
        client=client, input_fn=lambda: iq.popleft(),
        output_fn=lambda msg: displayed.append(msg),
    )
    return engine, displayed


class TestQuestionnaireFlow:
    async def test_completes_and_returns_goals(self) -> None:
        engine, _ = _make_engine(
            ["Welcome! Health?", _completion()],
            ["I want to be fit."],
        )
        goals = await engine.run()
        assert isinstance(goals, ExtractedGoals)
        assert goals.title == "My Dream Life"
        assert len(goals.categories) == 6

    async def test_empty_input_skipped(self) -> None:
        client = AsyncMock()
        rq = deque(["Welcome!", _completion()])
        client.chat = AsyncMock(side_effect=lambda **_: rq.popleft())
        iq = deque(["", "I want health."])
        engine = QuestionnaireEngine(
            client=client, input_fn=lambda: iq.popleft(), output_fn=lambda _: None,
        )
        await engine.run()
        assert client.chat.call_count == 2


class TestCompletionParsing:
    def _engine(self) -> QuestionnaireEngine:
        return QuestionnaireEngine(client=AsyncMock(), input_fn=lambda: "", output_fn=lambda _: None)

    def test_parses_valid_json(self) -> None:
        goals = self._engine()._parse_completion(_completion())
        assert goals.title == "My Dream Life"

    def test_parses_with_appearance(self) -> None:
        goals = self._engine()._parse_completion(_completion())
        assert goals.appearance is not None
        assert "athletic" in goals.appearance.description
        assert goals.initial_vision is not None

    def test_parses_without_appearance(self) -> None:
        goals = self._engine()._parse_completion(_completion(SAMPLE_GOALS_JSON_NO_APPEARANCE))
        assert goals.appearance is None
        assert goals.initial_vision is None
        assert goals.title == "My Dream Life"
        assert len(goals.categories) == 6

    def test_parses_legacy_json_without_new_fields(self) -> None:
        """Old goals JSON (without appearance/initial_vision) still parses correctly."""
        legacy_json = json.dumps({
            "title": "Legacy",
            "categories": [
                {"category": cat, "vision": "v", "visual_details": "d",
                 "actions": "a", "emotions": "e", "skipped": False}
                for cat in ["health", "wealth", "career", "relationships", "growth", "lifestyle"]
            ],
        })
        goals = self._engine()._parse_completion(_completion(legacy_json))
        assert goals.appearance is None
        assert goals.initial_vision is None
        assert goals.title == "Legacy"

    def test_raises_on_missing_json(self) -> None:
        with pytest.raises(ValueError, match="Could not find JSON"):
            self._engine()._parse_completion(f"{COMPLETION_MARKER}\nNo JSON here.")

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            self._engine()._parse_completion(f"{COMPLETION_MARKER}\n{{bad}}")


class TestSystemPrompt:
    def test_mentions_categories_and_marker(self) -> None:
        for cat in ["Health", "Wealth", "Career", "Relationships", "Growth", "Lifestyle"]:
            assert cat in SYSTEM_PROMPT
        assert COMPLETION_MARKER in SYSTEM_PROMPT

    def test_mentions_appearance_and_vision(self) -> None:
        assert "appearance" in SYSTEM_PROMPT.lower()
        assert "initial_vision" in SYSTEM_PROMPT
        assert "summary" in SYSTEM_PROMPT.lower()
        assert "hair" in SYSTEM_PROMPT.lower()
        assert "skin" in SYSTEM_PROMPT.lower()
