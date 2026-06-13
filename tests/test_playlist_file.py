from datetime import UTC, datetime
from pathlib import Path

from encore.constants import PLAYLIST_ALLOW_FILENAME
from encore.models.playlist import Playlist, PlaylistTrack
from encore.services.playlist_file import PlaylistFileStore


def test_playlist_round_trip(tmp_path: Path) -> None:
    store = PlaylistFileStore(tmp_path)
    playlist = Playlist(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="Road Trip",
        updated_at=datetime(2026, 6, 12, 14, 30, tzinfo=UTC),
        tracks=[
            PlaylistTrack(relative_path="Rock/Queen/Bohemian Rhapsody.mp3"),
            PlaylistTrack(relative_path="Jazz/Miles/So What.mp3"),
        ],
    )
    store.write(playlist)
    loaded = store.read(playlist.id)
    assert loaded == playlist


def test_playlist_file_uses_slug_filename(tmp_path: Path) -> None:
    store = PlaylistFileStore(tmp_path)
    playlist = Playlist(
        id="abc",
        name="Road Trip 2025",
        updated_at=datetime.now(UTC),
        tracks=[],
    )
    store.write(playlist)
    assert (tmp_path / "road-trip-2025.json").exists()


def test_delete_playlist_file(tmp_path: Path) -> None:
    store = PlaylistFileStore(tmp_path)
    playlist = Playlist(
        id="abc",
        name="Test",
        updated_at=datetime.now(UTC),
        tracks=[],
    )
    store.write(playlist)
    store.delete(playlist.id)
    assert store.find_by_id("abc") is None


def test_list_all_playlists(tmp_path: Path) -> None:
    store = PlaylistFileStore(tmp_path)
    p1 = Playlist(id="1", name="A", updated_at=datetime.now(UTC), tracks=[])
    p2 = Playlist(id="2", name="B", updated_at=datetime.now(UTC), tracks=[])
    store.write(p1)
    store.write(p2)
    ids = {p.id for p in store.list_all()}
    assert ids == {"1", "2"}


def test_playlist_to_dict_and_from_dict() -> None:
    playlist = Playlist(
        id="abc",
        name="Road Trip",
        updated_at=datetime(2026, 6, 12, 14, 30, tzinfo=UTC),
        tracks=[PlaylistTrack(relative_path="Rock/song.mp3")],
    )

    restored = Playlist.from_dict(playlist.to_dict())

    assert restored == playlist


def test_allowed_names_returns_none_when_file_missing(tmp_path: Path) -> None:
    store = PlaylistFileStore(tmp_path)
    assert store.allowed_names() is None


def test_allowed_names_parses_playlist_names(tmp_path: Path) -> None:
    store = PlaylistFileStore(tmp_path)
    (tmp_path / PLAYLIST_ALLOW_FILENAME).write_text(
        "Road Trip\n\nWorkout\n  Chill Mix  \n"
    )

    assert store.allowed_names() == {"Road Trip", "Workout", "Chill Mix"}


def test_allowed_names_handles_utf8_bom(tmp_path: Path) -> None:
    store = PlaylistFileStore(tmp_path)
    (tmp_path / PLAYLIST_ALLOW_FILENAME).write_bytes(
        b"\xef\xbb\xbfWorkout\nRoad Trip\n"
    )

    assert store.allowed_names() == {"Workout", "Road Trip"}
