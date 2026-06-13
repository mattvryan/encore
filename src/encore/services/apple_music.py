import subprocess
from dataclasses import dataclass
from pathlib import Path


class AppleMusicError(Exception):
    pass


@dataclass(frozen=True)
class MusicTrack:
    relative_path: str | None
    persistent_id: str
    name: str
    artist: str
    location: str | None


@dataclass(frozen=True)
class MusicPlaylist:
    name: str
    persistent_id: str


class AppleMusicService:
    def __init__(self, music_root: Path) -> None:
        self._music_root = music_root.resolve()

    def _run_script(self, script: str) -> str:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise AppleMusicError(result.stderr.strip() or "AppleScript failed")
        return result.stdout.strip()

    def ensure_running(self) -> None:
        self._run_script('tell application "Music" to activate')

    def list_playlists(self) -> list[MusicPlaylist]:
        output = self._run_script("""
            tell application "Music"
                set output to ""
                repeat with p in user playlists
                    set output to output & (name of p) & tab & (id of p as string) & linefeed
                end repeat
                return output
            end tell
        """)
        playlists = []
        for line in output.splitlines():
            if not line.strip():
                continue
            name, pid = line.split("\t", 1)
            playlists.append(MusicPlaylist(name=name, persistent_id=pid))
        return playlists

    def get_playlist_tracks(self, playlist_name: str) -> list[MusicTrack]:
        root = str(self._music_root)  # noqa: F841
        output = self._run_script(f'''
            tell application "Music"
                set output to ""
                set targetPlaylist to first user playlist whose name is "{_escape(playlist_name)}"
                repeat with t in tracks of targetPlaylist
                    set trackLocation to ""
                    try
                        set trackLocation to location of t
                    end try
                    set output to output & (name of t) & tab & (artist of t) & tab & (id of t as string) & tab & trackLocation & linefeed
                end repeat
                return output
            end tell
        ''')
        tracks = []
        for line in output.splitlines():
            if not line.strip():
                continue
            name, artist, pid, location = line.split("\t", 3)
            rel = (
                _location_to_relative(location, self._music_root) if location else None
            )
            tracks.append(
                MusicTrack(
                    relative_path=rel,
                    persistent_id=pid,
                    name=name,
                    artist=artist,
                    location=location or None,
                )
            )
        return tracks

    def create_playlist(self, name: str) -> str:
        return self._run_script(f'''
            tell application "Music"
                set p to make new user playlist with properties {{name:"{_escape(name)}"}}
                return id of p as string
            end tell
        ''')

    def delete_playlist(self, playlist_name: str) -> None:
        self._run_script(f'''
            tell application "Music"
                delete (first user playlist whose name is "{_escape(playlist_name)}")
            end tell
        ''')

    def add_track_by_path(self, playlist_name: str, file_path: Path) -> None:
        posix = str(file_path.resolve())
        self._run_script(f'''
            tell application "Music"
                set targetPlaylist to first user playlist whose name is "{_escape(playlist_name)}"
                set trackFile to POSIX file "{posix}"
                set foundTracks to (every track of library playlist 1 whose location is trackFile)
                if (count of foundTracks) is 0 then
                    set newTrack to add trackFile
                else
                    set newTrack to item 1 of foundTracks
                end if
                duplicate newTrack to targetPlaylist
            end tell
        ''')

    def remove_track_by_path(self, playlist_name: str, file_path: Path) -> None:
        posix = str(file_path.resolve())
        self._run_script(f'''
            tell application "Music"
                set targetPlaylist to first user playlist whose name is "{_escape(playlist_name)}"
                delete (every track of targetPlaylist whose location is POSIX file "{posix}")
            end tell
        ''')

    def import_file(self, file_path: Path) -> None:
        posix = str(file_path.resolve())
        self._run_script(f'''
            tell application "Music"
                set trackFile to POSIX file "{posix}"
                set existing to (every track of library playlist 1 whose location is trackFile)
                if (count of existing) is 0 then
                    add trackFile
                end if
            end tell
        ''')

    def remove_file_from_library(self, file_path: Path) -> None:
        posix = str(file_path.resolve())
        self._run_script(f'''
            tell application "Music"
                delete (every track of library playlist 1 whose location is POSIX file "{posix}")
            end tell
        ''')

    def track_exists_at_path(self, file_path: Path) -> bool:
        posix = str(file_path.resolve())
        output = self._run_script(f'''
            tell application "Music"
                set trackFile to POSIX file "{posix}"
                set matches to (every track of library playlist 1 whose location is trackFile)
                return (count of matches) as string
            end tell
        ''')
        return output.strip() != "0"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _location_to_relative(location: str, music_root: Path) -> str | None:
    if not location:
        return None
    path = location.removeprefix("file://")
    file_path = Path(path)
    try:
        return str(file_path.resolve().relative_to(music_root.resolve()))
    except ValueError:
        return None
