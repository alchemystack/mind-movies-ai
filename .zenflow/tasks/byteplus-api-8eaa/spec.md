# Technical Specification: BytePlus Seedance Video Generation API

## Difficulty: Medium

The codebase has a clean protocol-based architecture (`VideoGeneratorProtocol`) with a single reference implementation (VeoClient). Adding a new backend is a well-scoped change: one new API client + configuration wiring + a factory for provider selection. The BytePlus SDK follows a similar async-task-and-poll pattern to Veo, reducing novelty risk.

---

## 1. Technical Context

- **Language**: Python 3.11+
- **Key dependencies**: pydantic-settings, tenacity, typer, rich
- **New dependency**: `byteplus-python-sdk-v2` (BytePlus Ark SDK, provides `byteplussdkarkruntime.Ark`)
- **Type checking**: mypy strict mode, needs `byteplussdkarkruntime.*` in `ignore_missing_imports`
- **Testing**: pytest + pytest-asyncio, all external calls mocked

### BytePlus API Summary

The BytePlus ModelArk Video Generation API is task-based and asynchronous:

1. **Create task**: `client.content_generation.tasks.create(model=..., content=[...])`
   - Returns a task object with `.id`
   - Video params are appended inline to the prompt text: `--ratio 16:9 --resolution 720p --duration 8`
   - Audio toggle via `--generateaudio true/false` appended to prompt
2. **Poll task**: `client.content_generation.tasks.get(id=task_id)`
   - Status values: `"running"`, `"succeeded"`, `"failed"`
   - On success: `result.content.video_url` contains a downloadable URL
3. **Download**: HTTP GET on the video URL, write bytes to disk

**SDK**: `pip install byteplus-python-sdk-v2`
**Client**: `from byteplussdkarkruntime import Ark`
**Base URL**: `https://ark.ap-southeast.bytepluses.com/api/v3`
**Auth**: API key via `ARK_API_KEY` env var or `Ark(api_key=...)`

### Model & Defaults (per user)

| Setting | Value |
|---------|-------|
| Model ID | `bytedance-seedance-1-5-pro` |
| Resolution | `720p` |
| Aspect Ratio | `16:9` |
| Audio | Enabled (with audio) |
| Duration | 5s (configurable via `movie.scene_duration`) |

### Pricing

BytePlus uses token-based pricing: `Tokens = (Width * Height * FPS * Duration) / 1024`

| Model | Online (USD/M tokens) | Offline (USD/M tokens) |
|-------|----------------------|----------------------|
| Seedance 1.5 Pro (with audio) | $2.4 | $1.2 |
| Seedance 1.5 Pro (no audio) | $1.2 | $0.6 |

At 720p (1280x720), 24fps, 5s with audio (offline): ~$0.13/clip. With 12 scenes: ~$1.56 total.

For cost estimation, we'll use a per-second approximation since the pipeline thinks in seconds:
- `bytedance-seedance-1-5-pro` with audio at 720p: ~$0.026/s (derived from token formula)

---

## 2. Implementation Approach

### 2.1 Provider abstraction via factory function

Rather than scattering if/elif provider selection logic across `pipeline.py` and `render.py`, introduce a factory function in `src/mindmovie/api/factory.py` that takes `Settings` and returns the correct `VideoGeneratorProtocol` implementation. This centralizes provider selection in one place.

### 2.2 New `provider` field in VideoSettings

Add a `provider: Literal["veo", "byteplus"]` field to `VideoSettings` with default `"byteplus"` (as the user wants to switch away from Veo). The `model` field becomes provider-dependent — its default will be set based on the selected provider via a model validator.

### 2.3 BytePlusClient implementation

New file `src/mindmovie/api/byteplus_client.py` following the VeoClient pattern:
- Constructor takes `api_key`, `model`, `poll_interval`, `generate_audio`
- `_generate_and_poll()` is synchronous (uses `time.sleep` polling)
- `generate_video()` is async via `asyncio.to_thread()`
- Retry with tenacity (same pattern as VeoClient)
- `estimate_cost()` uses token-based formula

### 2.4 Dynamic API key validation

`Settings.has_required_api_keys()` and `get_missing_api_keys()` need to check the correct video provider key instead of always requiring `GEMINI_API_KEY`.

---

## 3. Source Code Changes

### New Files

| File | Purpose |
|------|---------|
| `src/mindmovie/api/byteplus_client.py` | BytePlus Seedance video generation client |
| `src/mindmovie/api/factory.py` | Video client factory function |
| `tests/unit/test_byteplus_client.py` | Unit tests for BytePlusClient |

