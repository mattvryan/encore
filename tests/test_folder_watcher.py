from pathlib import Path
from unittest.mock import MagicMock, patch

from encore.services.folder_watcher import FolderWatcher, _MusicRootHandler


class _FakeEvent:
    def __init__(self, src_path: str, *, is_directory: bool = False) -> None:
        self.src_path = src_path
        self.is_directory = is_directory


def _handler(tmp_path: Path) -> _MusicRootHandler:
    music_root = tmp_path / "Music"
    sync_dir = music_root / ".playlist-sync"
    music_root.mkdir()
    sync_dir.mkdir()
    return _MusicRootHandler(
        music_root,
        sync_dir,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )


def test_music_root_handler_created_calls_callback_for_audio_under_root(
    tmp_path: Path,
) -> None:
    handler = _handler(tmp_path)
    track = handler._music_root / "Rock" / "song.mp3"
    track.parent.mkdir(parents=True)
    track.touch()

    handler.on_created(_FakeEvent(str(track)))

    handler._on_audio_created.assert_called_once_with(track)


def test_music_root_handler_created_ignores_non_audio(tmp_path: Path) -> None:
    handler = _handler(tmp_path)
    cover = handler._music_root / "cover.jpg"
    cover.touch()

    handler.on_created(_FakeEvent(str(cover)))

    handler._on_audio_created.assert_not_called()


def test_music_root_handler_created_ignores_outside_music_root(
    tmp_path: Path,
) -> None:
    handler = _handler(tmp_path)
    outside = tmp_path / "Other" / "song.mp3"
    outside.parent.mkdir()
    outside.touch()

    handler.on_created(_FakeEvent(str(outside)))

    handler._on_audio_created.assert_not_called()


def test_music_root_handler_deleted_calls_callback(tmp_path: Path) -> None:
    handler = _handler(tmp_path)
    track = handler._music_root / "Jazz" / "Blue.mp3"
    track.parent.mkdir(parents=True)

    handler.on_deleted(_FakeEvent(str(track)))

    handler._on_audio_deleted.assert_called_once_with(track)


def test_music_root_handler_changed_ignores_tmp_files(tmp_path: Path) -> None:
    handler = _handler(tmp_path)
    tmp_file = handler._sync_dir / "road-trip.json.tmp"

    handler.on_modified(_FakeEvent(str(tmp_file)))

    handler._on_playlist_changed.assert_not_called()


def test_music_root_handler_changed_notifies_for_json_in_sync_dir(
    tmp_path: Path,
) -> None:
    handler = _handler(tmp_path)
    playlist_file = handler._sync_dir / "road-trip.json"

    handler.on_created(_FakeEvent(str(playlist_file)))

    handler._on_playlist_changed.assert_called_once_with(playlist_file)


def test_music_root_handler_deleted_notifies_for_json_in_sync_dir(
    tmp_path: Path,
) -> None:
    handler = _handler(tmp_path)
    playlist_file = handler._sync_dir / "road-trip.json"

    handler.on_deleted(_FakeEvent(str(playlist_file)))

    handler._on_playlist_deleted.assert_called_once_with(playlist_file)


@patch("encore.services.folder_watcher.Observer")
def test_folder_watcher_start_schedules_single_recursive_watch(
    mock_observer_cls: MagicMock, tmp_path: Path
) -> None:
    music_root = tmp_path / "Music"
    sync_dir = music_root / ".playlist-sync"
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

    observer.schedule.assert_called_once()
    schedule_args = observer.schedule.call_args
    assert schedule_args.args[1] == str(music_root)
    assert schedule_args.kwargs["recursive"] is True
    observer.start.assert_called_once()


@patch("encore.services.folder_watcher.Observer")
def test_folder_watcher_start_is_idempotent(
    mock_observer_cls: MagicMock, tmp_path: Path
) -> None:
    music_root = tmp_path / "Music"
    sync_dir = music_root / ".playlist-sync"
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
    watcher.start()

    observer.schedule.assert_called_once()


@patch("encore.services.folder_watcher.Observer")
def test_folder_watcher_stop_stops_observer(
    mock_observer_cls: MagicMock, tmp_path: Path
) -> None:
    music_root = tmp_path / "Music"
    sync_dir = music_root / ".playlist-sync"
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

    watcher.stop()

    observer.stop.assert_called_once()
    observer.join.assert_called_once()
