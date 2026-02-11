"""Integration tests for the compile CLI command.

Tests stage validation and error handling. No slow MoviePy encoding tests.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from mindmovie.cli.app import app
from mindmovie.models.scenes import MindMovieSpec
from mindmovie.state.manager import StateManager
from mindmovie.state.models import AssetStatus, PipelineStage

runner = CliRunner()


def _write_config(tmp_path: Path, build_dir: Path) -> Path:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        f"build:\n  build_dir: '{build_dir}'\n"
        "movie:\n  scene_duration: 5\n  title_duration: 3\n  closing_duration: 3\n"
        "  crossfade_duration: 0.3\n  fps: 24\n"
        "video:\n  resolution: '720p'\n"
    )
    return config_file


class TestCompileStageValidation:
    def test_no_state(self) -> None:
        result = runner.invoke(app, ["compile"])
        assert result.exit_code == 1
        assert "No pipeline state" in result.output

    def test_questionnaire_stage(self, tmp_path: Path) -> None:
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        state = sm.load_or_create()
        state.current_stage = PipelineStage.QUESTIONNAIRE
        sm.save(state)
        result = runner.invoke(app, ["compile", "--config", str(_write_config(tmp_path, build_dir))])
        assert result.exit_code == 1
        assert "Questionnaire not complete" in result.output

    def test_video_generation_incomplete(self, tmp_path: Path, fixtures_dir: Path) -> None:
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
        spec = MindMovieSpec.model_validate(data)
        sm.save_scenes(spec)
        sm.complete_scene_generation(spec)
        # Leave all videos PENDING
        result = runner.invoke(app, ["compile", "--config", str(_write_config(tmp_path, build_dir))])
        assert result.exit_code == 1
        assert "still pending" in result.output

    def test_already_complete(self, tmp_path: Path) -> None:
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        state = sm.load_or_create()
        state.current_stage = PipelineStage.COMPLETE
        state.output_path = "my_movie.mp4"
        sm.save(state)
        result = runner.invoke(app, ["compile", "--config", str(_write_config(tmp_path, build_dir))])
        assert result.exit_code == 0
        assert "already compiled" in result.output

    def test_missing_music_file(self, tmp_path: Path, fixtures_dir: Path) -> None:
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        sm = StateManager(str(build_dir))
        data = json.loads((fixtures_dir / "sample_scenes.json").read_text())
        spec = MindMovieSpec.model_validate(data)
        sm.save_scenes(spec)
        sm.complete_scene_generation(spec)
        for scene in spec.scenes:
            sm.update_video_status(scene.index, AssetStatus.COMPLETE, f"s{scene.index}.mp4")
        sm.advance_stage(PipelineStage.COMPOSITION)
        result = runner.invoke(
            app, ["compile", "--config", str(_write_config(tmp_path, build_dir)),
                  "--music", "/nonexistent/track.mp3"],
        )
        assert result.exit_code == 1
        assert "Music file not found" in result.output
