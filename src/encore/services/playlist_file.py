import json
from pathlib import Path

from encore.constants import PLAYLIST_ALLOW_FILENAME
from encore.models.playlist import Playlist
from encore.utils.paths import slugify


class PlaylistFileStore:
    def __init__(self, sync_dir: Path) -> None:
        self._sync_dir = sync_dir
        self._sync_dir.mkdir(parents=True, exist_ok=True)
        self._id_to_filename: dict[str, str] = {}
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._id_to_filename.clear()
        for path in self._sync_dir.glob("*.json"):
            data = json.loads(path.read_text())
            self._id_to_filename[data["id"]] = path.name

    def _path_for(self, playlist: Playlist) -> Path:
        filename = f"{slugify(playlist.name)}.json"
        self._id_to_filename[playlist.id] = filename
        return self._sync_dir / filename

    def write(self, playlist: Playlist) -> None:
        path = self._path_for(playlist)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(playlist.to_dict(), indent=2) + "\n")
        tmp.rename(path)

    def read(self, playlist_id: str) -> Playlist:
        path = self._find_path(playlist_id)
        return Playlist.from_dict(json.loads(path.read_text()))

    def delete(self, playlist_id: str) -> None:
        path = self._find_path(playlist_id)
        path.unlink()
        self._id_to_filename.pop(playlist_id, None)

    def find_by_id(self, playlist_id: str) -> Playlist | None:
        if playlist_id not in self._id_to_filename:
            return None
        return self.read(playlist_id)

    def list_all(self) -> list[Playlist]:
        return [self.read(pid) for pid in self._id_to_filename]

    def allowed_names(self) -> set[str] | None:
        path = self._sync_dir / PLAYLIST_ALLOW_FILENAME
        if not path.exists():
            return None
        names: set[str] = set()
        for line in path.read_text().splitlines():
            name = line.strip()
            if name:
                names.add(name)
        return names

    def _find_path(self, playlist_id: str) -> Path:
        if playlist_id not in self._id_to_filename:
            self._rebuild_index()
        filename = self._id_to_filename.get(playlist_id)
        if not filename:
            raise FileNotFoundError(f"No playlist file for id {playlist_id}")
        return self._sync_dir / filename
