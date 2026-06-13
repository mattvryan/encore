from importlib.resources import files
from pathlib import Path


def menubar_icon_path(*, syncing: bool = False) -> Path:
    name = "encore-menubar.png" if syncing else "encore-menubar-idle.png"
    return Path(str(files("encore").joinpath(f"assets/icons/{name}")))


def app_icon_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "icons" / "encore.icns"
