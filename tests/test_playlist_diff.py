import pytest

pytest.importorskip("encore.services.playlist_diff")

from encore.services.playlist_diff import diff_track_lists


def test_diff_additions() -> None:
    old = ["a.mp3", "b.mp3"]
    new = ["a.mp3", "b.mp3", "c.mp3"]
    result = diff_track_lists(old, new)
    assert result.to_add == ["c.mp3"]
    assert result.to_remove == []


def test_diff_removals() -> None:
    old = ["a.mp3", "b.mp3", "c.mp3"]
    new = ["a.mp3"]
    result = diff_track_lists(old, new)
    assert result.to_add == []
    assert result.to_remove == ["b.mp3", "c.mp3"]


def test_diff_both() -> None:
    old = ["a.mp3", "b.mp3"]
    new = ["b.mp3", "c.mp3"]
    result = diff_track_lists(old, new)
    assert result.to_add == ["c.mp3"]
    assert result.to_remove == ["a.mp3"]


def test_diff_empty() -> None:
    result = diff_track_lists([], [])
    assert result.to_add == []
    assert result.to_remove == []
