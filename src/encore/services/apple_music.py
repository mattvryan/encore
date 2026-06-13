import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SCRIPT_TIMEOUT = 120
TRACK_FETCH_TIMEOUT = 300
PLAYLIST_FIELD_SEP = "\x1f"


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

    def _run_script(
        self, script: str, *, timeout: float = DEFAULT_SCRIPT_TIMEOUT
    ) -> str:
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise AppleMusicError(f"AppleScript timed out after {timeout:g}s") from exc
        if result.returncode != 0:
            raise AppleMusicError(result.stderr.strip() or "AppleScript failed")
        return result.stdout.strip()

    def ensure_running(self) -> None:
        self._run_script("""
            tell application "Music"
                if not running then launch
            end tell
        """)

    @contextmanager
    def preserve_user_focus(self) -> Iterator[None]:
        front_app = self._frontmost_app_name()
        try:
            yield
        finally:
            self._restore_frontmost_app(front_app)

    def _frontmost_app_name(self) -> str | None:
        name = self._run_script("""
            tell application "System Events"
                set frontApps to name of every application process whose frontmost is true
                if (count of frontApps) is 0 then
                    return ""
                end if
                return item 1 of frontApps
            end tell
        """).strip()
        return name or None

    def _restore_frontmost_app(self, app_name: str | None) -> None:
        if not app_name or app_name == "Music":
            return
        self._run_script(f'tell application "{_escape(app_name)}" to activate')

    def list_playlists(self) -> list[MusicPlaylist]:
        sep = PLAYLIST_FIELD_SEP
        output = self._run_script("""
            tell application "Music"
                set output to ""
                set delim to (ASCII character 31)
                repeat with p in user playlists
                    if class of p is not folder then
                        set output to output & (name of p) & delim & (id of p as string) & linefeed
                    end if
                end repeat
                return output
            end tell
        """)
        playlists = []
        for line in output.splitlines():
            if not line.strip():
                continue
            if sep not in line:
                continue
            name, pid = line.split(sep, 1)
            if not pid.isdigit():
                continue
            playlists.append(MusicPlaylist(name=name, persistent_id=pid))
        return playlists

    def get_playlist_tracks(self, playlist: MusicPlaylist) -> list[MusicTrack]:
        if not playlist.persistent_id.isdigit():
            raise AppleMusicError(f"Invalid playlist id: {playlist.persistent_id!r}")
        output = self._run_script(
            f"""
            tell application "Music"
                set output to ""
                set targetPlaylist to first user playlist whose id is {playlist.persistent_id}
                repeat with t in tracks of targetPlaylist
                    set trackLocation to ""
                    try
                        set trackLocation to location of t
                    end try
                    set output to output & (name of t) & tab & (artist of t) & tab & (id of t as string) & tab & trackLocation & linefeed
                end repeat
                return output
            end tell
        """,
            timeout=TRACK_FETCH_TIMEOUT,
        )
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
