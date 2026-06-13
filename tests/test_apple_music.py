from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from encore.services.apple_music import (
    AppleMusicError,
    AppleMusicService,
    MusicPlaylist,
    MusicTrack,
    _escape,
    _location_to_relative,
)


def test_escape() -> None:
    assert _escape(r"foo\bar") == r"foo\\bar"
    assert _escape('say "hello"') == r"say \"hello\""


def test_location_to_relative_inside_root(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Rock" / "song.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    location = f"file://{track}"
    assert _location_to_relative(location, music_root) == "Rock/song.mp3"


def test_location_to_relative_outside_root(tmp_path: Path) -> None:
    music_root = tmp_path / "Music"
    music_root.mkdir()
    outside = tmp_path / "Other" / "song.mp3"
    outside.parent.mkdir()
    outside.touch()
    location = f"file://{outside}"
    assert _location_to_relative(location, music_root) is None


def test_location_to_relative_empty() -> None:
    assert _location_to_relative("", Path("/Music")) is None


@patch("encore.services.apple_music.subprocess.run")
def test_run_script_raises_on_failure(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=1, stderr="script error", stdout="")
    svc = AppleMusicService(tmp_path)
    with pytest.raises(AppleMusicError, match="script error"):
        svc._run_script("tell application Music to quit")


@patch("encore.services.apple_music.subprocess.run")
def test_list_playlists_parses_output(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Road Trip\tABC123\nWorkout\tDEF456\n",
        stderr="",
    )
    svc = AppleMusicService(tmp_path)
    playlists = svc.list_playlists()
    assert playlists == [
        MusicPlaylist(name="Road Trip", persistent_id="ABC123"),
        MusicPlaylist(name="Workout", persistent_id="DEF456"),
    ]


@patch("encore.services.apple_music.subprocess.run")
def test_get_playlist_tracks_parses_output_and_relative_paths(
    mock_run: MagicMock, tmp_path: Path
) -> None:
    music_root = tmp_path / "Music"
    track = music_root / "Jazz" / "Blue.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    location = f"file://{track}"
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=f"Blue Train\tJohn Coltrane\tPID1\t{location}\n",
        stderr="",
    )
    svc = AppleMusicService(music_root)
    tracks = svc.get_playlist_tracks("My Playlist")
    assert tracks == [
        MusicTrack(
            relative_path="Jazz/Blue.mp3",
            persistent_id="PID1",
            name="Blue Train",
            artist="John Coltrane",
            location=location,
        )
    ]


@patch("encore.services.apple_music.subprocess.run")
def test_track_exists_at_path_true(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="1", stderr="")
    svc = AppleMusicService(tmp_path)
    assert svc.track_exists_at_path(tmp_path / "song.mp3") is True


@patch("encore.services.apple_music.subprocess.run")
def test_track_exists_at_path_false(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="0", stderr="")
    svc = AppleMusicService(tmp_path)
    assert svc.track_exists_at_path(tmp_path / "missing.mp3") is False


@patch("encore.services.apple_music.subprocess.run")
def test_create_playlist_returns_id(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout="NEWPLAYLISTID", stderr="")
    svc = AppleMusicService(tmp_path)
    assert svc.create_playlist("Fresh Mix") == "NEWPLAYLISTID"
