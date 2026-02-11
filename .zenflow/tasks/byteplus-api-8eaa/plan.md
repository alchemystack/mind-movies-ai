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
<!-- chat-id: a4b83ef5-88b3-43cb-99e3-2c698024249a -->

Assessed difficulty as **medium**. Spec saved to `.zenflow/tasks/byteplus-api-8eaa/spec.md`.

---

### [x] Step: Configuration & Settings
<!-- chat-id: 4b5ddff2-0f81-4a64-a77a-12e22cf6d7c2 -->
<!-- depends-on: Technical Specification -->

Update the settings layer to support provider selection and BytePlus API key.

1. Add `byteplus_api_key: SecretStr` to `APISettings` in `src/mindmovie/config/settings.py`
2. Add `provider: Literal["veo", "byteplus"]` field (default `"byteplus"`) and `generate_audio: bool` (default `True`) to `VideoSettings`
3. Add `"480p"` to the `resolution` Literal (BytePlus supports it)
4. Update defaults: `model` to `"seedance-1-5-pro-251215"`, `resolution` to `"720p"`
5. Make `has_required_api_keys()` and `get_missing_api_keys()` provider-aware
6. Add `BYTEPLUS_API_KEY` to `.env.example`
7. Update `config.example.yaml` with `provider` field and BytePlus options
8. Add `byteplus-python-sdk-v2` to `pyproject.toml` dependencies
9. Add `byteplussdkarkruntime.*` to mypy `ignore_missing_imports` in `pyproject.toml`

---

### [x] Step: BytePlusClient Implementation
<!-- depends-on: Configuration & Settings -->

Create the BytePlus video generation client with tests.

1. Create `src/mindmovie/api/byteplus_client.py`:
   - `BytePlusClient` class with `__init__(api_key, model, poll_interval, generate_audio)`
   - `_build_prompt_text()` helper to append inline params (`--ratio`, `--resolution`, `--duration`, `--generateaudio`)
   - `_generate_and_poll()` synchronous method: create task -> poll status -> download video to disk
   - `generate_video()` async method with tenacity retry decorator, delegates via `asyncio.to_thread()`
   - `estimate_cost()` using token-based pricing formula
2. Create `tests/unit/test_byteplus_client.py`:
   - Test happy path (create -> poll -> download -> return path)
   - Test polling (pending -> succeeded)
   - Test failed task -> RuntimeError
   - Test retry on transient errors (ConnectionError, TimeoutError)
   - Test no retry on ValueError
   - Test prompt building (inline params appended correctly)
   - Test cost estimation
3. Run `ruff check src/ tests/` and `mypy src/`
4. Run `pytest tests/` — all tests must pass

---

### [ ] Step: Factory & Pipeline Wiring
<!-- depends-on: BytePlusClient Implementation -->

Wire up provider selection via factory function, update pipeline and CLI.

1. Create `src/mindmovie/api/factory.py` with `create_video_client(settings) -> VideoGeneratorProtocol`
2. Update `src/mindmovie/api/__init__.py` to export `BytePlusClient` and `create_video_client`
3. Update `src/mindmovie/core/pipeline.py`:
   - Replace hardcoded VeoClient instantiation (lines 209-220) with `create_video_client()`
   - Remove direct VeoClient import at top of file
   - Remove provider-specific API key check (factory handles it)
4. Update `src/mindmovie/cli/commands/render.py`:
   - Replace hardcoded VeoClient instantiation (lines 121-127) with `create_video_client()`
   - Replace `validate_api_keys_for_command(settings, require_gemini=True)` with provider-aware validation
5. Update `src/mindmovie/core/cost_estimator.py`:
   - Add `"seedance-1-5-pro-251215": 0.026` to `VIDEO_PRICING`
6. Update `src/mindmovie/cli/ui/setup.py`:
   - Add `require_byteplus` param to `validate_api_keys_for_command`
   - Add `BYTEPLUS_API_KEY` entry to `_KEY_HELP` dict
7. Update `src/mindmovie/cli/commands/config_cmd.py`:
   - Show `Provider` in video settings table
   - Show `BYTEPLUS_API_KEY` (masked) in API keys section
8. Write tests for factory function (correct client type per provider, error on missing key)
9. Run `ruff check src/ tests/` and `mypy src/`
10. Run `pytest tests/ -v` — all tests (old + new) must pass
11. Write report to `.zenflow/tasks/byteplus-api-8eaa/report.md`
