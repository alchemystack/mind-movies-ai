"""Integration tests for Mind Movie Generator CLI commands."""

from pathlib import Path

from typer.testing import CliRunner

from mindmovie.cli.app import app
from mindmovie.state import StateManager

runner = CliRunner()


class TestMainApp:
    def test_help_flag(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "mindmovie" in result.output.lower()

    def test_version_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "mindmovie version" in result.output


class TestGenerateCommand:
    def test_help(self) -> None:
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output


class TestRenderCommand:
    def test_no_state_exits_with_error(self) -> None:
        result = runner.invoke(app, ["render"])
        assert result.exit_code == 1
        assert "No pipeline state" in result.output


class TestCompileCommand:
    def test_help(self) -> None:
        result = runner.invoke(app, ["compile", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output
        assert "--music" in result.output

    def test_no_state_exits_with_error(self) -> None:
        result = runner.invoke(app, ["compile"])
        assert result.exit_code == 1
        assert "No pipeline state" in result.output


class TestConfigCommand:
    def test_displays_settings(self) -> None:
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "Video" in result.output or "video" in result.output


class TestCleanCommand:
    def test_clean_with_state(self, tmp_path: Path) -> None:
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        state = sm.load_or_create()
        sm.save(state)
        state_file = build_dir / "pipeline_state.json"
        assert state_file.exists()

        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"build:\n  build_dir: '{build_dir}'\n")

        result = runner.invoke(app, ["clean", "--force", "--config", str(config_file)])
        assert result.exit_code == 0
        assert not state_file.exists()
