import logging
from pathlib import Path

from encore.services.apple_music import AppleMusicService
from encore.utils.paths import is_audio_file

logger = logging.getLogger(__name__)


class LibraryImportService:
    def __init__(self, music_root: Path, apple_music: AppleMusicService) -> None:
        self._music_root = music_root
        self._apple_music = apple_music

    def import_file(self, file_path: Path) -> bool:
        if not is_audio_file(file_path):
            return False
        if not file_path.exists():
            return False
        if self._apple_music.track_exists_at_path(file_path):
            logger.debug("Already in library: %s", file_path)
            return False
        logger.info("Importing: %s", file_path)
        self._apple_music.import_file(file_path)
        return True

    def remove_file(self, file_path: Path) -> bool:
        if not is_audio_file(file_path):
            return False
        logger.info("Removing from library: %s", file_path)
        self._apple_music.remove_file_from_library(file_path)
        return True

    def scan_and_import_existing(self) -> int:
        count = 0
        for path in self._music_root.rglob("*"):
            if path.is_file() and is_audio_file(path) and self.import_file(path):
                count += 1
        return count
