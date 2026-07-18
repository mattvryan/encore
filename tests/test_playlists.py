"""Automated tests for scripts/playlists.py (AppleScript mocked)."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import playlists as pl


def test_slugify() -> None:
    assert pl.slugify("Road Trip") == "road-trip"
    assert pl.slugify("Café Mix 2025!") == "café-mix-2025"
    assert pl.slugify("   ") == "playlist"


def test_escape_applescript() -> None:
    assert pl.escape_applescript('Say "hi"') == 'Say \\"hi\\"'
    assert pl.escape_applescript("a\\b") == "a\\\\b"


def test_track_ref_round_trip() -> None:
    track = pl.TrackRef(
        relative_path="Rock/song.mp3",
        name="Song",
        artist="Artist",
        album="Album",
    )
    assert pl.TrackRef.from_dict(track.to_dict()) == track


def test_track_ref_omits_empty_fields() -> None:
    assert pl.TrackRef(relative_path="a.mp3").to_dict() == {"relative_path": "a.mp3"}


def test_playlist_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "road-trip.json"
    tracks = [
        pl.TrackRef(relative_path="Rock/a.mp3", name="A", artist="Art"),
        pl.TrackRef(name="Cloud Only", artist="Someone"),
    ]
    pl.write_playlist_json(path, "Road Trip", tracks)

    name, loaded = pl.read_playlist_json(path)
    assert name == "Road Trip"
    assert loaded == tracks


def test_read_playlist_json_rejects_missing_name(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"tracks": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing playlist name"):
        pl.read_playlist_json(path)


def test_playlist_path_uses_slug(tmp_path: Path) -> None:
    assert pl.playlist_path(tmp_path, "Road Trip") == tmp_path / "road-trip.json"


def test_location_to_relative_inside_root(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Rock" / "song.mp3"
    track.parent.mkdir(parents=True)
    track.touch()

    rel = pl.location_to_relative(str(track), music_root)
    assert rel == "Rock/song.mp3"


def test_location_to_relative_outside_root(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    other = tmp_path / "Other" / "song.mp3"
    other.parent.mkdir()
    other.touch()

    assert pl.location_to_relative(str(other), music_root) is None


def test_location_to_relative_strips_file_url(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "a.mp3"
    track.parent.mkdir(parents=True)
    track.touch()

    rel = pl.location_to_relative(f"file://{track}", music_root)
    assert rel == "a.mp3"


def test_resolve_track_by_path(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Jazz" / "live.mp3"
    track.parent.mkdir(parents=True)
    track.touch()

    status, path, meta = pl.resolve_track(
        pl.TrackRef(relative_path="Jazz/live.mp3", name="Live"),
        music_root,
    )
    assert status == "path"
    assert path == track.resolve()
    assert meta is None


def test_resolve_track_falls_back_to_metadata_when_file_missing(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()

    status, path, meta = pl.resolve_track(
        pl.TrackRef(relative_path="missing.mp3", name="Song", artist="Art"),
        music_root,
    )
    assert status == "metadata"
    assert path is None
    assert meta == ("Song", "Art", None)


def test_resolve_track_rejects_path_escape(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()

    status, path, meta = pl.resolve_track(
        pl.TrackRef(relative_path="../secret.mp3"),
        music_root,
    )
    assert status == "missing"
    assert path is None
    assert meta is None


def test_resolve_track_missing_without_name(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()

    status, path, meta = pl.resolve_track(pl.TrackRef(relative_path="gone.mp3"), music_root)
    assert status == "missing"
    assert path is None
    assert meta is None


def test_list_playlists_parses_osascript_output() -> None:
    sep = pl.FIELD_SEP
    with patch.object(
        pl,
        "run_osascript",
        return_value=f"Road Trip{sep}123\nWorkout{sep}456\nbad-line\n",
    ):
        playlists = pl.list_playlists()

    assert playlists == [
        pl.MusicPlaylist(name="Road Trip", persistent_id="123"),
        pl.MusicPlaylist(name="Workout", persistent_id="456"),
    ]


def test_get_playlist_tracks_parses_and_relativizes(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Rock" / "a.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    playlist = pl.MusicPlaylist(name="Mix", persistent_id="99")
    raw = f"Song\tArtist\tAlbum\t{track}\nCloud\tSomeone\t\t\n"

    with patch.object(pl, "run_osascript", return_value=raw):
        tracks = pl.get_playlist_tracks(playlist, music_root)

    assert tracks == [
        pl.TrackRef(
            relative_path="Rock/a.mp3",
            name="Song",
            artist="Artist",
            album="Album",
        ),
        pl.TrackRef(name="Cloud", artist="Someone"),
    ]


def test_build_parser_export_and_import_flags(tmp_path: Path) -> None:
    parser = pl.build_parser()
    export_args = parser.parse_args(
        [
            "export",
            "--music-root",
            str(tmp_path),
            "--out-dir",
            str(tmp_path / "out"),
            "--dry-run",
        ]
    )
    assert export_args.command == "export"
    assert export_args.dry_run is True
    assert not hasattr(export_args, "overwrite") or not getattr(
        export_args, "overwrite", False
    )

    import_args = parser.parse_args(
        [
            "import",
            "--music-root",
            str(tmp_path),
            "--in-dir",
            str(tmp_path / "in"),
            "--overwrite",
            "--dry-run",
        ]
    )
    assert import_args.command == "import"
    assert import_args.overwrite is True
    assert import_args.dry_run is True


def test_cmd_export_dry_run_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    out_dir = tmp_path / "out"
    args = Namespace(music_root=music_root, out_dir=out_dir, dry_run=True)

    with (
        patch.object(pl, "ensure_music_running"),
        patch.object(
            pl,
            "list_playlists",
            return_value=[pl.MusicPlaylist(name="Mix", persistent_id="1")],
        ),
        patch.object(
            pl,
            "get_playlist_tracks",
            return_value=[pl.TrackRef(relative_path="a.mp3", name="A")],
        ),
    ):
        assert pl.cmd_export(args) == 0

    assert not out_dir.exists()
    out = capsys.readouterr().out
    assert "would write" in out
    assert "Mix" in out


def test_cmd_export_writes_json(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    out_dir = tmp_path / "out"
    args = Namespace(music_root=music_root, out_dir=out_dir, dry_run=False)
    tracks = [pl.TrackRef(relative_path="Rock/a.mp3", name="A", artist="Art")]

    with (
        patch.object(pl, "ensure_music_running"),
        patch.object(
            pl,
            "list_playlists",
            return_value=[pl.MusicPlaylist(name="Road Trip", persistent_id="1")],
        ),
        patch.object(pl, "get_playlist_tracks", return_value=tracks),
    ):
        assert pl.cmd_export(args) == 0

    path = out_dir / "road-trip.json"
    assert path.is_file()
    name, loaded = pl.read_playlist_json(path)
    assert name == "Road Trip"
    assert loaded == tracks


def test_cmd_import_skips_existing_without_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    pl.write_playlist_json(in_dir / "mix.json", "Mix", [])
    args = Namespace(
        music_root=music_root, in_dir=in_dir, dry_run=False, overwrite=False
    )

    with (
        patch.object(pl, "ensure_music_running"),
        patch.object(
            pl,
            "list_playlists",
            return_value=[pl.MusicPlaylist(name="Mix", persistent_id="1")],
        ),
        patch.object(pl, "create_playlist") as create,
        patch.object(pl, "clear_playlist") as clear,
    ):
        assert pl.cmd_import(args) == 0

    create.assert_not_called()
    clear.assert_not_called()
    assert "Skip existing playlist" in capsys.readouterr().out


def test_cmd_import_create_adds_tracks_by_path(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Rock" / "song.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    pl.write_playlist_json(
        in_dir / "fresh.json",
        "Fresh Mix",
        [pl.TrackRef(relative_path="Rock/song.mp3", name="Song")],
    )
    args = Namespace(
        music_root=music_root, in_dir=in_dir, dry_run=False, overwrite=False
    )

    with (
        patch.object(pl, "ensure_music_running"),
        patch.object(pl, "list_playlists", return_value=[]),
        patch.object(pl, "create_playlist", return_value="99") as create,
        patch.object(pl, "add_track_by_path") as add_path,
        patch.object(pl, "add_track_by_metadata") as add_meta,
    ):
        assert pl.cmd_import(args) == 0

    create.assert_called_once_with("Fresh Mix")
    add_path.assert_called_once_with("Fresh Mix", track.resolve())
    add_meta.assert_not_called()


def test_cmd_import_overwrite_clears_then_adds(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    pl.write_playlist_json(
        in_dir / "mix.json",
        "Mix",
        [pl.TrackRef(name="Only Meta", artist="Art")],
    )
    args = Namespace(
        music_root=music_root, in_dir=in_dir, dry_run=False, overwrite=True
    )

    with (
        patch.object(pl, "ensure_music_running"),
        patch.object(
            pl,
            "list_playlists",
            return_value=[pl.MusicPlaylist(name="Mix", persistent_id="1")],
        ),
        patch.object(pl, "clear_playlist") as clear,
        patch.object(pl, "create_playlist") as create,
        patch.object(pl, "add_track_by_metadata") as add_meta,
    ):
        assert pl.cmd_import(args) == 0

    clear.assert_called_once_with("Mix")
    create.assert_not_called()
    add_meta.assert_called_once_with("Mix", "Only Meta", "Art", None)


def test_cmd_import_dry_run_does_not_mutate_music(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "a.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    pl.write_playlist_json(
        in_dir / "new.json",
        "New Playlist",
        [
            pl.TrackRef(relative_path="a.mp3", name="A"),
            pl.TrackRef(name="Cloud", artist="X"),
            pl.TrackRef(relative_path="missing.mp3"),
        ],
    )
    args = Namespace(
        music_root=music_root, in_dir=in_dir, dry_run=True, overwrite=False
    )

    with (
        patch.object(pl, "ensure_music_running"),
        patch.object(pl, "list_playlists", return_value=[]),
        patch.object(pl, "create_playlist") as create,
        patch.object(pl, "add_track_by_path") as add_path,
        patch.object(pl, "add_track_by_metadata") as add_meta,
    ):
        assert pl.cmd_import(args) == 0

    create.assert_not_called()
    add_path.assert_not_called()
    add_meta.assert_not_called()
    out = capsys.readouterr().out
    assert "would add by path" in out
    assert "would try metadata match" in out
    assert "would skip unmatched track" in out


def test_main_export_missing_music_root(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    code = pl.main(
        [
            "export",
            "--music-root",
            str(missing),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert code == 1


def test_run_osascript_raises_on_failure() -> None:
    failed = MagicMock(returncode=1, stdout="", stderr="boom")
    with patch("playlists.subprocess.run", return_value=failed):
        with pytest.raises(pl.MusicError, match="boom"):
            pl.run_osascript("tell application \"Music\" to quit")
