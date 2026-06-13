from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_app.sh"
SETUP_APP = ROOT / "setup_app.py"

EXPECTED_PLIST_KEYS = {
    "CFBundleName": "Encore",
    "CFBundleDisplayName": "Encore",
    "CFBundleIdentifier": "com.encore.app",
    "CFBundleVersion": "0.1.0",
    "LSUIElement": True,
    "NSAppleEventsUsageDescription": (
        "Encore needs to control Music to sync playlists."
    ),
}


def test_build_app_script_exists() -> None:
    assert BUILD_SCRIPT.is_file()


def test_build_app_script_runs_py2app() -> None:
    content = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert content.startswith("#!/bin/bash")
    assert "set -euo pipefail" in content
    assert "uv sync" in content
    assert "uv pip install py2app" in content
    assert "uv run python setup_app.py py2app" in content
    assert "dist/Encore.app" in content


def test_setup_app_exists() -> None:
    assert SETUP_APP.is_file()


def test_setup_app_has_expected_plist_keys() -> None:
    content = SETUP_APP.read_text(encoding="utf-8")

    for key, value in EXPECTED_PLIST_KEYS.items():
        assert f'"{key}"' in content
        if isinstance(value, bool):
            assert f'"{key}": {value}' in content
        else:
            assert f'"{key}": "{value}"' in content

    assert '"packages": ["encore", "rumps", "watchdog"]' in content
    assert '"argv_emulation": False' in content
