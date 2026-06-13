from pathlib import Path
from unittest.mock import patch

import pytest

from encore.services import launch_at_login


def test_set_launch_at_login_creates_plist(tmp_path: Path) -> None:
    plist_dir = tmp_path / "Library" / "LaunchAgents"
    app_path = "/Applications/Encore.app"

    with (
        patch.object(launch_at_login, "_get_app_bundle_path", return_value=app_path),
        patch("encore.services.launch_at_login.Path.home", return_value=tmp_path),
    ):
        launch_at_login.set_launch_at_login(True)

    plist_path = plist_dir / "com.encore.loginitem.plist"
    assert plist_path.exists()
    content = plist_path.read_text()
    assert app_path in content
    assert "<key>RunAtLoad</key>" in content


def test_set_launch_at_login_removes_plist(tmp_path: Path) -> None:
    plist_dir = tmp_path / "Library" / "LaunchAgents"
    plist_dir.mkdir(parents=True)
    plist_path = plist_dir / "com.encore.loginitem.plist"
    plist_path.write_text("old")

    with (
        patch.object(
            launch_at_login,
            "_get_app_bundle_path",
            return_value="/Applications/Encore.app",
        ),
        patch("encore.services.launch_at_login.Path.home", return_value=tmp_path),
    ):
        launch_at_login.set_launch_at_login(False)

    assert not plist_path.exists()


def test_set_launch_at_login_requires_app_bundle() -> None:
    with (
        patch.object(launch_at_login, "_get_app_bundle_path", return_value=None),
        pytest.raises(RuntimeError, match="requires running as a .app bundle"),
    ):
        launch_at_login.set_launch_at_login(True)


def test_get_app_bundle_path_finds_parent_app(tmp_path: Path) -> None:
    app = tmp_path / "Encore.app"
    exe = app / "Contents" / "MacOS" / "encore"
    exe.parent.mkdir(parents=True)

    with patch("sys.executable", str(exe)):
        assert launch_at_login._get_app_bundle_path() == str(app)


def test_get_app_bundle_path_returns_none_outside_app(tmp_path: Path) -> None:
    exe = tmp_path / "bin" / "python3"
    exe.parent.mkdir(parents=True)

    with patch("sys.executable", str(exe)):
        assert launch_at_login._get_app_bundle_path() is None
