import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from encore.models.sync_state import PlaylistSyncState


class MappingStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._playlists: dict[str, PlaylistSyncState] = {}
        if path.exists():
            self._load()

    def _load(self) -> None:
        data = json.loads(self._path.read_text())
        for item in data.get("playlists", []):
            state = PlaylistSyncState(
                playlist_id=item["playlist_id"],
                name=item["name"],
                music_hash=item["music_hash"],
                file_hash=item["file_hash"],
                last_synced_at=datetime.fromisoformat(item["last_synced_at"]),
            )
            self._playlists[state.playlist_id] = state

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "playlists": [
                {
                    **asdict(s),
                    "last_synced_at": s.last_synced_at.isoformat(),
                }
                for s in self._playlists.values()
            ]
        }
        self._path.write_text(json.dumps(payload, indent=2) + "\n")

    def upsert_playlist(self, state: PlaylistSyncState) -> None:
        self._playlists[state.playlist_id] = state
        self.save()

    def get_playlist(self, playlist_id: str) -> PlaylistSyncState | None:
        return self._playlists.get(playlist_id)

    def remove_playlist(self, playlist_id: str) -> None:
        self._playlists.pop(playlist_id, None)
        self.save()

    def all_playlists(self) -> list[PlaylistSyncState]:
        return list(self._playlists.values())
