from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_documents_app_launch() -> None:
    readme = README.read_text(encoding="utf-8")

    assert readme.startswith("# Encore")
    assert "uv sync" in readme
    assert "uv run encore" in readme


def test_readme_documents_runtime_requirements() -> None:
    readme = README.read_text(encoding="utf-8")

    assert "macOS 13+" in readme
    assert "Apple Music with Automation permission granted to Encore" in readme
    assert "Shared Dropbox music folder on each Mac" in readme
