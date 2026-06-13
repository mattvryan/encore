import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _load_pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _dependency_base_names(dependencies: list[str]) -> set[str]:
    names: set[str] = set()
    for dep in dependencies:
        base = dep.split(";", 1)[0].strip()
        name = base.split("[", 1)[0].strip()
        for operator in (">=", "==", "!=", "<=", "<", "~="):
            if operator in name:
                name = name.split(operator, 1)[0].strip()
                break
        names.add(name)
    return names


def test_uv_project_files_exist() -> None:
    assert PYPROJECT.is_file()
    assert (ROOT / "uv.lock").is_file()
    assert (ROOT / "src" / "encore" / "__init__.py").is_file()


def test_pyproject_declares_encore_package() -> None:
    data = _load_pyproject()
    assert data["project"]["name"] == "encore"


def test_pyproject_declares_runtime_dependencies() -> None:
    data = _load_pyproject()
    dep_names = _dependency_base_names(data["project"]["dependencies"])
    assert "rumps" in dep_names
    assert "watchdog" in dep_names


def test_pyproject_declares_pytest_dev_dependency() -> None:
    data = _load_pyproject()
    dev_dep_names = _dependency_base_names(data["dependency-groups"]["dev"])
    assert "pytest" in dev_dep_names


def test_encore_package_is_importable() -> None:
    import encore

    assert encore.__name__ == "encore"


def test_watchdog_is_importable() -> None:
    from watchdog import events

    assert events.FileSystemEvent is not None


def test_rumps_is_importable_on_macos() -> None:
    if sys.platform != "darwin":
        return

    import rumps

    assert rumps is not None
