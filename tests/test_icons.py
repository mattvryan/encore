import subprocess
import sys
from pathlib import Path

import pytest

from encore.icons import app_icon_path, menubar_icon_path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "icons"


def test_menubar_idle_icon_is_bundled() -> None:
    path = menubar_icon_path(syncing=False)
    assert path.is_file()
    assert path.name == "encore-menubar-idle.png"


def test_menubar_sync_icon_is_bundled() -> None:
    path = menubar_icon_path(syncing=True)
    assert path.is_file()
    assert path.name == "encore-menubar.png"


@pytest.mark.skipif(sys.platform != "darwin", reason="sips is macOS-only")
def test_menubar_icons_are_32_pixels_for_retina() -> None:
    for syncing in (False, True):
        result = subprocess.run(
            [
                "sips",
                "-g",
                "pixelWidth",
                "-g",
                "pixelHeight",
                str(menubar_icon_path(syncing=syncing)),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "pixelWidth: 32" in result.stdout
        assert "pixelHeight: 32" in result.stdout


def test_app_icon_icns_exists() -> None:
    path = app_icon_path()
    assert path.is_file()
    assert path.suffix == ".icns"


def test_app_source_icon_exists() -> None:
    assert (ASSETS / "encore-app-1024.png").is_file()


def test_menubar_source_icons_exist() -> None:
    assert (ASSETS / "encore-menubar-16.png").is_file()
    assert (ASSETS / "encore-menubar-idle.png").is_file()
    assert (ASSETS / "encore-menubar-idle-16.png").is_file()