### Modified Files

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `byteplus-python-sdk-v2` dependency + mypy override |
| `src/mindmovie/config/settings.py` | Add `provider` to VideoSettings, `byteplus_api_key` to APISettings, update `has_required_api_keys`/`get_missing_api_keys` to be provider-aware |
| `src/mindmovie/api/__init__.py` | Export `BytePlusClient` and `create_video_client` |
| `src/mindmovie/core/pipeline.py` | Replace hardcoded VeoClient with factory call |
| `src/mindmovie/cli/commands/render.py` | Replace hardcoded VeoClient with factory call |
| `src/mindmovie/cli/ui/setup.py` | Add BytePlus key help, make `validate_api_keys_for_command` provider-aware |
| `src/mindmovie/cli/commands/config_cmd.py` | Display provider + BytePlus key in config output |
| `src/mindmovie/core/cost_estimator.py` | Add BytePlus pricing entries |
| `.env.example` | Add `BYTEPLUS_API_KEY` |
| `config.example.yaml` | Add `provider` field, BytePlus model examples |

---

## 4. Detailed Design

### 4.1 `src/mindmovie/config/settings.py` Changes

```python
class APISettings(BaseSettings):
    # ... existing fields ...
    byteplus_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="BYTEPLUS_API_KEY",
        description="BytePlus API key for Seedance video generation",
    )

class VideoSettings(BaseSettings):
    provider: Literal["veo", "byteplus"] = Field(
        default="byteplus",
        description="Video generation provider",
    )
    model: str = Field(
        default="bytedance-seedance-1-5-pro",
        description="Video generation model ID",
    )
    resolution: Literal["480p", "720p", "1080p", "4K"] = Field(
        default="720p",  # Changed from 1080p for BytePlus default
        description="Output resolution",
    )
    # existing aspect_ratio, max_concurrent, max_retries unchanged
    generate_audio: bool = Field(
        default=True,
        description="Generate audio with video (BytePlus Seedance 1.5+ only)",
    )

class Settings(BaseSettings):
    def has_required_api_keys(self) -> bool:
        """Check if required API keys are configured for the selected provider."""
        has_anthropic = bool(self.api.anthropic_api_key.get_secret_value())
        if self.video.provider == "veo":
            return has_anthropic and bool(self.api.gemini_api_key.get_secret_value())
        elif self.video.provider == "byteplus":
            return has_anthropic and bool(self.api.byteplus_api_key.get_secret_value())
        return has_anthropic

    def get_missing_api_keys(self) -> list[str]:
        """Return list of missing required API keys for current provider."""
        missing = []
        if not self.api.anthropic_api_key.get_secret_value():
            missing.append("ANTHROPIC_API_KEY")
        if self.video.provider == "veo" and not self.api.gemini_api_key.get_secret_value():
            missing.append("GEMINI_API_KEY")
        if self.video.provider == "byteplus" and not self.api.byteplus_api_key.get_secret_value():
            missing.append("BYTEPLUS_API_KEY")
        return missing
```

### 4.2 `src/mindmovie/api/byteplus_client.py`

```python
class BytePlusClient:
    """BytePlus Seedance video generation client implementing VideoGeneratorProtocol."""

    def __init__(
        self,
        api_key: str,
        model: str = "bytedance-seedance-1-5-pro",
        poll_interval: int = 10,
        generate_audio: bool = True,
    ) -> None:
        self.client = Ark(
            base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
            api_key=api_key,
        )
        self.model = model
        self.poll_interval = poll_interval
        self.generate_audio = generate_audio

    def _build_prompt_text(
        self, prompt: str, resolution: str, aspect_ratio: str, duration: int,
    ) -> str:
        """Append BytePlus inline parameters to the prompt text."""
        parts = [prompt]
        parts.append(f"--ratio {aspect_ratio}")
        parts.append(f"--resolution {resolution}")
        parts.append(f"--duration {duration}")
        parts.append(f"--generateaudio {'true' if self.generate_audio else 'false'}")
        return " ".join(parts)

    def _generate_and_poll(self, prompt: str, output_path: Path, ...) -> Path:
        """Synchronous create + poll + download."""
        full_prompt = self._build_prompt_text(prompt, resolution, aspect_ratio, duration)

        task = self.client.content_generation.tasks.create(
            model=self.model,
            content=[{"type": "text", "text": full_prompt}],
        )

        # Poll until complete
        import time
        task_id = task.id
        while True:
            result = self.client.content_generation.tasks.get(id=task_id)
            if result.status == "succeeded":
                break
            elif result.status == "failed":
                error_msg = getattr(result, "error", "Unknown error")
                raise RuntimeError(f"BytePlus video generation failed: {error_msg}")
            time.sleep(self.poll_interval)

        # Download video
        video_url = result.content.video_url
        import urllib.request
        output_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(video_url, str(output_path))
        return output_path

    @retry(...)  # Same tenacity config as VeoClient
    async def generate_video(self, prompt, output_path, duration=8, ...) -> Path:
        return await asyncio.to_thread(self._generate_and_poll, ...)

    def estimate_cost(self, duration: int) -> float:
        # Token formula: (W * H * FPS * duration) / 1024
        # 720p = 1280x720, 24fps
        # With audio coefficient: 0.6, price: $1.2/M tokens (offline)
        ...
```

