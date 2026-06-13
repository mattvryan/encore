import logging
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from encore.utils.paths import is_audio_file

logger = logging.getLogger(__name__)


class _AudioHandler(FileSystemEventHandler):
    def __init__(
        self,
        music_root: Path,
        on_created: Callable[[Path], None],
        on_deleted: Callable[[Path], None],
    ) -> None:
        self._music_root = music_root
        self._on_created = on_created
        self._on_deleted = on_deleted

    def _to_path(self, src_path: str) -> Path | None:
        path = Path(src_path)
        if not is_audio_file(path):
            return None
        try:
            path.resolve().relative_to(self._music_root.resolve())
        except ValueError:
            return None
        return path

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = self._to_path(event.src_path)
        if path:
            self._on_created(path)

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return
        path = self._to_path(event.src_path)
        if path:
            self._on_deleted(path)


class FolderWatcher:
    def __init__(
        self,
        music_root: Path,
        sync_dir: Path,
        on_audio_created: Callable[[Path], None],
        on_audio_deleted: Callable[[Path], None],
        on_playlist_changed: Callable[[Path], None],
        on_playlist_deleted: Callable[[Path], None],
    ) -> None:
        self._music_root = music_root
        self._sync_dir = sync_dir
        self._on_audio_created = on_audio_created
        self._on_audio_deleted = on_audio_deleted
        self._on_playlist_changed = on_playlist_changed
        self._on_playlist_deleted = on_playlist_deleted
        self._observer = Observer()

    def start(self) -> None:
        audio_handler = _AudioHandler(
            self._music_root,
            self._on_audio_created,
            self._on_audio_deleted,
        )
        self._observer.schedule(audio_handler, str(self._music_root), recursive=True)
        self._observer.schedule(
            _PlaylistSyncHandler(
                self._on_playlist_changed,
                self._on_playlist_deleted,
            ),
            str(self._sync_dir),
            recursive=False,
        )
        thread = threading.Thread(target=self._observer.start, daemon=True)
        thread.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()


class _PlaylistSyncHandler(FileSystemEventHandler):
    def __init__(
        self,
        on_changed: Callable[[Path], None],
        on_deleted: Callable[[Path], None],
    ) -> None:
        self._on_changed = on_changed
        self._on_deleted = on_deleted

    def on_created(self, event) -> None:
        if not event.is_directory:
            self._handle(event.src_path)

    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._handle(event.src_path)

    def _handle(self, src_path: str) -> None:
        path = Path(src_path)
        if path.suffix == ".json" and not path.name.endswith(".tmp"):
            self._on_changed(path)

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".json":
            self._on_deleted(path)
