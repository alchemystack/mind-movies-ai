# Mind Movie Generator

AI-powered CLI pipeline that generates personalized 3-minute visualization videos by orchestrating LLM-driven questionnaires, video generation APIs, and programmatic video composition.

## Quick Reference

```bash
# Install (editable, with dev tools)
pip install -e ".[dev]"

# Run CLI
mindmovie --help
mindmovie generate          # Full pipeline: questionnaire -> scenes -> video -> compile
mindmovie questionnaire     # Interactive goal extraction only
mindmovie render            # Generate video clips from saved scenes
mindmovie compile           # Assemble final MP4 from generated assets
mindmovie config --check    # Verify API keys and system dependencies
mindmovie clean             # Clear build directory

# Quality checks
ruff check src/ tests/      # Linting
mypy src/                   # Type checking (strict mode)
pytest tests/ -v            # All tests (116 tests)
pytest tests/unit/ -v       # Unit tests only
pytest tests/integration/ -v  # Integration tests only
```

## Required Environment

- Python >= 3.11
- FFmpeg (system dependency, required for video composition)
- API keys in `.env` (copy from `.env.example`):
  - `ANTHROPIC_API_KEY` — Claude API for questionnaire and scene generation
  - `GEMINI_API_KEY` — Google Veo API for video generation

## Architecture

The pipeline has 4 stages, each checkpointed to disk for resume capability:

```
Questionnaire -> Scene Generation -> Video Generation -> Composition
(Claude chat)    (Claude structured)  (Google Veo)       (MoviePy/FFmpeg)
```

### Package structure

```
src/mindmovie/
  api/              # External API clients (Anthropic, Veo)
    base.py         #   Protocol definitions (VideoGeneratorProtocol, LLMClientProtocol)
    anthropic_client.py  # Claude chat + structured output with retry
    veo_client.py   #   Veo video generation with polling + retry
  assets/           # Asset generation orchestration
    generator.py    #   Parallel video generation with semaphore concurrency
    video_generator.py  # Per-scene video generation wrapper
  cli/              # Typer CLI application
    app.py          #   Main app with command registration
    commands/       #   One module per CLI command
    ui/             #   Rich console, progress bars, prompts, setup wizard
  config/           # Pydantic Settings + YAML config loading
    settings.py     #   All settings models (API, Video, Movie, Music, Build)
    loader.py       #   YAML file discovery and parsing
  core/             # Business logic
    questionnaire.py  # Multi-turn Claude conversation for goal extraction
    scene_generator.py  # Goals-to-scenes via structured output
    cost_estimator.py   # Per-model cost calculation
    pipeline.py     #   Stage orchestrator with checkpoint resume
  models/           # Pydantic data models
    goals.py        #   LifeCategory, CategoryGoal, ExtractedGoals
    scenes.py       #   Scene (with affirmation validation), MindMovieSpec
  state/            # Pipeline state persistence
    models.py       #   PipelineStage enum, PipelineState model
    manager.py      #   File-based state CRUD in build/ directory
  video/            # Video composition
    composer.py     #   MoviePy-based final video assembly
    text_overlay.py #   Pillow-based text rendering (avoids ImageMagick dependency)
    effects.py      #   Crossfade transitions
```

### Key patterns

- **Protocol-based abstractions**: `VideoGeneratorProtocol` and `LLMClientProtocol` in `api/base.py` enable swappable backends
- **State checkpointing**: `StateManager` persists `PipelineState` as JSON in `build/`. Each pipeline stage is atomic — crash at any point resumes from last checkpoint
- **Retry with tenacity**: All API clients use exponential backoff for transient errors
- **Text rendering via Pillow**: `text_overlay.py` renders text to PIL Images, avoiding the ImageMagick system dependency that MoviePy's `TextClip` requires
- **Async video generation**: Veo's synchronous SDK is wrapped in `asyncio.to_thread()` for concurrent scene generation

### Configuration hierarchy

1. Environment variables (`.env`) — highest priority for API keys
2. YAML config file (`config.yaml`) — video, movie, music, build settings
3. Pydantic defaults — sensible defaults for all settings

## Testing

Tests are organized as unit (mocked) and integration (CLI + component interaction). All external API calls are mocked. Key test fixtures live in `tests/fixtures/` with sample goals, scenes, and LLM responses.

## Tool Configuration

- **ruff**: Line length 100, Python 3.11 target, select rules: E/W/F/I/B/C4/UP/ARG/SIM
- **mypy**: Strict mode with pydantic plugin; `moviepy.*` and `google.genai.*` have `ignore_missing_imports`
- **pytest**: asyncio_mode=auto, markers for `slow` and `integration`
