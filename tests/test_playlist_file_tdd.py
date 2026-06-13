import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_playlist_models_not_implemented_yet() -> None:
    with pytest.raises(ModuleNotFoundError, match=r"encore\.models"):
        importlib.import_module("encore.models.playlist")


def test_playlist_file_store_not_implemented_yet() -> None:
    with pytest.raises(ModuleNotFoundError, match=r"encore\.(models|services)"):
        importlib.import_module("encore.services.playlist_file")


def test_playlist_import_fails_without_implementation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from encore.services.playlist_file import PlaylistFileStore",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    combined = f"{result.stdout}\n{result.stderr}"
    assert "ModuleNotFoundError" in combined or "No module named" in combined


def test_playlist_file_tests_not_ready() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_playlist_file.py",
            "-v",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTEST_ADDOPTS": ""},
    )

    assert result.returncode != 0
    combined = f"{result.stdout}\n{result.stderr}"
    assert (
        "skipped" in combined
        or "ModuleNotFoundError" in combined
        or "No module named" in combined
    )
