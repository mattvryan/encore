from datetime import UTC, datetime, timedelta

from encore.services.retry_queue import PendingTrack, RetryQueue


def test_first_retry_due_immediately() -> None:
    queue = RetryQueue()
    queue.add("playlist-1", "Rock/song.mp3")
    due = queue.due_items(datetime.now(UTC))
    assert len(due) == 1
    assert due[0].relative_path == "Rock/song.mp3"


def test_retry_not_due_before_interval() -> None:
    queue = RetryQueue()
    queue.add("playlist-1", "Rock/song.mp3")
    now = datetime.now(UTC)
    queue.mark_attempted("playlist-1", "Rock/song.mp3", now)
    before_interval = now + timedelta(seconds=15)
    assert queue.due_items(before_interval) == []


def test_exhausted_after_max_retries() -> None:
    queue = RetryQueue(max_retries=2)
    queue.add("playlist-1", "Rock/song.mp3")
    now = datetime.now(UTC)
    queue.mark_attempted("playlist-1", "Rock/song.mp3", now)
    queue.mark_attempted("playlist-1", "Rock/song.mp3", now + timedelta(seconds=60))
    assert queue.is_exhausted("playlist-1", "Rock/song.mp3")
    assert queue.exhausted_items() == [PendingTrack("playlist-1", "Rock/song.mp3")]


def test_resolve_removes_item() -> None:
    queue = RetryQueue()
    queue.add("playlist-1", "Rock/song.mp3")
    queue.resolve("playlist-1", "Rock/song.mp3")
    assert queue.due_items(datetime.now(UTC)) == []


def test_clear_playlist_removes_all_tracks_for_playlist() -> None:
    queue = RetryQueue()
    queue.add("playlist-1", "Rock/song.mp3")
    queue.add("playlist-1", "Jazz/song.mp3")
    queue.add("playlist-2", "Pop/song.mp3")

    queue.clear_playlist("playlist-1")

    assert queue.due_items(datetime.now(UTC)) == [
        PendingTrack("playlist-2", "Pop/song.mp3")
    ]


def test_add_is_idempotent() -> None:
    queue = RetryQueue()
    queue.add("playlist-1", "Rock/song.mp3")
    queue.add("playlist-1", "Rock/song.mp3")

    assert queue.due_items(datetime.now(UTC)) == [
        PendingTrack("playlist-1", "Rock/song.mp3")
    ]
