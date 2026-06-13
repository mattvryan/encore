from dataclasses import dataclass


@dataclass(frozen=True)
class PlaylistTrack:
    relative_path: str
