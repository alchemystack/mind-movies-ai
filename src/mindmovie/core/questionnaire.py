"""Conversational goal extraction engine for Mind Movie Generator.

Runs a multi-turn conversation with Claude to guide users through
six life categories, extracting vivid visual details and emotions
that drive scene generation downstream.
"""

import json
import logging
import uuid
from typing import Any

from mindmovie.api.anthropic_client import AnthropicClient
from mindmovie.models.goals import ExtractedGoals

logger = logging.getLogger(__name__)

COMPLETION_MARKER = "[QUESTIONNAIRE_COMPLETE]"

SYSTEM_PROMPT = """\
You are a warm, empathetic life vision coach conducting a mind movie questionnaire.

ROLE: Guide users to articulate vivid, specific visions for their ideal life.

WORKFLOW:
1. Greet warmly. Explain you'll explore 6 life areas together.
2. For each area (Health, Wealth, Career, Relationships, Growth, Lifestyle):
   a. Ask ONE open-ended question about their vision
   b. Based on response, ask 1-2 follow-ups to extract VISUAL DETAILS:
      - What does it LOOK like? (setting, environment, colors)
      - What are you DOING? (specific actions, who's with you)
      - How does it FEEL? (emotions, sensations)
   c. Confirm understanding before moving to next area
3. Allow skipping areas ("skip" or "next")
4. After all areas, summarize what you heard and ask for confirmation

BEHAVIOR RULES:
- Ask ONE question at a time
- Be encouraging and supportive
- Never judge or question the feasibility of goals
- Probe for concrete, filmable details (not abstractions)
- Keep responses under 3 sentences

When user says "done" or you've covered all categories, respond with exactly:
[QUESTIONNAIRE_COMPLETE]
followed by a JSON object with this structure:
{
  "title": "optional custom title or My Vision",
  "categories": [
    {
      "category": "health",
      "vision": "user's described vision",
      "visual_details": "what it looks like",
      "actions": "what the user is doing",
      "emotions": "how it feels",
      "skipped": false
    }
  ]
}

Include all 6 categories. For skipped categories set skipped to true and use empty strings \
for other fields."""


class QuestionnaireEngine:
    """Conversational goal extraction using Claude.

    Manages a multi-turn dialogue where Claude acts as a life vision
    coach, walking the user through six life categories and extracting
    the sensory details needed for scene generation.
    """

    def __init__(
        self,
        client: AnthropicClient,
        *,
        input_fn: Any | None = None,
        output_fn: Any | None = None,
    ) -> None:
        """Initialize the questionnaire engine.

        Args:
            client: Anthropic API client for Claude interactions.
            input_fn: Callable to read user input. Defaults to console input.
                      Signature: () -> str
            output_fn: Callable to display assistant messages. Defaults to print.
                       Signature: (str) -> None
        """
        self.client = client
        self._input_fn = input_fn
        self._output_fn = output_fn
        self.messages: list[dict[str, str]] = []

    async def run(self) -> ExtractedGoals:
        """Run the interactive questionnaire and return extracted goals.

        Starts with an empty message list to let Claude greet the user,
        then loops: display Claude's response, read user input, send to
        Claude, until the completion marker is detected.

        Returns:
            ExtractedGoals parsed from Claude's final structured response.
        """
        # Kick off the conversation — Claude sends the opening greeting
        response = await self.client.chat(
            messages=[{"role": "user", "content": "Hello, help me create a mind movie."}],
            system_prompt=SYSTEM_PROMPT,
        )
        self._display(response)
        self.messages.append({"role": "user", "content": "Hello, help me create a mind movie."})
        self.messages.append({"role": "assistant", "content": response})

        # Conversation loop
        while True:
            user_input = self._read_input()
            if not user_input:
                continue

            self.messages.append({"role": "user", "content": user_input})

            response = await self.client.chat(
                messages=self.messages,
                system_prompt=SYSTEM_PROMPT,
            )

            if COMPLETION_MARKER in response:
                logger.info("Questionnaire complete — parsing goals")
                goals = self._parse_completion(response)
                return goals

            self._display(response)
            self.messages.append({"role": "assistant", "content": response})

    def _read_input(self) -> str:
        """Read user input via the configured input function."""
        if self._input_fn is not None:
            return self._input_fn()
        # Default: Rich console prompt is wired in by the CLI command
        raise RuntimeError(
            "No input function configured. "
            "Pass input_fn to QuestionnaireEngine or use the CLI command."
        )

    def _display(self, message: str) -> None:
        """Display an assistant message via the configured output function."""
        if self._output_fn is not None:
            self._output_fn(message)

    def _parse_completion(self, response: str) -> ExtractedGoals:
        """Parse the completion marker and extract goals JSON.

        The response is expected to contain ``[QUESTIONNAIRE_COMPLETE]``
        followed by a JSON object matching the ``ExtractedGoals`` schema.

        Args:
            response: Claude's response containing the completion marker and JSON.

        Returns:
            Validated ExtractedGoals model.

        Raises:
            ValueError: If the JSON cannot be found or parsed.
        """
        marker_idx = response.index(COMPLETION_MARKER)
        after_marker = response[marker_idx + len(COMPLETION_MARKER) :].strip()

        # Extract JSON — find the first { and last }
        json_start = after_marker.find("{")
        json_end = after_marker.rfind("}")
        if json_start == -1 or json_end == -1:
            raise ValueError(
                "Could not find JSON object after completion marker. "
                f"Response after marker: {after_marker[:200]}"
            )

        raw_json = after_marker[json_start : json_end + 1]

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON after completion marker: {e}") from e

        # Add conversation_id if not present
        if "conversation_id" not in data:
            data["conversation_id"] = str(uuid.uuid4())

        return ExtractedGoals.model_validate(data)
