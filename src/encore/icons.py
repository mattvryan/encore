from importlib.resources import files
from pathlib import Path


def menubar_icon_path() -> Path:
    return Path(str(files("encore").joinpath("assets/icons/encore-menubar.png")))


def app_icon_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "icons" / "encore.icns"
