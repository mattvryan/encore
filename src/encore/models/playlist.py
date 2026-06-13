from dataclasses import dataclass
from datetime import datetime

from encore.models.track import PlaylistTrack

__all__ = ["Playlist", "PlaylistTrack"]


@dataclass
class Playlist:
    id: str
    name: str
    updated_at: datetime
    tracks: list[PlaylistTrack]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "updatedAt": self.updated_at.isoformat(),
            "tracks": [{"relativePath": t.relative_path} for t in self.tracks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Playlist":
        from datetime import datetime

        return cls(
            id=data["id"],
            name=data["name"],
            updated_at=datetime.fromisoformat(data["updatedAt"]),
            tracks=[
                PlaylistTrack(relative_path=t["relativePath"])
                for t in data.get("tracks", [])
            ],
        )
