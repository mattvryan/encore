import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

from encore.about import ABOUT_MESSAGE, show_about


def test_about_message_includes_version() -> None:
    assert "Version 0.1.0" in ABOUT_MESSAGE
    assert "Apple Music" in ABOUT_MESSAGE


def _mock_rumps() -> ModuleType:
    rumps = ModuleType("rumps")
    rumps.alert = MagicMock()
    return rumps


def test_show_about_displays_alert(tmp_path: Path) -> None:
    icon = tmp_path / "encore.icns"
    icon.write_bytes(b"")
    mock_rumps = _mock_rumps()

    with (
        patch.dict(sys.modules, {"rumps": mock_rumps}),
        patch("encore.about.app_icon_path", return_value=icon),
    ):
        show_about()

    mock_rumps.alert.assert_called_once_with(
        "Encore",
        ABOUT_MESSAGE,
        icon_path=str(icon),
    )


def test_show_about_omits_icon_when_unavailable() -> None:
    mock_rumps = _mock_rumps()

    with (
        patch.dict(sys.modules, {"rumps": mock_rumps}),
        patch("encore.about.app_icon_path") as mock_icon_path,
    ):
        mock_icon_path.return_value = MagicMock(is_file=lambda: False)

        show_about()

    mock_rumps.alert.assert_called_once_with("Encore", ABOUT_MESSAGE, icon_path=None)
