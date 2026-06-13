from pathlib import Path
from unittest.mock import MagicMock

import pytest

from encore.services.library_import import LibraryImportService


@pytest.fixture
def music_root(tmp_path: Path) -> Path:
    root = tmp_path / "Music"
    root.mkdir()
    return root


@pytest.fixture
def apple_music() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(music_root: Path, apple_music: MagicMock) -> LibraryImportService:
    return LibraryImportService(music_root, apple_music)


def test_import_file_skips_non_audio(service: LibraryImportService) -> None:
    assert service.import_file(Path("readme.txt")) is False
    service._apple_music.import_file.assert_not_called()


def test_import_file_skips_missing_file(
    service: LibraryImportService, music_root: Path
) -> None:
    missing = music_root / "Rock" / "missing.mp3"
    assert service.import_file(missing) is False
    service._apple_music.import_file.assert_not_called()


def test_import_file_skips_already_in_library(
    service: LibraryImportService, music_root: Path, apple_music: MagicMock
) -> None:
    track = music_root / "Rock" / "song.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    apple_music.track_exists_at_path.return_value = True

    assert service.import_file(track) is False
    apple_music.import_file.assert_not_called()


def test_import_file_imports_new_track(
    service: LibraryImportService, music_root: Path, apple_music: MagicMock
) -> None:
    track = music_root / "Jazz" / "Blue.mp3"
    track.parent.mkdir(parents=True)
    track.touch()
    apple_music.track_exists_at_path.return_value = False

    assert service.import_file(track) is True
    apple_music.import_file.assert_called_once_with(track)


def test_remove_file_skips_non_audio(service: LibraryImportService) -> None:
    assert service.remove_file(Path("notes.txt")) is False
    service._apple_music.remove_file_from_library.assert_not_called()


def test_remove_file_removes_audio(
    service: LibraryImportService, music_root: Path, apple_music: MagicMock
) -> None:
    track = music_root / "Pop" / "hit.m4a"
    track.parent.mkdir(parents=True)
    track.touch()

    assert service.remove_file(track) is True
    apple_music.remove_file_from_library.assert_called_once_with(track)


def test_scan_and_import_existing_counts_new_files(
    service: LibraryImportService, music_root: Path, apple_music: MagicMock
) -> None:
    existing = music_root / "Rock" / "old.mp3"
    new_track = music_root / "Rock" / "new.mp3"
    ignored = music_root / "Rock" / "cover.jpg"
    for path in (existing, new_track, ignored):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def track_exists(path: Path) -> bool:
        return path.name == "old.mp3"

    apple_music.track_exists_at_path.side_effect = track_exists

    assert service.scan_and_import_existing() == 1
    apple_music.import_file.assert_called_once_with(new_track)
