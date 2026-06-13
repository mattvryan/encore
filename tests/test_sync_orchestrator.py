import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from encore.models.playlist import Playlist, PlaylistTrack
from encore.models.sync_state import PlaylistSyncState
from encore.services.apple_music import MusicPlaylist, MusicTrack
from encore.services.library_import import LibraryImportService
from encore.services.playlist_file import PlaylistFileStore
from encore.services.retry_queue import RetryQueue
from encore.services.sync_orchestrator import SyncOrchestrator, _hash_paths
from encore.storage.mapping_store import MappingStore


@pytest.fixture
def music_root(tmp_path: Path) -> Path:
    root = tmp_path / "Music"
    root.mkdir()
    return root


@pytest.fixture
def sync_dir(music_root: Path) -> Path:
    path = music_root / ".playlist-sync"
    path.mkdir()
    return path


@pytest.fixture
def apple_music() -> MagicMock:
    return MagicMock()


@pytest.fixture
def library_import(apple_music: MagicMock, music_root: Path) -> MagicMock:
    return MagicMock(spec=LibraryImportService)


@pytest.fixture
def playlist_store(sync_dir: Path) -> PlaylistFileStore:
    return PlaylistFileStore(sync_dir)


@pytest.fixture
def mapping_store(tmp_path: Path) -> MappingStore:
    return MappingStore(tmp_path / "mapping.json")


@pytest.fixture
def retry_queue() -> RetryQueue:
    return RetryQueue()


@pytest.fixture
def orchestrator(
    music_root: Path,
    apple_music: MagicMock,
    playlist_store: PlaylistFileStore,
    mapping_store: MappingStore,
    library_import: MagicMock,
    retry_queue: RetryQueue,
) -> SyncOrchestrator:
    return SyncOrchestrator(
        music_root,
        apple_music,
        playlist_store,
        mapping_store,
        library_import,
        retry_queue,
    )


def test_hash_paths_is_order_independent() -> None:
    assert _hash_paths(["b.mp3", "a.mp3"]) == _hash_paths(["a.mp3", "b.mp3"])


def test_sync_all_runs_full_pipeline(orchestrator: SyncOrchestrator) -> None:
    with (
        patch.object(orchestrator, "sync_music_to_files") as sync_music,
        patch.object(orchestrator, "sync_files_to_music") as sync_files,
        patch.object(orchestrator, "_process_retry_queue") as process_retry,
    ):
        orchestrator.sync_all()

    orchestrator._apple_music.ensure_running.assert_called_once()
    sync_music.assert_called_once()
    sync_files.assert_called_once()
    process_retry.assert_called_once()


def test_sync_music_to_files_skips_unchanged_hash(
    orchestrator: SyncOrchestrator,
    mapping_store: MappingStore,
    apple_music: MagicMock,
    playlist_store: PlaylistFileStore,
) -> None:
    tracks = [MusicTrack("Rock/a.mp3", "T1", "A", "Artist", "loc")]
    apple_music.list_playlists.return_value = [
        MusicPlaylist(name="Road Trip", persistent_id="PID1")
    ]
    apple_music.get_playlist_tracks.return_value = tracks
    mapping_store.upsert_playlist(
        PlaylistSyncState(
            playlist_id="PID1",
            name="Road Trip",
            music_hash=_hash_paths(["Rock/a.mp3"]),
            file_hash="file-hash",
            last_synced_at=datetime.now(UTC),
        )
    )

    with patch.object(playlist_store, "write") as write:
        orchestrator.sync_music_to_files()

    write.assert_not_called()


def test_sync_music_to_files_writes_updated_playlist(
    orchestrator: SyncOrchestrator,
    apple_music: MagicMock,
    playlist_store: PlaylistFileStore,
) -> None:
    apple_music.list_playlists.return_value = [
        MusicPlaylist(name="Workout", persistent_id="PID2")
    ]
    apple_music.get_playlist_tracks.return_value = [
        MusicTrack("Pop/hit.mp3", "T1", "Hit", "Artist", "loc")
    ]

    orchestrator.sync_music_to_files()

    saved = playlist_store.find_by_id(playlist_store.list_all()[0].id)
    assert saved is not None
    assert saved.name == "Workout"
    assert saved.tracks == [PlaylistTrack(relative_path="Pop/hit.mp3")]


