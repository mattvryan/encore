from pathlib import Path

import pytest

pytest.importorskip("encore.utils.paths")

from encore.utils.paths import (
    is_audio_file,
    relative_to_root,
    resolve_relative_path,
    slugify,
)


def test_relative_to_root() -> None:
    root = Path("/Users/matt/Dropbox/Music")
    file = Path("/Users/matt/Dropbox/Music/Rock/song.mp3")
    assert relative_to_root(file, root) == "Rock/song.mp3"


def test_relative_to_root_rejects_outside() -> None:
    root = Path("/Users/matt/Dropbox/Music")
    file = Path("/Users/matt/Other/song.mp3")
    with pytest.raises(ValueError):
        relative_to_root(file, root)


def test_resolve_relative_path() -> None:
    root = Path("/Users/matt/Dropbox/Music")
    assert resolve_relative_path(root, "Rock/song.mp3") == root / "Rock" / "song.mp3"


def test_is_audio_file() -> None:
    assert is_audio_file(Path("song.mp3"))
    assert is_audio_file(Path("song.M4A"))
    assert not is_audio_file(Path("notes.txt"))


def test_slugify() -> None:
    assert slugify("Road Trip 2025!") == "road-trip-2025"
