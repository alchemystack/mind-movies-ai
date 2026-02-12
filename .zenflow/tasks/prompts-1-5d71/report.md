# Implementation Report: Update Scene Generation Prompts

## What Was Implemented

### 1. Overhauled `GENERATION_PROMPT` in `scene_generator.py`

The system prompt that drives Claude's structured output for scene generation was substantially rewritten. The new prompt addresses four user-requested constraints and incorporates sophisticated video generation prompting techniques:

**New constraint sections added:**

| Section | Purpose |
|---------|---------|
| ABSOLUTELY NO SPEECH | Hard ban on any person speaking/talking in any scene; non-verbal sounds allowed |
| VISUAL-ONLY — NO ABSTRACT CONCEPTS | Forces scene prompts to describe only what a camera can see; abstract goals get translated to concrete visuals |
| KEEP IT SIMPLE AND ACHIEVABLE | Guides prompts toward simple compositions (1-2 subjects, common environments) that video models can reliably render |
| EMOTIONAL EXPRESSIVENESS (HIGHEST PRIORITY) | Establishes photorealism + emotional authenticity as the two non-negotiable scene qualities |

**Video generation sophistication techniques integrated:**

- **Camera-first approach**: Front-load camera setup, lens specs, and movement before scene content
- **Focal length as a realism lever**: Use specific lens specs (e.g., "85mm, f/1.8") instead of vague "close-up"
- **Light source physics**: Describe direction, quality, and interaction rather than mood words
- **Motion anchored to physics**: Ground movement in real forces (wind, gravity, inertia)
- **Film stock references**: Use specific color science targets (Kodak Vision3, Fujifilm Eterna) for organic color
- **Deliberate micro-imperfections**: Include rack focus, chromatic aberration, overexposure to signal real footage
- **Subject count discipline**: Limit to 1-2 people maximum for temporal consistency

### 2. Added `name` field to `Scene` model

Added a required `name` field to the `Scene` Pydantic model (`scenes.py:15-19`) — a unique, descriptive identifier (3-60 chars) like `"coastal_sunrise_run"` or `"garden_meditation"`. This allows users to identify saved scenes by name rather than just numeric index.

The `GENERATION_PROMPT` was updated to instruct Claude to generate these names (item 1 in the scene specification).

### 3. Updated all dependent files

- **`tests/fixtures/sample_scenes.json`**: Added `name` fields to all 12 fixture scenes
- **`tests/unit/test_models.py`**: Updated `_make_scene()` and `_make_spec()` helpers with `name`
- **`tests/unit/test_state_manager.py`**: Updated `_make_scenes()` helper with `name`
- **`tests/integration/test_composer.py`**: Updated `_make_spec()` and individual Scene constructors with `name`
- **`tests/unit/test_scene_generator.py`**: Added 6 new tests for prompt section presence

## Files Modified

| File | Lines Changed | Nature |
|------|---------------|--------|
| `src/mindmovie/core/scene_generator.py` | ~130 lines (prompt rewrite) | `GENERATION_PROMPT` constant fully rewritten |
| `src/mindmovie/models/scenes.py` | +5 lines | New `name` field on `Scene` model |
| `tests/fixtures/sample_scenes.json` | +12 lines | `name` field added to each scene |
| `tests/unit/test_scene_generator.py` | +18 lines | 6 new prompt section tests |
| `tests/unit/test_models.py` | 2 lines changed | `name` added to test helpers |
| `tests/unit/test_state_manager.py` | 1 line changed | `name` added to test helper |
| `tests/integration/test_composer.py` | 3 lines changed | `name` added to Scene constructors |

## How the Solution Was Tested

1. **Full test suite**: `pytest tests/ -v` — **168 passed, 0 failed**
2. **Linting**: `ruff check src/ tests/` — All checks passed
3. **Type checking**: `mypy src/` — Success, no issues in 43 source files
4. **New test coverage**: 6 new tests in `TestGenerationPrompt` verify all critical prompt sections exist:
   - `test_prompt_forbids_speech` — asserts "NO SPEECH" present
   - `test_prompt_requires_visual_only` — asserts "VISUAL-ONLY" present
   - `test_prompt_addresses_video_model_achievability` — asserts "KEEP IT SIMPLE AND ACHIEVABLE" present
   - `test_prompt_prioritizes_emotion` — asserts "EMOTIONAL EXPRESSIVENESS" present
   - `test_prompt_requires_photorealism` — asserts "PHOTOREALISTIC" present
   - `test_prompt_references_camera_technique` — asserts "CAMERA-FIRST" present

## Challenges Encountered

1. **Stale `.pyc` cache**: After editing `scene_generator.py`, the first test run imported a cached version of the old prompt. Resolved by reinstalling the package in editable mode (`pip install -e .`), which forced a fresh import.

2. **Prompt length management**: The new prompt is substantially longer (~130 lines vs ~60). Used Python line continuation (`\`) throughout to keep logical lines readable while avoiding unnecessary whitespace in the actual string sent to Claude. This is important because excess whitespace wastes tokens in the API call.
