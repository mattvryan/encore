import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from encore.models.playlist import Playlist, PlaylistTrack
from encore.models.sync_state import PlaylistSyncState
from encore.services.apple_music import (
    AppleMusicError,
    AppleMusicService,
    MusicPlaylist,
)
from encore.services.library_import import LibraryImportService
from encore.services.playlist_diff import diff_track_lists
from encore.services.playlist_file import PlaylistFileStore
from encore.services.retry_queue import RetryQueue
from encore.storage.mapping_store import MappingStore
from encore.utils.paths import resolve_relative_path

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    def __init__(
        self,
        music_root: Path,
        apple_music: AppleMusicService,
        playlist_store: PlaylistFileStore,
        mapping_store: MappingStore,
        library_import: LibraryImportService,
        retry_queue: RetryQueue,
    ) -> None:
        self._music_root = music_root
        self._apple_music = apple_music
        self._playlist_store = playlist_store
        self._mapping_store = mapping_store
        self._library_import = library_import
        self._retry_queue = retry_queue
        self._exhausted_count = 0

    @property
    def exhausted_count(self) -> int:
        return self._exhausted_count

    def sync_all(self) -> None:
        logger.info("Starting sync")
        allowed = self._playlist_store.allowed_names()
        if allowed is not None:
            logger.info("Playlist allow-list active (%d name(s))", len(allowed))
        self._apple_music.ensure_running()
        with self._apple_music.preserve_user_focus():
            self.sync_music_to_files()
            self.sync_files_to_music()
            self._process_retry_queue()
        logger.info("Sync complete")

    def sync_music_to_files(self) -> None:
        music_playlists = self._apple_music.list_playlists()
        logger.info("Checking %d playlist(s) in Music", len(music_playlists))
        for music_playlist in music_playlists:
            if not self._is_playlist_allowed(music_playlist.name):
                logger.info(
                    "Skipping playlist music→file: %s (not in allow-list)",
                    music_playlist.name,
                )
                continue
            logger.info(
                "Syncing playlist music→file: %s (id=%s)",
                music_playlist.name,
                music_playlist.persistent_id,
            )
            try:
                tracks = self._apple_music.get_playlist_tracks(music_playlist)
            except AppleMusicError as exc:
                logger.warning(
                    "Skipping playlist music→file: %s (id=%s): %s",
                    music_playlist.name,
                    music_playlist.persistent_id,
                    exc,
                )
                continue
            relative_paths = [t.relative_path for t in tracks if t.relative_path]
            music_hash = _hash_paths(relative_paths)
            state = self._mapping_store.get_playlist(music_playlist.persistent_id)
            if state and state.music_hash == music_hash:
                logger.info("Playlist unchanged music→file: %s", music_playlist.name)
                continue
            playlist_id = state.playlist_id if state else str(uuid.uuid4())
            playlist = Playlist(
                id=playlist_id,
                name=music_playlist.name,
                updated_at=datetime.now(UTC),
                tracks=[PlaylistTrack(relative_path=p) for p in relative_paths],
            )
            existing = self._playlist_store.find_by_id(playlist_id)
            if existing and existing.updated_at > playlist.updated_at:
                logger.info("Skipping music→file for %s; file is newer", playlist.name)
                continue
            self._playlist_store.write(playlist)
            self._mapping_store.upsert_playlist(
                PlaylistSyncState(
                    playlist_id=playlist_id,
                    name=playlist.name,
                    music_hash=music_hash,
                    file_hash=_hash_paths(relative_paths),
                    last_synced_at=datetime.now(UTC),
                )
            )
            logger.info(
                "Synced playlist music→file: %s (%d tracks)",
                playlist.name,
                len(relative_paths),
            )

    def sync_files_to_music(self) -> None:
        playlists = self._playlist_store.list_all()
        logger.info("Checking %d playlist file(s)", len(playlists))
        for playlist in playlists:
            self._apply_playlist_to_music(playlist)

    def apply_playlist_file(self, path: Path) -> None:
        data = json.loads(path.read_text())
        playlist = Playlist.from_dict(data)
        self._apply_playlist_to_music(playlist)

    def handle_playlist_file_deleted(self, path: Path) -> None:
        for state in self._mapping_store.all_playlists():
            try:
                stored = self._playlist_store.find_by_id(state.playlist_id)
            except FileNotFoundError:
                stored = None
            if stored is None:
                logger.info(
                    "Detected deleted playlist file %s for %s; "
                    "leaving Apple Music playlist unchanged",
                    path.name,
                    state.name,
                )

    def handle_audio_created(self, path: Path) -> None:
        if self._library_import.import_file(path):
            self._process_retry_queue()

    def handle_audio_deleted(self, path: Path) -> None:
        self._library_import.remove_file(path)

    def _is_playlist_allowed(self, name: str) -> bool:
        allowed = self._playlist_store.allowed_names()
        if allowed is None:
            return True
        return name in allowed

    def _apply_playlist_to_music(self, playlist: Playlist) -> None:
        if not self._is_playlist_allowed(playlist.name):
            logger.info(
                "Skipping playlist file→music: %s (not in allow-list)",
                playlist.name,
            )
            return
        logger.info("Syncing playlist file→music: %s", playlist.name)
        music_playlists = {p.name: p for p in self._apple_music.list_playlists()}
        music_playlist = music_playlists.get(playlist.name)
        if music_playlist is None:
            logger.info("Creating playlist in Music: %s", playlist.name)
            persistent_id = self._apple_music.create_playlist(playlist.name)
            music_playlist = MusicPlaylist(
                name=playlist.name, persistent_id=persistent_id
            )
        try:
            current = self._apple_music.get_playlist_tracks(music_playlist)
        except AppleMusicError as exc:
            logger.warning(
                "Skipping playlist file→music: %s (id=%s): %s",
                music_playlist.name,
                music_playlist.persistent_id,
                exc,
            )
            return
        current_paths = {t.relative_path for t in current if t.relative_path}
        target_paths = [t.relative_path for t in playlist.tracks]
        resolved_paths: list[str] = []
        for rel in target_paths:
            abs_path = resolve_relative_path(self._music_root, rel)
            if not abs_path.exists():
                logger.info(
                    "Track missing, queued for retry: %s in %s",
                    rel,
                    playlist.name,
                )
                self._retry_queue.add(playlist.id, rel)
                continue
            if not self._apple_music.track_exists_at_path(abs_path):
                self._library_import.import_file(abs_path)
            if self._apple_music.track_exists_at_path(abs_path):
                resolved_paths.append(rel)
                self._retry_queue.resolve(playlist.id, rel)
            else:
                self._retry_queue.add(playlist.id, rel)
        diff = diff_track_lists(
            sorted(current_paths),
            sorted(resolved_paths),
        )
        for rel in diff.to_add:
            logger.info("Adding track to %s: %s", playlist.name, rel)
            self._apple_music.add_track_by_path(
                playlist.name,
                resolve_relative_path(self._music_root, rel),
            )
        for rel in diff.to_remove:
            logger.info("Removing track from %s: %s", playlist.name, rel)
            self._apple_music.remove_track_by_path(
                playlist.name,
                resolve_relative_path(self._music_root, rel),
            )
        self._mapping_store.upsert_playlist(
            PlaylistSyncState(
                playlist_id=playlist.id,
                name=playlist.name,
                music_hash=_hash_paths(sorted(resolved_paths)),
                file_hash=_hash_paths(target_paths),
                last_synced_at=datetime.now(UTC),
            )
        )
        logger.info(
            "Synced playlist file→music: %s (%d tracks)",
            playlist.name,
            len(resolved_paths),
        )

    def _process_retry_queue(self) -> None:
        now = datetime.now(UTC)
        due_items = self._retry_queue.due_items(now)
        if due_items:
            logger.info("Processing %d retry queue item(s)", len(due_items))
        for item in due_items:
            playlist = self._playlist_store.find_by_id(item.playlist_id)
            if playlist:
                self._apply_playlist_to_music(playlist)
                self._retry_queue.mark_attempted(
                    item.playlist_id, item.relative_path, now
                )
        self._exhausted_count = len(self._retry_queue.exhausted_items())


def _hash_paths(paths: list[str]) -> str:
    joined = "\n".join(sorted(paths))
    return hashlib.sha256(joined.encode()).hexdigest()
