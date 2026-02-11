# Technical Specification: Remove Audio Generation Parameter

## Difficulty: Easy-Medium

The error is straightforward (invalid API parameter), but the `generate_audio` concept is threaded through many files: API client, protocol, settings, cost estimator, CLI config display, video generator, and tests. The changes themselves are simple deletions, but the breadth requires careful attention.

## Problem

The Veo client passes `generate_audio=True` to `types.GenerateVideosConfig()`, but the Google Gemini API does not accept this parameter:

```
ValueError: generate_audio parameter is not supported in Gemini API.
```

Veo 3.x models **natively generate audio** as part of their video output — there is no opt-in/opt-out toggle. The codebase incorrectly modeled audio generation as a separate boolean setting.

## Technical Context

- **Language**: Python 3.11+
- **Key dependencies**: google-genai SDK, Pydantic, MoviePy, Typer
- **Veo API reality**: Veo 3.x always generates video+audio. No `generate_audio` parameter exists. Cost is a single rate per second (no with/without audio tiers).

### Two distinct audio concepts in the codebase

1. **Veo native audio** (`generate_audio` boolean) — **REMOVE**: Invalid parameter passed to the Veo SDK. All related config, protocol parameters, cost tiers, and display logic must be removed.
2. **Background music mixing** (`MusicSettings`, `mix_audio()`) — **KEEP**: This is a valid MoviePy-based feature that overlays an external music file during composition. Unrelated to the Veo API error.

## Implementation Approach

Remove the `generate_audio` parameter and its dual-pricing logic from all layers. Simplify cost estimation to a single rate per model (since audio is always included). Leave background music mixing untouched.

## Source Code Changes

### Files to Modify

#### 1. `src/mindmovie/api/veo_client.py`
- **Lines 33-39**: Simplify `_COST_PER_SECOND` from `dict[str, dict[str, float]]` to `dict[str, float]` (single cost per second per model, always with audio).
- **Line 73**: Remove `generate_audio: bool` parameter from `_generate_and_poll()`.
- **Line 84**: Remove `generate_audio=generate_audio` from `GenerateVideosConfig()`.
- **Lines 92-95**: Remove audio from log message.
- **Line 144**: Remove `generate_audio: bool = True` parameter from `generate_video()`.
- **Lines 161**: Remove `generate_audio` docstring entry.
- **Line 177**: Remove `generate_audio` from `asyncio.to_thread()` call.
- **Lines 181-196**: Simplify `estimate_cost()` — remove `with_audio` parameter, use single rate.

#### 2. `src/mindmovie/api/base.py`
- **Line 23**: Remove `generate_audio: bool = True` from `VideoGeneratorProtocol.generate_video()`.
- **Line 28**: Remove `with_audio: bool` parameter from `estimate_cost()`.

#### 3. `src/mindmovie/config/settings.py`
- **Lines 51-54**: Remove `generate_audio` field from `VideoSettings`.

#### 4. `src/mindmovie/assets/video_generator.py`
- **Line 94**: Remove `generate_audio=self.settings.video.generate_audio` from `generate_video()` call.

#### 5. `src/mindmovie/core/cost_estimator.py`
- **Lines 17-27**: Simplify `VIDEO_PRICING` from `dict[str, tuple[float, float]]` to `dict[str, float]` (single cost per model).
- **Line 27**: Update `_DEFAULT_VIDEO_COST_PER_SEC` to a single float.
- **Lines 140-162**: Simplify `estimate_video_cost()` — remove audio branching logic.

#### 6. `src/mindmovie/cli/commands/config_cmd.py`
- **Line 62**: Remove "Generate Audio" from the video settings display table.

### Files NOT Modified (background music — kept as-is)

- `src/mindmovie/video/composer.py` — Background music mixing is a valid feature
- `src/mindmovie/video/effects.py` — `mix_audio()` function stays
- `src/mindmovie/config/settings.py` `MusicSettings` — Stays as-is
- `src/mindmovie/cli/commands/generate.py` — `--music` option stays
- `src/mindmovie/cli/commands/compile_cmd.py` — Music handling stays
- `src/mindmovie/core/pipeline.py` — `music_path` parameter stays
- `src/mindmovie/models/scenes.py` — `music_mood` field stays (used in scene generation prompt)
- `src/mindmovie/state/models.py` — `music_path` field stays
- `src/mindmovie/config/loader.py` — Music config loading stays

### Test Files to Update

#### 7. `tests/unit/test_veo_client.py`
- **Lines 87-88**: Remove `with_audio` parameter from `estimate_cost()` calls in `TestVeoClientCost`.
- **Line 93**: Update cost table assertion if structure changes.

#### 8. `tests/unit/test_cost_estimator.py`
- **Lines 26-28**: Remove `audio` parameter from `_settings()` helper and `VideoSettings` instantiation.
- **Line 34**: Update `test_veo_fast_no_audio` — rename and fix expected cost (now always "with audio" pricing since that's the only rate).

### No changes needed for these test files (they only reference `music_mood` or music settings, not `generate_audio`)

- `tests/unit/test_models.py` — Uses `music_mood` (kept)
- `tests/unit/test_scene_generator.py` — Asserts `music_mood` (kept)
- `tests/unit/test_state_manager.py` — Uses `music_mood` (kept)
- `tests/integration/test_composer.py` — Uses `MusicSettings` (kept)
- `tests/integration/test_error_handling.py` — Tests `--music` option (kept)
- `tests/integration/test_cli_commands.py` — Tests `--music` in help (kept)
- `tests/fixtures/sample_scenes.json` — Contains `music_mood` (kept)

## Data Model / API / Interface Changes

### Protocol change (`VideoGeneratorProtocol`)
- `generate_video()`: Remove `generate_audio` parameter
- `estimate_cost()`: Remove `with_audio` parameter

### Settings change (`VideoSettings`)
- Remove `generate_audio: bool` field

### Cost estimation change
- `VIDEO_PRICING`: From `dict[str, tuple[float, float]]` to `dict[str, float]`
- `_COST_PER_SECOND` (veo_client): From `dict[str, dict[str, float]]` to `dict[str, float]`
- Pricing uses the "with_audio" rate as the only rate (since Veo 3.x always generates audio)

### Pricing decisions
Use the **"with_audio" rates** as the single rate per model, since audio is always generated:
- `veo-3.1-fast-generate-preview`: $0.15/sec
- `veo-3.1-generate-preview`: $0.40/sec
- `veo-3.0-fast-generate-001`: $0.15/sec
- `veo-3.0-generate-001`: $0.40/sec
- `veo-2.0-generate-001`: $0.35/sec (previously had $0.00 "with_audio" and $0.35 "no_audio" — use $0.35 as the actual rate)

**Note on Veo 2.0**: The old pricing had `(0.00, 0.35)` — $0.00 with audio, $0.35 without. This is clearly wrong (Veo 2.0 doesn't have native audio). The correct single rate should be $0.35/sec.

## Verification

```bash
# 1. Run all tests
pytest tests/ -v

# 2. Type checking
mypy src/

# 3. Linting
ruff check src/ tests/

# 4. Verify no remaining references to generate_audio in src/
grep -r "generate_audio" src/
# Should return zero matches

# 5. Verify no remaining with_audio references in src/ (except any in comments if any)
grep -r "with_audio" src/
# Should return zero matches
```