### 4.3 `src/mindmovie/api/factory.py`

```python
def create_video_client(settings: Settings) -> VideoGeneratorProtocol:
    """Create the video generation client based on configured provider."""
    provider = settings.video.provider
    if provider == "veo":
        from .veo_client import VeoClient
        api_key = settings.api.gemini_api_key.get_secret_value()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Veo provider")
        return VeoClient(api_key=api_key, model=settings.video.model)
    elif provider == "byteplus":
        from .byteplus_client import BytePlusClient
        api_key = settings.api.byteplus_api_key.get_secret_value()
        if not api_key:
            raise ValueError("BYTEPLUS_API_KEY is required for BytePlus provider")
        return BytePlusClient(
            api_key=api_key,
            model=settings.video.model,
            generate_audio=settings.video.generate_audio,
        )
    else:
        raise ValueError(f"Unknown video provider: {provider}")
```

### 4.4 Pipeline & Render Changes

Both `pipeline.py:_run_video_generation` (lines 209-220) and `render.py` (lines 121-127) replace their hardcoded VeoClient instantiation with:

```python
from mindmovie.api import create_video_client
video_client = create_video_client(self.settings)
```

This eliminates the need for provider-specific API key checks in these files — the factory handles it.

### 4.5 Cost Estimator Changes

Add BytePlus pricing to `VIDEO_PRICING` dict in `cost_estimator.py`:

```python
VIDEO_PRICING: dict[str, float] = {
    # Veo models (per second)
    "veo-3.1-generate-preview": 0.40,
    "veo-3.1-fast-generate-preview": 0.15,
    "veo-3.0-generate-001": 0.40,
    "veo-3.0-fast-generate-001": 0.15,
    "veo-2.0-generate-001": 0.35,
    # BytePlus Seedance (per second, derived from token pricing at 720p/24fps)
    "bytedance-seedance-1-5-pro": 0.026,
}
```

### 4.6 CLI Setup/Config Changes

- `setup.py`: Add `require_byteplus` parameter to `validate_api_keys_for_command`, add `BYTEPLUS_API_KEY` to `_KEY_HELP`
- `render.py`: Replace `require_gemini=True` with provider-aware validation
- `config_cmd.py`: Show `Provider` in video settings, show BytePlus API key masked

---

## 5. Data Model / API / Interface Changes

### VideoGeneratorProtocol — No changes needed

The existing protocol signature works as-is. BytePlus `duration` is actually configurable (unlike Veo which ignores it), so the protocol's `duration` parameter becomes meaningful.

### VideoSettings model — New fields

- `provider: Literal["veo", "byteplus"]` — defaults to `"byteplus"`
- `generate_audio: bool` — defaults to `True`
- `resolution` Literal — add `"480p"` as valid option (BytePlus supports it)

### APISettings model — New field

- `byteplus_api_key: SecretStr` — loaded from `BYTEPLUS_API_KEY` env var

---

## 6. Verification Approach

1. **Linting**: `ruff check src/ tests/` — must pass
2. **Type checking**: `mypy src/` — must pass (add byteplussdkarkruntime to ignore_missing_imports)
3. **Unit tests**: New `tests/unit/test_byteplus_client.py` covering:
   - Happy path: create -> poll -> download -> return path
   - Polling: pending -> succeeded
   - Error handling: task fails -> RuntimeError
   - Retry: transient errors retried, non-transient fail fast
   - Prompt building: verify inline params appended correctly
   - Cost estimation: verify token-based calculation
4. **Existing tests**: `pytest tests/` — all 116+ existing tests must still pass
5. **Factory tests**: Test `create_video_client` returns correct client type per provider
6. **Settings tests**: Test provider-aware `has_required_api_keys` and `get_missing_api_keys`

---

## 7. Key Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| BytePlus SDK types not available for mypy | Add `byteplussdkarkruntime.*` to `ignore_missing_imports` in pyproject.toml |
| Exact prompt parameter format may differ | Build prompt helper as isolated method, easy to adjust. Log full prompt at DEBUG level. |
| Video download from URL may need auth headers | Start with simple `urllib.request.urlretrieve`; if it fails, switch to `requests` with bearer token |
| Cost estimation is approximate | Use token formula for accuracy; document that it's an estimate |
| Model ID format uncertainty | User confirmed `bytedance-seedance-1-5-pro`; can be overridden via config |
