import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_paths_module_not_implemented_yet() -> None:
    with pytest.raises(ModuleNotFoundError, match=r"encore\.utils"):
        importlib.import_module("encore.utils.paths")


def test_path_utility_tests_fail_without_implementation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from encore.utils.paths import relative_to_root",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    combined = f"{result.stdout}\n{result.stderr}"
    assert "ModuleNotFoundError" in combined or "No module named" in combined


def test_paths_test_module_reports_not_ready() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_paths.py",
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
