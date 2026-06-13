import re
from pathlib import Path

from encore.constants import AUDIO_EXTENSIONS


def relative_to_root(file_path: Path, music_root: Path) -> str:
    resolved_file = file_path.resolve()
    resolved_root = music_root.resolve()
    if not resolved_file.is_relative_to(resolved_root):
        raise ValueError(f"{file_path} is not under {music_root}")
    return str(resolved_file.relative_to(resolved_root))


def resolve_relative_path(music_root: Path, relative_path: str) -> Path:
    return music_root / Path(relative_path)


def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def slugify(name: str) -> str:
    lowered = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    return slug.strip("-")
