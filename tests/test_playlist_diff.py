from encore.services.playlist_diff import PlaylistDiff, diff_track_lists


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


def test_diff_preserves_new_list_order_for_additions() -> None:
    old = ["a.mp3"]
    new = ["d.mp3", "b.mp3", "c.mp3", "a.mp3"]
    result = diff_track_lists(old, new)
    assert result.to_add == ["d.mp3", "b.mp3", "c.mp3"]


def test_playlist_diff_is_frozen() -> None:
    result = PlaylistDiff(to_add=["a.mp3"], to_remove=[])
    assert result.to_add == ["a.mp3"]
    assert result.to_remove == []
