import importlib
import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _install_rumps_mock() -> ModuleType:
    rumps = ModuleType("rumps")
    rumps.notification = MagicMock()
    rumps.quit_application = MagicMock()

    class App:
        def __init__(self, name: str, quit_button: str | None = None) -> None:
            self.name = name
            self.quit_button = quit_button
            self.menu: list[str | None] | None = None

    rumps.App = App
    rumps.clicked = lambda _label: lambda fn: fn
    return rumps


def _reload_encore_app_module() -> Any:
    sys.modules.pop("encore.app", None)
    sys.modules.pop("encore.__main__", None)
    return importlib.import_module("encore.app")


@pytest.fixture
def encore_app_module() -> Any:
    rumps = _install_rumps_mock()
    with patch.dict(sys.modules, {"rumps": rumps}):
        yield _reload_encore_app_module()


def test_encore_app_configures_menu_bar(encore_app_module: Any) -> None:
    app = encore_app_module.EncoreApp()

    assert app.name == "Encore"
    assert app.quit_button is None
    assert app.menu == ["Sync Now", None, "Quit"]


def test_sync_now_shows_notification(encore_app_module: Any) -> None:
    rumps = sys.modules["rumps"]
    app = encore_app_module.EncoreApp()

    app.sync_now(None)

    rumps.notification.assert_called_once_with(
        "Encore",
        "",
        "Sync not yet implemented",
    )


def test_quit_app_quits(encore_app_module: Any) -> None:
    rumps = sys.modules["rumps"]
    app = encore_app_module.EncoreApp()

    app.quit_app(None)

    rumps.quit_application.assert_called_once()


def test_main_starts_encore_app(encore_app_module: Any) -> None:
    sys.modules.pop("encore.__main__", None)
    main_module = importlib.import_module("encore.__main__")
    mock_app = MagicMock()
    mock_app.run = MagicMock()

    with patch.object(main_module, "EncoreApp", return_value=mock_app):
        main_module.main()

    mock_app.run.assert_called_once()
