# Technical Specification: Update Scene Generation Prompts

## Difficulty: Easy

Prompt-only change in a single file. No model, logic, or API changes required.

## Technical Context

- **Language**: Python 3.11+
- **Key dependency**: Anthropic Claude API (structured output via tool-use)
- **Downstream consumer**: BytePlus Seedance / Google Veo video generation APIs

## Problem Statement

The current `GENERATION_PROMPT` in `scene_generator.py` instructs Claude to create cinematic scene descriptions but lacks guidance in four critical areas:

1. **No speech constraint**: Video generation models produce poor results when prompts imply dialogue. The prompt must explicitly forbid any speech in scenes (human sounds like breathing/yelling are acceptable).

2. **Abstract concepts leak into prompts**: When users describe goals involving non-visual concepts (e.g., "solving a specific technical problem"), the LLM may output abstract descriptions that can't be visualized. The prompt must instruct the model to translate everything into strictly visual, concrete scenes.

3. **Video model limitations not accounted for**: The prompt encourages complex cinematic descriptions but doesn't account for the fact that current video generation models struggle with unusual, complex, or non-ordinary scenes. The prompt must guide Claude to write prompts that maximize the probability of a believable, photorealistic result from the video model.

4. **Emotional state underemphasized**: The user's emotional state and desire should be the primary driver of scene content, more important than literal accuracy to what the user described. The prompt must prioritize photorealism + desired emotional state as the two non-negotiable qualities of every scene.

## Implementation Approach

Modify the `GENERATION_PROMPT` string constant in `src/mindmovie/core/scene_generator.py` to add four new instruction sections that address each requirement. The new sections will be added after the existing video_prompt formula (item 2) and before the SCENE DISTRIBUTION section.

### New Sections to Add

#### NO SPEECH RULE
- Add a prominent rule stating no person may speak in any scene
- Clarify that non-verbal human sounds (yelling, breathing, laughing, cheering) are allowed
- Position this near the top of the video_prompt instructions since it's a hard constraint

#### VISUAL-ONLY SCENES
- Instruct the model to never include abstract, theoretical, or non-visual concepts in video prompts
- If a user's goal is inherently non-visual (e.g., "solve a complex algorithm"), the scene should depict a generic visual representation (e.g., person working confidently at a desk)
- The video_prompt field must describe only what a camera can see

#### VIDEO MODEL OPTIMIZATION
- Acknowledge that the video generation model has limitations with complex/unusual scenes
- Instruct Claude to write prompts that favor common, recognizable, photorealistic compositions
- Prefer simple, clear subjects and environments over elaborate multi-element scenes
- Avoid prompting for things that are hard to generate (text on screen, specific brand logos, unusual physics, crowds with specific actions)

#### EMOTIONAL PRIORITY
- Establish that photorealism and emotional authenticity are the two highest priorities for every scene
- The user's desired emotional state must be visible through facial expressions, body language, environment, and lighting
- Scene accuracy to the user's literal description is secondary to these two qualities
- Explicitly instruct that scenes must be photorealistic and believable

### Modifications to Existing Prompt Sections

The existing **video_prompt formula** (item 2, lines 28-35) should be augmented to reinforce the new constraints inline:
- Add "photorealistic" to the style keywords list
- Add a note about emotional expressiveness in subject descriptions

## Source Code Changes

### Files to Modify

| File | Change |
|------|--------|
| `src/mindmovie/core/scene_generator.py` | Modify `GENERATION_PROMPT` constant (lines 12-70) to add four new instruction sections |

### Files Potentially Affected

| File | Impact |
|------|--------|
| `tests/unit/test_scene_generator.py` | `TestGenerationPrompt` tests check for section headers. New sections should be tested similarly. No existing tests should break since we're only adding content, not removing existing sections. |

### Files NOT Changed

- `src/mindmovie/models/scenes.py` — No model changes needed
- `src/mindmovie/api/anthropic_client.py` — No API client changes
- `src/mindmovie/core/pipeline.py` — No pipeline logic changes
- `src/mindmovie/core/questionnaire.py` — No questionnaire changes
- Test fixtures (`tests/fixtures/sample_scenes.json`) — Existing fixtures remain valid

## Verification Approach

1. **Existing tests**: Run `pytest tests/unit/test_scene_generator.py -v` to confirm no regressions
2. **Existing model tests**: Run `pytest tests/unit/test_models.py -v` to confirm Scene/MindMovieSpec validation unchanged
3. **Full test suite**: Run `pytest tests/ -v` to verify no side effects
4. **Linting**: Run `ruff check src/mindmovie/core/scene_generator.py`
5. **Type checking**: Run `mypy src/mindmovie/core/scene_generator.py`
6. **Manual review**: Read the final prompt to verify it reads naturally and all four requirements are clearly expressed
