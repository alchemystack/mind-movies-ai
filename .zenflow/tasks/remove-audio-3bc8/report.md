# Implementation Report: Remove Audio Generation Parameter

## What Was Implemented

Removed the invalid `generate_audio` parameter that was being passed to the Google Veo API's `GenerateVideosConfig`. Veo 3.x models natively generate audio as part of their video output — there is no opt-in/opt-out toggle. The codebase incorrectly modeled this as a boolean setting.

### Changes Made (8 files)

**Source files (6):**

1. **`src/mindmovie/api/veo_client.py`** — Removed `generate_audio` parameter from `_generate_and_poll()` and `generate_video()`. Removed it from `GenerateVideosConfig()` constructor call. Simplified `_COST_PER_SECOND` from `dict[str, dict[str, float]]` to `dict[str, float]` (single rate per model). Simplified `estimate_cost()` to remove `with_audio` parameter. Updated docstrings.

2. **`src/mindmovie/api/base.py`** — Removed `generate_audio: bool = True` from `VideoGeneratorProtocol.generate_video()` and `with_audio: bool` from `estimate_cost()`.

3. **`src/mindmovie/config/settings.py`** — Removed `generate_audio: bool` field from `VideoSettings`.

4. **`src/mindmovie/assets/video_generator.py`** — Removed `generate_audio=self.settings.video.generate_audio` kwarg from the `generate_video()` call.

5. **`src/mindmovie/core/cost_estimator.py`** — Simplified `VIDEO_PRICING` from `dict[str, tuple[float, float]]` to `dict[str, float]`. Removed audio branching logic in `estimate_video_cost()`.

6. **`src/mindmovie/cli/commands/config_cmd.py`** — Removed "Generate Audio" row from the video settings display table.

**Test files (2):**

7. **`tests/unit/test_veo_client.py`** — Updated `test_cost_estimation` to call `estimate_cost(8)` without `with_audio` parameter. Removed the second assertion that tested no-audio pricing.

8. **`tests/unit/test_cost_estimator.py`** — Removed `audio` parameter from `_settings()` helper. Renamed `test_veo_fast_no_audio` to `test_veo_fast_cost` and updated expected cost from $9.60 to $14.40 (now using the single $0.15/sec rate).

### What Was Intentionally Kept

- **Background music mixing** (`MusicSettings`, `mix_audio()`, `--music` CLI option) — This is a valid MoviePy-based feature for overlaying external music files during composition. Unrelated to the Veo API error.
- **`music_mood` field** in `MindMovieSpec` — Used in the scene generation prompt.
- **`music_path`** in pipeline state and CLI commands.

## How the Solution Was Tested

1. **`ruff check src/ tests/`** — All checks passed
2. **`mypy src/`** — No issues found in 41 source files
3. **`pytest tests/ -v`** — All 116 tests passed (19.54s)
4. **`grep generate_audio src/`** — Zero matches (fully removed)
5. **`grep with_audio src/`** — Only one match: `composer.py:273` using MoviePy's `VideoClip.with_audio()` method for background music mixing (not related to Veo API)

## Pricing Impact

The cost estimation now uses a single rate per model (the "with audio" rate, since audio is always included):

| Model | Old (no audio) | Old (with audio) | New (single rate) |
|-------|---------------|-------------------|-------------------|
| veo-3.1-fast | $0.10/sec | $0.15/sec | $0.15/sec |
| veo-3.1 | $0.30/sec | $0.40/sec | $0.40/sec |
| veo-3.0-fast | $0.10/sec | $0.15/sec | $0.15/sec |
| veo-3.0 | $0.30/sec | $0.40/sec | $0.40/sec |
| veo-2.0 | $0.35/sec | $0.00/sec | $0.35/sec |

For the default config (12 scenes x 8s, veo-3.1-fast): **$9.60 -> $14.40**

## Challenges

None significant. The change was mechanically straightforward — removing a parameter from a call chain across 6 source files and updating 2 test files. The main consideration was correctly distinguishing between the invalid Veo API `generate_audio` parameter and the legitimate MoviePy background music mixing feature.
