# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification

Specification saved to `.zenflow/tasks/remove-audio-3bc8/spec.md`.

Difficulty: Easy-Medium. The fix is straightforward (remove invalid `generate_audio` parameter from Veo API calls), but the parameter is threaded through 8 source files and 2 test files.

Key decision: Veo 3.x natively generates audio — there is no opt-in toggle. Remove `generate_audio` from all layers. Keep background music mixing (`MusicSettings`, `mix_audio()`) since it's unrelated to the Veo API error.

---

### [ ] Step: Implementation

Remove `generate_audio` parameter from API layer, protocol, settings, cost estimation, CLI display, and video generator. Update affected unit tests. Verify with full test suite, mypy, and ruff.

**Source files to modify (6):**
- `src/mindmovie/api/veo_client.py` — Remove `generate_audio` param from `_generate_and_poll()`, `generate_video()`, `GenerateVideosConfig`; simplify `_COST_PER_SECOND` to single rate; simplify `estimate_cost()`
- `src/mindmovie/api/base.py` — Remove `generate_audio` from `VideoGeneratorProtocol.generate_video()`, `with_audio` from `estimate_cost()`
- `src/mindmovie/config/settings.py` — Remove `generate_audio` field from `VideoSettings`
- `src/mindmovie/assets/video_generator.py` — Remove `generate_audio=...` from `generate_video()` call
- `src/mindmovie/core/cost_estimator.py` — Simplify `VIDEO_PRICING` to single rate per model; remove audio branching in `estimate_video_cost()`
- `src/mindmovie/cli/commands/config_cmd.py` — Remove "Generate Audio" from config display

**Test files to update (2):**
- `tests/unit/test_veo_client.py` — Remove `with_audio` from cost tests; update cost table assertions
- `tests/unit/test_cost_estimator.py` — Remove `audio` param from `_settings()` helper; fix expected costs

**Verification:**
- [ ] `ruff check src/ tests/`
- [ ] `mypy src/`
- [ ] `pytest tests/ -v`
- [ ] `grep -r "generate_audio" src/` returns zero matches
- [ ] `grep -r "with_audio" src/` returns zero matches

After completion, write report to `.zenflow/tasks/remove-audio-3bc8/report.md`.
