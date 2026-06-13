from pathlib import Path
from unittest.mock import MagicMock, patch

from encore.services.folder_watcher import (
    FolderWatcher,
    _AudioHandler,
    _PlaylistSyncHandler,
)


class _FakeEvent:
    def __init__(self, src_path: str, *, is_directory: bool = False) -> None:
        self.src_path = src_path
        self.is_directory = is_directory


def test_audio_handler_created_calls_callback_for_audio_under_root(
    tmp_path: Path,
) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Rock" / "song.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    on_created = MagicMock()
    handler = _AudioHandler(music_root, on_created, MagicMock())

    handler.on_created(_FakeEvent(str(track)))

    on_created.assert_called_once_with(track)


def test_audio_handler_created_ignores_non_audio(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    cover = music_root / "cover.jpg"
    cover.touch()
    on_created = MagicMock()
    handler = _AudioHandler(music_root, on_created, MagicMock())

    handler.on_created(_FakeEvent(str(cover)))

    on_created.assert_not_called()


def test_audio_handler_created_ignores_outside_music_root(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    outside = tmp_path / "Other" / "song.mp3"
    outside.parent.mkdir()
    outside.touch()
    on_created = MagicMock()
    handler = _AudioHandler(music_root, on_created, MagicMock())

    handler.on_created(_FakeEvent(str(outside)))

    on_created.assert_not_called()


def test_audio_handler_deleted_calls_callback(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Jazz" / "Blue.mp3"
    track.parent.mkdir(parents=True)
    on_deleted = MagicMock()
    handler = _AudioHandler(music_root, MagicMock(), on_deleted)

    handler.on_deleted(_FakeEvent(str(track)))

    on_deleted.assert_called_once_with(track)


def test_playlist_handler_changed_ignores_tmp_files(tmp_path: Path) -> None:
    on_changed = MagicMock()
    handler = _PlaylistSyncHandler(on_changed, MagicMock())
    tmp_file = tmp_path / "road-trip.json.tmp"

    handler.on_modified(_FakeEvent(str(tmp_file)))

    on_changed.assert_not_called()


def test_playlist_handler_changed_notifies_for_json(tmp_path: Path) -> None:
    on_changed = MagicMock()
    handler = _PlaylistSyncHandler(on_changed, MagicMock())
    playlist_file = tmp_path / "road-trip.json"

    handler.on_created(_FakeEvent(str(playlist_file)))

    on_changed.assert_called_once_with(playlist_file)


def test_playlist_handler_deleted_notifies_for_json(tmp_path: Path) -> None:
    on_deleted = MagicMock()
    handler = _PlaylistSyncHandler(MagicMock(), on_deleted)
    playlist_file = tmp_path / "road-trip.json"

    handler.on_deleted(_FakeEvent(str(playlist_file)))

    on_deleted.assert_called_once_with(playlist_file)


@patch("encore.services.folder_watcher.Observer")
def test_folder_watcher_start_schedules_handlers(
    mock_observer_cls: MagicMock, tmp_path: Path
) -> None:
    music_root = tmp_path / "Music"
    sync_dir = tmp_path / ".playlist-sync"
    music_root.mkdir()
    sync_dir.mkdir()
    observer = MagicMock()
    mock_observer_cls.return_value = observer
    watcher = FolderWatcher(
        music_root,
        sync_dir,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )

    watcher.start()

    assert observer.schedule.call_count == 2
    observer.start.assert_called_once()


@patch("encore.services.folder_watcher.Observer")
def test_folder_watcher_stop_stops_observer(
    mock_observer_cls: MagicMock, tmp_path: Path
) -> None:
    music_root = tmp_path / "Music"
    sync_dir = tmp_path / ".playlist-sync"
    music_root.mkdir()
    sync_dir.mkdir()
    observer = MagicMock()
    mock_observer_cls.return_value = observer
    watcher = FolderWatcher(
        music_root,
        sync_dir,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )

    watcher.stop()

    observer.stop.assert_called_once()
    observer.join.assert_called_once()
