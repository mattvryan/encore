import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _install_rumps_mock() -> ModuleType:
    rumps = ModuleType("rumps")

    class MenuItem:
        def __init__(self, title: str, callback=None) -> None:
            self.title = title
            self.callback = callback
            self.state = False

    class Timer:
        def __init__(self, callback, interval: float) -> None:
            self.callback = callback
            self.interval = interval
            self.started = False

        def start(self) -> None:
            self.started = True

    class MenuDict(dict):
        def __getitem__(self, key: str) -> Any:
            for item in self.values():
                if isinstance(item, MenuItem) and item.title.startswith(
                    key.split(":")[0]
                ):
                    return item
                if item == key:
                    return MenuItem(key)
            return MenuItem(key)

    class App:
        def __init__(
            self,
            name: str,
            quit_button: str | None = None,
            icon: str | None = None,
        ) -> None:
            self.name = name
            self.quit_button = quit_button
            self.icon = icon
            self.menu: list[Any] | MenuDict | None = None

    rumps.App = App
    rumps.MenuItem = MenuItem
    rumps.Timer = Timer
    rumps.MenuDict = MenuDict
    rumps.notification = MagicMock()
    rumps.alert = MagicMock()
    rumps.quit_application = MagicMock()
    rumps.clicked = lambda _label: lambda fn: fn
    return rumps


def _reload_encore_app_module() -> Any:
    for mod in (
        "encore.app",
        "encore.__main__",
        "encore.services.apple_music",
        "encore.services.folder_watcher",
        "encore.services.library_import",
        "encore.services.playlist_file",
        "encore.services.retry_queue",
        "encore.services.sync_orchestrator",
        "encore.storage.mapping_store",
        "encore.settings",
    ):
        sys.modules.pop(mod, None)
    return importlib.import_module("encore.app")


@pytest.fixture
def encore_app_module() -> Any:
    rumps = _install_rumps_mock()
    mock_settings = MagicMock()
    mock_settings.music_root = None
    mock_settings.sync_dir = None
    mock_settings.launch_at_login = False

    with (
        patch.dict(sys.modules, {"rumps": rumps}),
        patch("encore.settings.Settings.load", return_value=mock_settings),
    ):
        yield _reload_encore_app_module()


def test_encore_app_configures_menu_bar(encore_app_module: Any) -> None:
    app = encore_app_module.EncoreApp()

    assert app.name == "Encore"
    assert app.quit_button is None
    assert app.icon is not None
    assert Path(app.icon).name == "encore-menubar.png"
    assert app.menu[0].title == "Status: Idle"
    assert app.menu[1] == "Sync Now"
    assert app.menu[2] == "Open Sync Folder"
    assert app.menu[3] == "Choose Music Folder..."
    assert app.menu[4].title == "Launch at Login"
    assert app.menu[5] is None
    assert app.menu[6] == "About Encore..."
    assert app.menu[7] == "Quit"
    assert app._timer.started is True


def test_sync_now_without_orchestrator_shows_alert(encore_app_module: Any) -> None:
    rumps = sys.modules["rumps"]
    app = encore_app_module.EncoreApp()

    app.sync_now(None)

    rumps.alert.assert_called_once_with("Encore", "Choose a music folder first.")


def test_open_sync_folder_without_sync_dir_shows_alert(encore_app_module: Any) -> None:
    rumps = sys.modules["rumps"]
    app = encore_app_module.EncoreApp()

    app.open_sync_folder(None)

    rumps.alert.assert_called_once_with("Encore", "Choose a music folder first.")


def test_about_shows_dialog(encore_app_module: Any) -> None:
    app = encore_app_module.EncoreApp()

    with patch("encore.app.show_about") as mock_show_about:
        app.about(None)

    mock_show_about.assert_called_once()


def test_quit_app_stops_watcher_and_quits(encore_app_module: Any) -> None:
    rumps = sys.modules["rumps"]
    app = encore_app_module.EncoreApp()
    mock_watcher = MagicMock()
    app._watcher = mock_watcher
    app._orchestrator = MagicMock()

    app.quit_app(None)

    mock_watcher.stop.assert_called_once()
    assert app._watcher is None
    assert app._orchestrator is None
    rumps.quit_application.assert_called_once()


def test_start_services_replaces_existing_watcher(encore_app_module: Any) -> None:
    app = encore_app_module.EncoreApp()
    old_watcher = MagicMock()
    app._watcher = old_watcher
    app._orchestrator = MagicMock()
    app.settings.music_root = Path("/tmp/music")

    with patch("encore.app.FolderWatcher") as mock_folder_watcher:
        mock_folder_watcher.return_value = MagicMock()
        app._start_services()

    old_watcher.stop.assert_called_once()
    mock_folder_watcher.return_value.start.assert_called_once()


def test_main_starts_encore_app(encore_app_module: Any) -> None:
    sys.modules.pop("encore.__main__", None)
    main_module = importlib.import_module("encore.__main__")
    mock_app = MagicMock()
    mock_app.run = MagicMock()

    with patch.object(main_module, "EncoreApp", return_value=mock_app):
        main_module.main()

    mock_app.run.assert_called_once()
