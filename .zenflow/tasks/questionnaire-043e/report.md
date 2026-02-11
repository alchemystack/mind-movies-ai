# Step Report: Update scene generation to use appearance data

## Changes Made

### 1. `src/mindmovie/core/scene_generator.py`

**GENERATION_PROMPT** — Added two new instruction sections:
- **SUBJECT APPEARANCE**: Instructs Claude to use physical appearance data consistently in all video prompts, replacing generic "person" references with appearance-matching descriptions. Falls back to generic inclusive descriptions when no appearance is provided.
- **INITIAL VISION**: Instructs Claude to use any pre-existing vision summary as additional context for scene tone and imagery.

**`_build_user_message()`** — Added conditional blocks that include:
- `## Subject Appearance` section with `goals.appearance.description` (when present)
- `## Initial Vision Summary` section with `goals.initial_vision` (when present)

Both sections are placed between the title/scene-count header and the per-category goals, so appearance is established before category-specific content.

### 2. `tests/fixtures/sample_scenes.json`

Updated 10 of 12 video prompts to replace generic "person" references with appearance-matching descriptions derived from the `sample_goals.json` fixture ("Tall athletic man with light skin, short brown hair, and blue eyes"). Relationship scenes (index 6, 7) were left unchanged as they reference groups/couples rather than a solo subject.

### 3. `tests/unit/test_scene_generator.py`

Added two new test classes:
- **`TestBuildUserMessage`** (5 tests):
  - `test_includes_appearance_when_present` — Verifies appearance section in user message
  - `test_includes_initial_vision_when_present` — Verifies initial vision section in user message
  - `test_omits_appearance_when_absent` — Verifies no appearance section when field is None
  - `test_omits_initial_vision_when_absent` — Verifies no vision section when field is None
  - `test_appearance_precedes_categories` — Verifies ordering (appearance before categories)
- **`TestGenerationPrompt`** (2 tests):
  - `test_prompt_mentions_subject_appearance` — Verifies SUBJECT APPEARANCE in system prompt
  - `test_prompt_mentions_initial_vision` — Verifies INITIAL VISION in system prompt

## Verification

- `ruff check src/ tests/` — All checks passed
- `mypy src/` — Success: no issues found in 41 source files
- `pytest tests/ -v` — 127 passed (up from 120 before this task branch, with 7 new tests added in this step)
