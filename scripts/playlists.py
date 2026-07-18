#!/usr/bin/env python3
"""Export and import Apple Music user playlists as JSON files.

Examples:
  python3 scripts/playlists.py export --music-root ~/Dropbox/Tunes --out-dir ./playlist-export
  python3 scripts/playlists.py import --music-root ~/Dropbox/Tunes --in-dir ./playlist-export
  python3 scripts/playlists.py import --music-root ~/Dropbox/Tunes --in-dir ./playlist-export --overwrite
  python3 scripts/playlists.py export --music-root ~/Dropbox/Tunes --out-dir ./playlist-export --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FIELD_SEP = "\x1f"
SCRIPT_TIMEOUT = 120
TRACK_FETCH_TIMEOUT = 300


class MusicError(Exception):
    pass


@dataclass(frozen=True)
class MusicPlaylist:
    name: str
    persistent_id: str


@dataclass(frozen=True)
class TrackRef:
    relative_path: str | None = None
    name: str | None = None
    artist: str | None = None
    album: str | None = None

    def to_dict(self) -> dict:
        data: dict[str, str] = {}
        if self.relative_path:
            data["relative_path"] = self.relative_path
        if self.name:
            data["name"] = self.name
        if self.artist:
            data["artist"] = self.artist
        if self.album:
            data["album"] = self.album
        return data

    @classmethod
    def from_dict(cls, data: dict) -> TrackRef:
        return cls(
            relative_path=data.get("relative_path") or None,
            name=data.get("name") or None,
            artist=data.get("artist") or None,
            album=data.get("album") or None,
        )


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "playlist"


def escape_applescript(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def run_osascript(script: str, *, timeout: float = SCRIPT_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise MusicError(f"AppleScript timed out after {timeout:g}s") from exc
    if result.returncode != 0:
        raise MusicError(result.stderr.strip() or "AppleScript failed")
    return result.stdout.strip()


def ensure_music_running() -> None:
    run_osascript(
        """
        tell application "Music"
            if not running then launch
        end tell
        """
    )


def list_playlists() -> list[MusicPlaylist]:
    output = run_osascript(
        """
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
        """
    )
    playlists: list[MusicPlaylist] = []
    for line in output.splitlines():
        if not line.strip() or FIELD_SEP not in line:
            continue
        name, pid = line.split(FIELD_SEP, 1)
        if not pid.isdigit():
            continue
        playlists.append(MusicPlaylist(name=name, persistent_id=pid))
    return playlists


def get_playlist_tracks(playlist: MusicPlaylist, music_root: Path) -> list[TrackRef]:
    if not playlist.persistent_id.isdigit():
        raise MusicError(f"Invalid playlist id: {playlist.persistent_id!r}")
    output = run_osascript(
        f"""
        tell application "Music"
            set output to ""
            set targetPlaylist to first user playlist whose id is {playlist.persistent_id}
            repeat with t in tracks of targetPlaylist
                set trackLocation to ""
                set trackAlbum to ""
                try
                    set trackLocation to location of t as string
                end try
                try
                    set trackAlbum to album of t
                end try
                set output to output & (name of t) & tab & (artist of t) & tab & trackAlbum & tab & trackLocation & linefeed
            end repeat
            return output
        end tell
        """,
        timeout=TRACK_FETCH_TIMEOUT,
    )
    tracks: list[TrackRef] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 3)
        while len(parts) < 4:
            parts.append("")
        name, artist, album, location = parts
        rel = location_to_relative(location, music_root) if location else None
        tracks.append(
            TrackRef(
                relative_path=rel,
                name=name or None,
                artist=artist or None,
                album=album or None,
            )
        )
    return tracks


def location_to_relative(location: str, music_root: Path) -> str | None:
    if not location:
        return None
    path = Path(location.removeprefix("file://"))
    try:
        return str(path.resolve().relative_to(music_root.resolve()))
    except ValueError:
        return None


def create_playlist(name: str) -> str:
    return run_osascript(
        f'''
        tell application "Music"
            set p to make new user playlist with properties {{name:"{escape_applescript(name)}"}}
            return id of p as string
        end tell
        '''
    )


def delete_playlist(name: str) -> None:
    run_osascript(
        f'''
        tell application "Music"
            delete (first user playlist whose name is "{escape_applescript(name)}")
        end tell
        '''
    )


def clear_playlist(name: str) -> None:
    run_osascript(
        f'''
        tell application "Music"
            set targetPlaylist to first user playlist whose name is "{escape_applescript(name)}"
            delete every track of targetPlaylist
        end tell
        '''
    )


def add_track_by_path(playlist_name: str, file_path: Path) -> None:
    posix = str(file_path.resolve())
    run_osascript(
        f'''
        tell application "Music"
            set targetPlaylist to first user playlist whose name is "{escape_applescript(playlist_name)}"
            set trackFile to POSIX file "{posix}"
            set foundTracks to (every track of library playlist 1 whose location is trackFile)
            if (count of foundTracks) is 0 then
                set newTrack to add trackFile
            else
                set newTrack to item 1 of foundTracks
            end if
            duplicate newTrack to targetPlaylist
        end tell
        '''
    )


def add_track_by_metadata(
    playlist_name: str, name: str, artist: str | None, album: str | None
) -> None:
    clauses = [f'name is "{escape_applescript(name)}"']
    if artist:
        clauses.append(f'artist is "{escape_applescript(artist)}"')
    if album:
        clauses.append(f'album is "{escape_applescript(album)}"')
    whose = " and ".join(clauses)
    run_osascript(
        f'''
        tell application "Music"
            set targetPlaylist to first user playlist whose name is "{escape_applescript(playlist_name)}"
            set matches to (every track of library playlist 1 whose {whose})
            if (count of matches) is 0 then
                error "No library track matched metadata"
            end if
            duplicate item 1 of matches to targetPlaylist
        end tell
        '''
    )


def playlist_path(out_dir: Path, name: str) -> Path:
    return out_dir / f"{slugify(name)}.json"


def write_playlist_json(path: Path, name: str, tracks: list[TrackRef]) -> None:
    payload = {
        "name": name,
        "tracks": [t.to_dict() for t in tracks],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_playlist_json(path: Path) -> tuple[str, list[TrackRef]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{path}: missing playlist name")
    tracks_raw = data.get("tracks", [])
    if not isinstance(tracks_raw, list):
        raise ValueError(f"{path}: tracks must be a list")
    tracks = [TrackRef.from_dict(t) for t in tracks_raw if isinstance(t, dict)]
    return name.strip(), tracks


def cmd_export(args: argparse.Namespace) -> int:
    music_root: Path = args.music_root.resolve()
    out_dir: Path = args.out_dir.resolve()
    dry_run: bool = args.dry_run

    if not music_root.is_dir():
        print(f"error: music root does not exist: {music_root}", file=sys.stderr)
        return 1

    ensure_music_running()
    playlists = list_playlists()
    print(f"Found {len(playlists)} user playlist(s)")

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for playlist in playlists:
        print(f"Exporting: {playlist.name}")
        try:
            tracks = get_playlist_tracks(playlist, music_root)
        except MusicError as exc:
            print(f"  skip (error): {exc}", file=sys.stderr)
            continue
        path = playlist_path(out_dir, playlist.name)
        if dry_run:
            print(f"  would write {path} ({len(tracks)} track(s))")
        else:
            write_playlist_json(path, playlist.name, tracks)
            print(f"  wrote {path} ({len(tracks)} track(s))")
    return 0


def resolve_track(
    track: TrackRef, music_root: Path
) -> tuple[str, Path | None, tuple[str, str | None, str | None] | None]:
    """Return (status, path_or_none, metadata_or_none).

    status is one of: path, metadata, missing
    """
    if track.relative_path:
        abs_path = (music_root / track.relative_path).resolve()
        try:
            abs_path.relative_to(music_root.resolve())
        except ValueError:
            return "missing", None, None
        if abs_path.is_file():
            return "path", abs_path, None
    if track.name:
        return "metadata", None, (track.name, track.artist, track.album)
    return "missing", None, None


def cmd_import(args: argparse.Namespace) -> int:
    music_root: Path = args.music_root.resolve()
    in_dir: Path = args.in_dir.resolve()
    dry_run: bool = args.dry_run
    overwrite: bool = args.overwrite

    if not music_root.is_dir():
        print(f"error: music root does not exist: {music_root}", file=sys.stderr)
        return 1
    if not in_dir.is_dir():
        print(f"error: input directory does not exist: {in_dir}", file=sys.stderr)
        return 1

    files = sorted(in_dir.glob("*.json"))
    if not files:
        print(f"No JSON playlist files in {in_dir}")
        return 0

    ensure_music_running()
    existing = {p.name: p for p in list_playlists()}
    print(f"Importing {len(files)} playlist file(s)")

    for path in files:
        try:
            name, tracks = read_playlist_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"skip {path.name}: {exc}", file=sys.stderr)
            continue

        exists = name in existing
        if exists and not overwrite:
            print(f"Skip existing playlist (use --overwrite): {name}")
            continue

        action = "overwrite" if exists else "create"
        print(f"{action.capitalize()}: {name} ({len(tracks)} track(s) in file)")

        if dry_run:
            for track in tracks:
                status, file_path, meta = resolve_track(track, music_root)
                if status == "path":
                    print(f"  would add by path: {file_path}")
                elif status == "metadata":
                    assert meta is not None
                    print(
                        f"  would try metadata match: {meta[0]}"
                        + (f" / {meta[1]}" if meta[1] else "")
                    )
                else:
                    print(f"  would skip unmatched track: {track.to_dict()}")
            continue

        if exists and overwrite:
            clear_playlist(name)
        elif not exists:
            create_playlist(name)
            existing[name] = MusicPlaylist(name=name, persistent_id="")

        for track in tracks:
            status, file_path, meta = resolve_track(track, music_root)
            try:
                if status == "path" and file_path is not None:
                    add_track_by_path(name, file_path)
                    print(f"  added: {file_path.relative_to(music_root)}")
                elif status == "metadata" and meta is not None:
                    add_track_by_metadata(name, meta[0], meta[1], meta[2])
                    print(f"  added by metadata: {meta[0]}")
                else:
                    print(f"  skip unmatched: {track.to_dict()}")
            except MusicError as exc:
                print(f"  skip failed: {track.to_dict()} ({exc})", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export/import Apple Music playlists as JSON for machine-to-machine transfer."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export_p = sub.add_parser("export", help="Export playlists from Apple Music to JSON files")
    export_p.add_argument(
        "--music-root",
        type=Path,
        required=True,
        help="Root folder of your music files (used for relative paths)",
    )
    export_p.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory to write playlist JSON files",
    )
    export_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be exported without writing files",
    )
    export_p.set_defaults(func=cmd_export)

    import_p = sub.add_parser("import", help="Import playlists from JSON files into Apple Music")
    import_p.add_argument(
        "--music-root",
        type=Path,
        required=True,
        help="Root folder of your music files (used to resolve relative paths)",
    )
    import_p.add_argument(
        "--in-dir",
        type=Path,
        required=True,
        help="Directory containing playlist JSON files",
    )
    import_p.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing playlist's tracks with the imported file",
    )
    import_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without changing Music",
    )
    import_p.set_defaults(func=cmd_import)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except MusicError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
