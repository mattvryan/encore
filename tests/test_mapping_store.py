from datetime import UTC, datetime
from pathlib import Path

from encore.models.sync_state import PlaylistSyncState
from encore.storage.mapping_store import MappingStore


def test_save_and_load_playlist_state(tmp_path: Path) -> None:
    store = MappingStore(tmp_path / "state.json")
    state = PlaylistSyncState(
        playlist_id="abc",
        name="Road Trip",
        music_hash="hash-music",
        file_hash="hash-file",
        last_synced_at=datetime(2026, 6, 12, tzinfo=UTC),
    )
    store.upsert_playlist(state)
    loaded = store.get_playlist("abc")
    assert loaded == state


def test_remove_playlist_state(tmp_path: Path) -> None:
    store = MappingStore(tmp_path / "state.json")
    state = PlaylistSyncState(
        playlist_id="abc",
        name="Road Trip",
        music_hash="h1",
        file_hash="h2",
        last_synced_at=datetime(2026, 6, 12, tzinfo=UTC),
    )
    store.upsert_playlist(state)
    store.remove_playlist("abc")
    assert store.get_playlist("abc") is None


def test_mapping_store_persists_to_disk(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = PlaylistSyncState(
        playlist_id="abc",
        name="Road Trip",
        music_hash="h1",
        file_hash="h2",
        last_synced_at=datetime(2026, 6, 12, tzinfo=UTC),
    )
    MappingStore(path).upsert_playlist(state)

    reloaded = MappingStore(path).get_playlist("abc")

    assert reloaded == state
