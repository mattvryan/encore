from dataclasses import dataclass
from datetime import datetime


@dataclass
class PlaylistSyncState:
    playlist_id: str
    name: str
    music_hash: str
    file_hash: str
    last_synced_at: datetime
