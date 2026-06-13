import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _load_pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_pyproject_uses_hatchling_build_backend() -> None:
    data = _load_pyproject()
    build_system = data["build-system"]

    assert build_system["build-backend"] == "hatchling.build"
    assert "hatchling" in build_system["requires"]


def test_pyproject_hatch_wheel_packages() -> None:
    data = _load_pyproject()
    packages = data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]

    assert packages == ["src/encore"]


def test_pyproject_declares_encore_cli_entry_point() -> None:
    data = _load_pyproject()
    scripts = data["project"]["scripts"]

    assert scripts["encore"] == "encore.__main__:main"


def test_pyproject_configures_pytest() -> None:
    data = _load_pyproject()
    pytest_options = data["tool"]["pytest"]["ini_options"]

    assert pytest_options["testpaths"] == ["tests"]
    assert pytest_options["pythonpath"] == ["src"]


def test_pyproject_requires_python_3_12_or_newer() -> None:
    data = _load_pyproject()
    assert data["project"]["requires-python"] == ">=3.12"


def test_project_wheel_builds_with_hatchling() -> None:
    dist_dir = ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    result = subprocess.run(
        ["uv", "build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    try:
        assert result.returncode == 0, result.stderr or result.stdout
        wheel_paths = list(dist_dir.glob("encore-*.whl"))
        assert wheel_paths, "expected hatchling to produce an encore wheel"
    finally:
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
