"""Integration tests for CLI error handling and user experience."""

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mindmovie.cli.app import app
from mindmovie.models.scenes import MindMovieSpec
from mindmovie.state import PipelineStage, StateManager

runner = CliRunner()

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load_sample_spec() -> MindMovieSpec:
    """Load sample MindMovieSpec from test fixtures."""
    data = json.loads((FIXTURES_DIR / "sample_scenes.json").read_text())
    return MindMovieSpec.model_validate(data)


def _make_config(tmp_path: Path, build_dir: Path) -> Path:
    """Create a config.yaml pointing to the given build directory."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(f"build:\n  build_dir: '{build_dir}'\n")
    return config_file


class TestConfigCheck:
    def test_config_check_missing_keys(self) -> None:
        """config --check exits 1 when API keys are missing."""
        with patch(
            "mindmovie.cli.ui.setup.check_system_dependencies", return_value=[]
        ):
            result = runner.invoke(app, ["config", "--check"])
        assert result.exit_code == 1
        assert "not set" in result.output.lower() or "ANTHROPIC_API_KEY" in result.output

    def test_config_check_all_present(self) -> None:
        """config --check exits 0 when everything is configured."""
        with (
            patch(
                "mindmovie.cli.ui.setup.check_system_dependencies", return_value=[]
            ),
            patch.dict(
                "os.environ",
                {
                    "ANTHROPIC_API_KEY": "sk-ant-test",
                    "GEMINI_API_KEY": "gk-test",
                },
            ),
        ):
            result = runner.invoke(app, ["config", "--check"])
        assert result.exit_code == 0

    def test_config_check_missing_ffmpeg(self) -> None:
        """config --check warns about missing ffmpeg."""
        with (
            patch(
                "mindmovie.cli.ui.setup.check_system_dependencies",
                return_value=["ffmpeg"],
            ),
            patch.dict(
                "os.environ",
                {
                    "ANTHROPIC_API_KEY": "sk-ant-test",
                    "GEMINI_API_KEY": "gk-test",
                },
            ),
        ):
            result = runner.invoke(app, ["config", "--check"])
        assert result.exit_code == 1
        assert "ffmpeg" in result.output.lower()


class TestRenderErrorHandling:
    def test_render_no_state(self) -> None:
        """render exits 1 with guidance when no state exists."""
        result = runner.invoke(app, ["render"])
        assert result.exit_code == 1
        assert "No pipeline state" in result.output
        assert "mindmovie generate" in result.output

    def test_render_questionnaire_incomplete(self, tmp_path: Path) -> None:
        """render exits 1 when questionnaire is not complete."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        state = sm.load_or_create()
        sm.save(state)

        config_file = _make_config(tmp_path, build_dir)
        result = runner.invoke(app, ["render", "--config", str(config_file)])
        assert result.exit_code == 1
        assert "Questionnaire not complete" in result.output

    def test_render_already_done(self, tmp_path: Path) -> None:
        """render warns when videos are already generated."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        state = sm.load_or_create()
        state.current_stage = PipelineStage.COMPLETE
        sm.save(state)

        config_file = _make_config(tmp_path, build_dir)
        result = runner.invoke(app, ["render", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "already generated" in result.output.lower()

    def test_render_dry_run(self, tmp_path: Path) -> None:
        """render --dry-run shows cost estimate without generating."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))

        spec = _load_sample_spec()
        sm.complete_scene_generation(spec)

        config_file = _make_config(tmp_path, build_dir)
        result = runner.invoke(app, ["render", "--dry-run", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "dry run" in result.output.lower()


class TestCompileErrorHandling:
    def test_compile_no_state(self) -> None:
        """compile exits 1 with guidance when no state exists."""
        result = runner.invoke(app, ["compile"])
        assert result.exit_code == 1
        assert "No pipeline state" in result.output
        assert "mindmovie generate" in result.output

    def test_compile_videos_pending(self, tmp_path: Path) -> None:
        """compile exits 1 when videos are not all generated."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))

        spec = _load_sample_spec()
        sm.complete_scene_generation(spec)

        config_file = _make_config(tmp_path, build_dir)
        result = runner.invoke(app, ["compile", "--config", str(config_file)])
        assert result.exit_code == 1
        assert "pending" in result.output.lower() or "render" in result.output.lower()

    def test_compile_music_not_found(self, tmp_path: Path) -> None:
        """compile exits 1 when music file doesn't exist."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        state = sm.load_or_create()
        state.current_stage = PipelineStage.COMPOSITION
        sm.save(state)

        # Write valid scenes JSON from fixtures
        spec = _load_sample_spec()
        sm.save_scenes(spec)

        config_file = _make_config(tmp_path, build_dir)
        result = runner.invoke(
            app,
            ["compile", "--music", "/nonexistent/music.mp3", "--config", str(config_file)],
        )
        assert result.exit_code == 1
        assert "Music file not found" in result.output


class TestGenerateErrorHandling:
    def test_generate_help_text(self) -> None:
        """generate --help shows comprehensive help."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--output" in result.output
        assert "--music" in result.output
        assert "--resume" in result.output

    def test_generate_music_not_found(self) -> None:
        """generate exits 1 when music file doesn't exist."""
        with (
            patch(
                "mindmovie.cli.ui.setup.check_system_dependencies", return_value=[]
            ),
            patch.dict(
                "os.environ",
                {
                    "ANTHROPIC_API_KEY": "sk-ant-test",
                    "GEMINI_API_KEY": "gk-test",
                },
            ),
        ):
            result = runner.invoke(
                app, ["generate", "--music", "/nonexistent/music.mp3"]
            )
        assert result.exit_code == 1
        assert "Music file not found" in result.output

    def test_generate_already_complete(self, tmp_path: Path) -> None:
        """generate exits cleanly when pipeline is already complete."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        state = sm.load_or_create()
        state.current_stage = PipelineStage.COMPLETE
        state.output_path = "test_output.mp4"
        sm.save(state)

        config_file = _make_config(tmp_path, build_dir)
        result = runner.invoke(app, ["generate", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "already complete" in result.output.lower()
        assert "mindmovie clean" in result.output.lower()


class TestQuestionnaireErrorHandling:
    def test_questionnaire_help_text(self) -> None:
        """questionnaire --help shows comprehensive help."""
        result = runner.invoke(app, ["questionnaire", "--help"])
        assert result.exit_code == 0
        assert "life categories" in result.output.lower() or "goal" in result.output.lower()


class TestHelpText:
    """Verify all commands have useful --help output."""

    def test_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "generate" in result.output
        assert "questionnaire" in result.output
        assert "render" in result.output
        assert "compile" in result.output
        assert "config" in result.output
        assert "clean" in result.output

    def test_render_help(self) -> None:
        result = runner.invoke(app, ["render", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--config" in result.output

    def test_compile_help(self) -> None:
        result = runner.invoke(app, ["compile", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--music" in result.output

    def test_config_help(self) -> None:
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "--check" in result.output

    def test_clean_help(self) -> None:
        result = runner.invoke(app, ["clean", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output
