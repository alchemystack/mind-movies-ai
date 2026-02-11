# Mind Movie Generator

AI-powered CLI pipeline that generates personalized 3-minute visualization videos. Describe your goals through an interactive questionnaire, and the tool orchestrates LLMs and video generation APIs to produce a fully composed mind movie.

## How It Works

The pipeline runs in 4 stages, each checkpointed to disk so you can resume if anything fails:

```
Questionnaire  ->  Scene Generation  ->  Video Generation       ->  Composition
(Claude chat)     (Claude structured)    (BytePlus or Google Veo)   (MoviePy/FFmpeg)
```

1. **Questionnaire** -- An interactive Claude-powered conversation extracts your life goals across categories
2. **Scene Generation** -- Goals are transformed into visual scene descriptions with affirmations via structured output
3. **Video Generation** -- Each scene is sent to the configured video provider (BytePlus Seedance by default, Google Veo as alternative) to generate video clips with native audio (concurrent generation)
4. **Composition** -- Clips are assembled into a final MP4 with text overlays, crossfades, and optional background music

## Prerequisites

- **Python** >= 3.11
- **FFmpeg** installed and available on your PATH
- **API Keys**:
  - [Anthropic API key](https://console.anthropic.com/) -- for questionnaire and scene generation (Claude)
  - [BytePlus API key](https://console.byteplus.com/) -- for video generation with Seedance (default provider)
  - [Google Gemini API key](https://aistudio.google.com/apikey) -- for video generation with Veo (alternative provider)

## Installation

```bash
# Clone the repo
git clone https://github.com/alchemystack/mind-movies-ai.git
cd mind-movies-ai

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Set up your API keys
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and BYTEPLUS_API_KEY (or GEMINI_API_KEY for Veo)
```

## Usage

```bash
# Run the full pipeline: questionnaire -> scenes -> video -> compile
mindmovie generate

# Or run individual stages
mindmovie questionnaire     # Interactive goal extraction only
mindmovie render            # Generate video clips from saved scenes
mindmovie compile           # Assemble final MP4 from generated assets

# Utilities
mindmovie config --check    # Verify API keys and system dependencies
mindmovie clean             # Clear build directory
mindmovie --help            # See all commands
```

## Configuration

Copy `config.example.yaml` to `config.yaml` to customize settings. Environment variables in `.env` take precedence over YAML values.

Key configuration options:

| Section | Setting | Default | Description |
|---------|---------|---------|-------------|
| `video` | `provider` | `byteplus` | Video provider: `byteplus` or `veo` |
| `video` | `model` | `seedance-1-5-pro-251215` | Video generation model ID |
| `video` | `resolution` | `720p` | Output resolution (480p / 720p / 1080p / 4K) |
| `video` | `generate_audio` | `true` | Generate native audio (BytePlus Seedance only) |
| `video` | `max_concurrent` | `5` | Parallel video generation limit |
| `movie` | `num_scenes` | `12` | Target number of scenes |
| `movie` | `scene_duration` | `8` | Duration per scene (seconds) |
| `movie` | `crossfade_duration` | `0.5` | Crossfade between scenes (seconds) |
| `music` | `source` | `file` | Music source (`file`, `mubert`, `musicgen`) |
| `music` | `volume` | `0.20` | Background music volume (0.0--1.0) |

## Project Structure

```
src/mindmovie/
  api/              # External API clients (Anthropic, BytePlus, Veo) + factory
  assets/           # Asset generation orchestration
  cli/              # Typer CLI application and commands
  config/           # Pydantic Settings + YAML config loading
  core/             # Business logic (questionnaire, scene gen, pipeline)
  models/           # Pydantic data models (goals, scenes)
  state/            # Pipeline state persistence and checkpointing
  video/            # Video composition, text overlays, effects
```

## Development

```bash
# Linting
ruff check src/ tests/

# Type checking (strict mode)
mypy src/

# Run all tests (158 tests, all API calls mocked)
pytest tests/ -v

# Run subsets
pytest tests/unit/ -v
pytest tests/integration/ -v
```

## Architecture Notes

- **Protocol-based abstractions** -- `VideoGeneratorProtocol` and `LLMClientProtocol` enable swappable backends
- **Multi-provider video generation** -- Factory pattern (`api/factory.py`) supports BytePlus Seedance and Google Veo; new providers can be added by implementing `VideoGeneratorProtocol` and adding a branch in the factory
- **State checkpointing** -- Each pipeline stage is atomic; crash at any point and resume from the last checkpoint
- **Retry with backoff** -- All API clients use tenacity for exponential backoff on transient errors
- **Text rendering via Pillow** -- Avoids the ImageMagick system dependency that MoviePy's `TextClip` requires
- **Async video generation** -- Both providers' synchronous SDKs are wrapped in `asyncio.to_thread()` for concurrency

## License

MIT
