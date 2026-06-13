import logging
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from encore.utils.paths import is_audio_file

logger = logging.getLogger(__name__)


class _MusicRootHandler(FileSystemEventHandler):
    def __init__(
        self,
        music_root: Path,
        sync_dir: Path,
        on_audio_created: Callable[[Path], None],
        on_audio_deleted: Callable[[Path], None],
        on_playlist_changed: Callable[[Path], None],
        on_playlist_deleted: Callable[[Path], None],
    ) -> None:
        self._music_root = music_root.resolve()
        self._sync_dir = sync_dir.resolve()
        self._on_audio_created = on_audio_created
        self._on_audio_deleted = on_audio_deleted
        self._on_playlist_changed = on_playlist_changed
        self._on_playlist_deleted = on_playlist_deleted

    def _in_sync_dir(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self._sync_dir)
        except ValueError:
            return False
        return True

    def _is_playlist_file(self, path: Path) -> bool:
        return path.suffix == ".json" and not path.name.endswith(".tmp")

    def _audio_path(self, src_path: str) -> Path | None:
        path = Path(src_path)
        if not is_audio_file(path):
            return None
        try:
            path.resolve().relative_to(self._music_root)
        except ValueError:
            return None
        return path

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._in_sync_dir(path):
            if self._is_playlist_file(path):
                self._on_playlist_changed(path)
            return
        audio_path = self._audio_path(event.src_path)
        if audio_path:
            self._on_audio_created(audio_path)

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._in_sync_dir(path) and self._is_playlist_file(path):
            self._on_playlist_changed(path)

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._in_sync_dir(path):
            if path.suffix == ".json":
                self._on_playlist_deleted(path)
            return
        audio_path = self._audio_path(event.src_path)
        if audio_path:
            self._on_audio_deleted(audio_path)


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
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        handler = _MusicRootHandler(
            self._music_root,
            self._sync_dir,
            self._on_audio_created,
            self._on_audio_deleted,
            self._on_playlist_changed,
            self._on_playlist_deleted,
        )
        self._observer.schedule(handler, str(self._music_root), recursive=True)
        thread = threading.Thread(target=self._observer.start, daemon=True)
        thread.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._observer.stop()
        self._observer.join()
        self._started = False
