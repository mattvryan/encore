import json
from pathlib import Path
from unittest.mock import patch

from encore.constants import PLAYLIST_SYNC_DIR
from encore.settings import Settings


def test_default_settings(tmp_path: Path) -> None:
    settings_dir = tmp_path / "Encore"
    settings_path = settings_dir / "settings.json"

    with (
        patch("encore.settings.SETTINGS_DIR", settings_dir),
        patch("encore.settings.SETTINGS_PATH", settings_path),
    ):
        settings = Settings()

        assert settings.music_root is None
        assert settings.launch_at_login is False
        assert settings.sync_dir is None
        assert settings.state_path == settings_dir / "sync_state.json"


def test_sync_dir_derived_from_music_root(tmp_path: Path) -> None:
    music_root = tmp_path / "Dropbox" / "Music"
    settings = Settings(music_root=music_root)

    assert settings.sync_dir == music_root / PLAYLIST_SYNC_DIR


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    settings_dir = tmp_path / "Encore"
    settings_path = settings_dir / "settings.json"
    music_root = tmp_path / "Dropbox" / "Music"

    with (
        patch("encore.settings.SETTINGS_DIR", settings_dir),
        patch("encore.settings.SETTINGS_PATH", settings_path),
    ):
        Settings(music_root=music_root, launch_at_login=True).save()
        loaded = Settings.load()

    assert loaded.music_root == music_root
    assert loaded.launch_at_login is True
    assert json.loads(settings_path.read_text()) == {
        "music_root": str(music_root),
        "launch_at_login": True,
    }


def test_load_returns_defaults_when_missing(tmp_path: Path) -> None:
    settings_dir = tmp_path / "Encore"
    settings_path = settings_dir / "settings.json"

    with (
        patch("encore.settings.SETTINGS_DIR", settings_dir),
        patch("encore.settings.SETTINGS_PATH", settings_path),
    ):
        loaded = Settings.load()

    assert loaded.music_root is None
    assert loaded.launch_at_login is False