def test_sync_music_to_files_skips_when_file_is_newer(
    orchestrator: SyncOrchestrator,
    apple_music: MagicMock,
    playlist_store: PlaylistFileStore,
    mapping_store: MappingStore,
) -> None:
    playlist_id = "playlist-1"
    newer = Playlist(
        id=playlist_id,
        name="Road Trip",
        updated_at=datetime(2099, 1, 1, tzinfo=UTC),
        tracks=[PlaylistTrack(relative_path="Rock/old.mp3")],
    )
    playlist_store.write(newer)
    apple_music.list_playlists.return_value = [
        MusicPlaylist(name="Road Trip", persistent_id=playlist_id)
    ]
    apple_music.get_playlist_tracks.return_value = [
        MusicTrack("Rock/new.mp3", "T1", "New", "Artist", "loc")
    ]
    mapping_store.upsert_playlist(
        PlaylistSyncState(
            playlist_id=playlist_id,
            name="Road Trip",
            music_hash="old-hash",
            file_hash="old-file-hash",
            last_synced_at=datetime.now(UTC),
        )
    )

    orchestrator.sync_music_to_files()

    loaded = playlist_store.find_by_id(playlist_id)
    assert loaded is not None
    assert loaded.tracks == [PlaylistTrack(relative_path="Rock/old.mp3")]


def test_apply_playlist_to_music_creates_playlist_and_adds_tracks(
    orchestrator: SyncOrchestrator,
    music_root: Path,
    apple_music: MagicMock,
) -> None:
    track = music_root / "Rock" / "song.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    playlist = Playlist(
        id="p1",
        name="Fresh Mix",
        updated_at=datetime.now(UTC),
        tracks=[PlaylistTrack(relative_path="Rock/song.mp3")],
    )
    apple_music.list_playlists.return_value = []
    apple_music.get_playlist_tracks.return_value = []
    apple_music.track_exists_at_path.return_value = True

    orchestrator._apply_playlist_to_music(playlist)

    apple_music.create_playlist.assert_called_once_with("Fresh Mix")
    apple_music.add_track_by_path.assert_called_once_with("Fresh Mix", track)


def test_apply_playlist_to_music_removes_stale_tracks(
    orchestrator: SyncOrchestrator,
    music_root: Path,
    apple_music: MagicMock,
) -> None:
    kept = music_root / "Rock" / "keep.mp3"
    removed = music_root / "Rock" / "gone.mp3"
    for path in (kept, removed):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    playlist = Playlist(
        id="p1",
        name="Mix",
        updated_at=datetime.now(UTC),
        tracks=[PlaylistTrack(relative_path="Rock/keep.mp3")],
    )
    apple_music.list_playlists.return_value = [
        MusicPlaylist(name="Mix", persistent_id="PID")
    ]
    apple_music.get_playlist_tracks.return_value = [
        MusicTrack("Rock/keep.mp3", "T1", "Keep", "Artist", "loc1"),
        MusicTrack("Rock/gone.mp3", "T2", "Gone", "Artist", "loc2"),
    ]
    apple_music.track_exists_at_path.return_value = True

    orchestrator._apply_playlist_to_music(playlist)

    apple_music.remove_track_by_path.assert_called_once_with("Mix", removed)


def test_apply_playlist_to_music_queues_missing_files(
    orchestrator: SyncOrchestrator,
    retry_queue: RetryQueue,
    apple_music: MagicMock,
) -> None:
    playlist = Playlist(
        id="p1",
        name="Mix",
        updated_at=datetime.now(UTC),
        tracks=[PlaylistTrack(relative_path="Rock/missing.mp3")],
    )
    apple_music.list_playlists.return_value = [
        MusicPlaylist(name="Mix", persistent_id="PID")
    ]
    apple_music.get_playlist_tracks.return_value = []

    orchestrator._apply_playlist_to_music(playlist)

    assert retry_queue.due_items(datetime.now(UTC)) != []


def test_apply_playlist_to_music_imports_missing_library_tracks(
    orchestrator: SyncOrchestrator,
    music_root: Path,
    apple_music: MagicMock,
    library_import: MagicMock,
) -> None:
    track = music_root / "Jazz" / "live.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    playlist = Playlist(
        id="p1",
        name="Live",
        updated_at=datetime.now(UTC),
        tracks=[PlaylistTrack(relative_path="Jazz/live.mp3")],
    )
    apple_music.list_playlists.return_value = [
        MusicPlaylist(name="Live", persistent_id="PID")
    ]
    apple_music.get_playlist_tracks.return_value = []
    apple_music.track_exists_at_path.side_effect = [False, True]

    orchestrator._apply_playlist_to_music(playlist)

    library_import.import_file.assert_called_once_with(track)
    apple_music.add_track_by_path.assert_called_once_with("Live", track)


