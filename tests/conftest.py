"""Pytest configuration and fixtures for Mind Movie Generator tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_build_dir(tmp_path: Path) -> Path:
    """Return a temporary build directory for testing."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    return build_dir
