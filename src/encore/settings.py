import json
from pathlib import Path

from encore.constants import PLAYLIST_SYNC_DIR

SETTINGS_DIR = Path.home() / "Library" / "Application Support" / "Encore"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"


class Settings:
    def __init__(
        self, music_root: Path | None = None, launch_at_login: bool = False
    ) -> None:
        self.music_root = music_root
        self.launch_at_login = launch_at_login

    @property
    def sync_dir(self) -> Path | None:
        if self.music_root is None:
            return None
        return self.music_root / PLAYLIST_SYNC_DIR

    @property
    def state_path(self) -> Path:
        return SETTINGS_DIR / "sync_state.json"

    def save(self) -> None:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "music_root": str(self.music_root) if self.music_root else None,
            "launch_at_login": self.launch_at_login,
        }
        SETTINGS_PATH.write_text(json.dumps(payload, indent=2) + "\n")

    @classmethod
    def load(cls) -> "Settings":
        if not SETTINGS_PATH.exists():
            return cls()
        data = json.loads(SETTINGS_PATH.read_text())
        music_root = Path(data["music_root"]) if data.get("music_root") else None
        return cls(
            music_root=music_root,
            launch_at_login=data.get("launch_at_login", False),
        )