def test_apply_playlist_file_reads_json_and_applies(
    orchestrator: SyncOrchestrator,
    sync_dir: Path,
    apple_music: MagicMock,
) -> None:
    playlist = Playlist(
        id="p1",
        name="From File",
        updated_at=datetime.now(UTC),
        tracks=[],
    )
    path = sync_dir / "from-file.json"
    path.write_text(json.dumps(playlist.to_dict()))
    apple_music.list_playlists.return_value = [
        MusicPlaylist(name="From File", persistent_id="PID")
    ]
    apple_music.get_playlist_tracks.return_value = []

    with patch.object(orchestrator, "_apply_playlist_to_music") as apply:
        orchestrator.apply_playlist_file(path)

    apply.assert_called_once()
    assert apply.call_args.args[0].name == "From File"


def test_handle_playlist_file_deleted_removes_orphaned_music_playlist(
    orchestrator: SyncOrchestrator,
    mapping_store: MappingStore,
    retry_queue: RetryQueue,
    apple_music: MagicMock,
) -> None:
    mapping_store.upsert_playlist(
        PlaylistSyncState(
            playlist_id="gone",
            name="Deleted Mix",
            music_hash="h1",
            file_hash="h2",
            last_synced_at=datetime.now(UTC),
        )
    )

    orchestrator.handle_playlist_file_deleted(Path("deleted.json"))

    apple_music.delete_playlist.assert_called_once_with("Deleted Mix")
    assert mapping_store.get_playlist("gone") is None
    assert retry_queue.due_items(datetime.now(UTC)) == []


def test_handle_audio_created_processes_retry_queue_on_import(
    orchestrator: SyncOrchestrator,
    library_import: MagicMock,
) -> None:
    path = Path("Rock/new.mp3")
    library_import.import_file.return_value = True

    with patch.object(orchestrator, "_process_retry_queue") as process_retry:
        orchestrator.handle_audio_created(path)

    library_import.import_file.assert_called_once_with(path)
    process_retry.assert_called_once()


def test_handle_audio_created_skips_retry_when_not_imported(
    orchestrator: SyncOrchestrator,
    library_import: MagicMock,
) -> None:
    library_import.import_file.return_value = False

    with patch.object(orchestrator, "_process_retry_queue") as process_retry:
        orchestrator.handle_audio_created(Path("Rock/existing.mp3"))

    process_retry.assert_not_called()


def test_handle_audio_deleted_removes_from_library(
    orchestrator: SyncOrchestrator,
    library_import: MagicMock,
) -> None:
    path = Path("Rock/gone.mp3")

    orchestrator.handle_audio_deleted(path)

    library_import.remove_file.assert_called_once_with(path)


def test_process_retry_queue_retries_due_playlists(
    orchestrator: SyncOrchestrator,
    playlist_store: PlaylistFileStore,
    retry_queue: RetryQueue,
) -> None:
    playlist = Playlist(
        id="p1",
        name="Retry Me",
        updated_at=datetime.now(UTC),
        tracks=[PlaylistTrack(relative_path="Rock/missing.mp3")],
    )
    playlist_store.write(playlist)
    retry_queue.add("p1", "Rock/missing.mp3")

    with patch.object(orchestrator, "_apply_playlist_to_music") as apply:
        orchestrator._process_retry_queue()

    apply.assert_called_once_with(playlist)


def test_exhausted_count_tracks_retry_queue(
    orchestrator: SyncOrchestrator,
    retry_queue: RetryQueue,
) -> None:
    retry_queue.add("p1", "Rock/missing.mp3")
    now = datetime.now(UTC)
    retry_queue.mark_attempted("p1", "Rock/missing.mp3", now)
    retry_queue.mark_attempted("p1", "Rock/missing.mp3", now)
    retry_queue.mark_attempted("p1", "Rock/missing.mp3", now)
    retry_queue.mark_attempted("p1", "Rock/missing.mp3", now)
    retry_queue.mark_attempted("p1", "Rock/missing.mp3", now)

    orchestrator._process_retry_queue()

    assert orchestrator.exhausted_count == 1
