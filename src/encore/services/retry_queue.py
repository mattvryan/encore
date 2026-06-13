from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from encore.constants import RETRY_INTERVALS_SECONDS


@dataclass(frozen=True)
class PendingTrack:
    playlist_id: str
    relative_path: str


@dataclass
class _PendingEntry:
    playlist_id: str
    relative_path: str
    attempts: int
    next_retry_at: datetime


class RetryQueue:
    def __init__(self, max_retries: int | None = None) -> None:
        self._entries: dict[tuple[str, str], _PendingEntry] = {}
        self._max_retries = max_retries or len(RETRY_INTERVALS_SECONDS)

    def add(self, playlist_id: str, relative_path: str) -> None:
        key = (playlist_id, relative_path)
        if key not in self._entries:
            self._entries[key] = _PendingEntry(
                playlist_id=playlist_id,
                relative_path=relative_path,
                attempts=0,
                next_retry_at=datetime.now(UTC),
            )

    def due_items(self, now: datetime) -> list[PendingTrack]:
        return [
            PendingTrack(e.playlist_id, e.relative_path)
            for e in self._entries.values()
            if e.next_retry_at <= now and e.attempts < self._max_retries
        ]

    def mark_attempted(
        self, playlist_id: str, relative_path: str, now: datetime
    ) -> None:
        entry = self._entries[(playlist_id, relative_path)]
        entry.attempts += 1
        if entry.attempts < self._max_retries:
            delay = RETRY_INTERVALS_SECONDS[
                min(entry.attempts - 1, len(RETRY_INTERVALS_SECONDS) - 1)
            ]
            entry.next_retry_at = now + timedelta(seconds=delay)

    def resolve(self, playlist_id: str, relative_path: str) -> None:
        self._entries.pop((playlist_id, relative_path), None)

    def clear_playlist(self, playlist_id: str) -> None:
        keys = [k for k in self._entries if k[0] == playlist_id]
        for key in keys:
            del self._entries[key]

    def is_exhausted(self, playlist_id: str, relative_path: str) -> bool:
        entry = self._entries.get((playlist_id, relative_path))
        return entry is not None and entry.attempts >= self._max_retries

    def exhausted_items(self) -> list[PendingTrack]:
        return [
            PendingTrack(e.playlist_id, e.relative_path)
            for e in self._entries.values()
            if e.attempts >= self._max_retries
        ]
