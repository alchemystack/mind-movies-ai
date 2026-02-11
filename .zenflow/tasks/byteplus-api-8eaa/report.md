# Factory & Pipeline Wiring — Implementation Report

## Summary

Wired up BytePlus as a video generation provider alongside the existing Veo provider. Introduced a factory function to centralize provider selection, updated the pipeline and CLI to use it, and ensured all 158 tests pass with full lint/type coverage.

## Changes Made

### New Files

- **`src/mindmovie/api/factory.py`** — Factory function `create_video_client(settings)` that reads `settings.video.provider` and returns the appropriate `VideoGeneratorProtocol` implementation. Uses lazy imports to avoid requiring both SDKs to be installed. Validates API keys eagerly with clear error messages.

- **`tests/unit/test_factory.py`** — 6 unit tests covering: BytePlus client creation, Veo client creation, missing key errors for both providers, unknown provider error, and audio setting passthrough.

### Modified Files

- **`src/mindmovie/api/__init__.py`** — Added `BytePlusClient` and `create_video_client` to public API exports.

- **`src/mindmovie/core/pipeline.py`** — Replaced hardcoded `VeoClient` import and instantiation with `create_video_client()`. Removed direct `VeoClient` import. Factory's `ValueError` is caught and re-raised as `PipelineError` to maintain the existing error contract.

- **`src/mindmovie/cli/commands/render.py`** — Replaced hardcoded `VeoClient` instantiation with `create_video_client()`. Changed `require_gemini=True` to `require_video_provider=True` for provider-aware API key validation. Added provider info to the output display.

- **`src/mindmovie/core/cost_estimator.py`** — Added `seedance-1-5-pro-251215` at `$0.026/s` to the `VIDEO_PRICING` table (derived from token formula at 720p/24fps with audio).

- **`src/mindmovie/cli/ui/setup.py`** — Added `require_byteplus` and `require_video_provider` parameters to `validate_api_keys_for_command()`. The `require_video_provider` flag dynamically checks the correct key based on `settings.video.provider`. Added `BYTEPLUS_API_KEY` entry to `_KEY_HELP` dict.

- **`src/mindmovie/cli/commands/config_cmd.py`** — Added `BYTEPLUS_API_KEY` (masked) to API keys display. Added `Provider` and `Generate Audio` fields to the video settings table.

- **`tests/integration/test_pipeline.py`** — Updated all patches from `mindmovie.core.pipeline.VeoClient` to `mindmovie.core.pipeline.create_video_client`. Added `byteplus_api_key` to the settings fixture. Renamed `test_missing_gemini_key_raises` to `test_missing_video_provider_key_raises` and added `test_missing_byteplus_key_raises`.

- **`tests/unit/test_setup.py`** — Added 6 new tests: `test_byteplus_present`, `test_byteplus_missing`, `test_video_provider_byteplus_present`, `test_video_provider_byteplus_missing`, `test_video_provider_veo_present`, `test_video_provider_veo_missing`.

## Test Results

```
158 passed in 33.78s
ruff check: All checks passed!
mypy: Success: no issues found in 43 source files
```
