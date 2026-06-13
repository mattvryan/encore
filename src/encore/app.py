import logging
import threading
from pathlib import Path

import rumps

from encore.icons import menubar_icon_path
from encore.services.apple_music import AppleMusicService
from encore.services.folder_watcher import FolderWatcher
from encore.services.library_import import LibraryImportService
from encore.services.playlist_file import PlaylistFileStore
from encore.services.retry_queue import RetryQueue
from encore.services.sync_orchestrator import SyncOrchestrator
from encore.settings import Settings
from encore.storage.mapping_store import MappingStore

logger = logging.getLogger(__name__)


class EncoreApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(
            "Encore",
            icon=str(menubar_icon_path()),
            quit_button=None,
        )
        self.settings = Settings.load()
        self._orchestrator: SyncOrchestrator | None = None
        self._watcher: FolderWatcher | None = None
        self._syncing = False
        self._build_menu()
        if self.settings.music_root:
            self._start_services()
        self._timer = rumps.Timer(self._on_poll, 30)
        self._timer.start()

    def _build_menu(self) -> None:
        self.menu = [
            rumps.MenuItem("Status: Idle", callback=None),
            "Sync Now",
            "Open Sync Folder",
            "Choose Music Folder...",
            rumps.MenuItem("Launch at Login", callback=self._toggle_launch_at_login),
            None,
            "Quit",
        ]

    def _start_services(self) -> None:
        root = self.settings.music_root
        sync_dir = self.settings.sync_dir
        if root is None or sync_dir is None:
            return
        apple_music = AppleMusicService(root)
        playlist_store = PlaylistFileStore(sync_dir)
        mapping_store = MappingStore(self.settings.state_path)
        library_import = LibraryImportService(root, apple_music)
        retry_queue = RetryQueue()
        self._orchestrator = SyncOrchestrator(
            root,
            apple_music,
            playlist_store,
            mapping_store,
            library_import,
            retry_queue,
        )
        self._watcher = FolderWatcher(
            music_root=root,
            sync_dir=sync_dir,
            on_audio_created=lambda p: self._run_async(
                self._orchestrator.handle_audio_created, p
            ),
            on_audio_deleted=lambda p: self._run_async(
                self._orchestrator.handle_audio_deleted, p
            ),
            on_playlist_changed=lambda p: self._run_async(
                self._orchestrator.apply_playlist_file, p
            ),
            on_playlist_deleted=lambda p: self._run_async(
                self._orchestrator.handle_playlist_file_deleted, p
            ),
        )
        self._watcher.start()

    def _run_async(self, func, *args) -> None:
        threading.Thread(target=func, args=args, daemon=True).start()

    def _on_poll(self, _) -> None:
        if self._orchestrator and not self._syncing:
            self._run_async(self._do_sync)

    @rumps.clicked("Sync Now")
    def sync_now(self, _) -> None:
        if not self._orchestrator:
            rumps.alert("Encore", "Choose a music folder first.")
            return
        self._run_async(self._do_sync)

    def _do_sync(self) -> None:
        if not self._orchestrator:
            return
        self._syncing = True
        self._set_status("Syncing...")
        try:
            self._orchestrator.sync_all()
            exhausted = self._orchestrator.exhausted_count
            if exhausted:
                self._set_status(f"{exhausted} track(s) not found")
            else:
                self._set_status("Idle")
        except Exception as exc:
            logger.exception("Sync failed")
            self._set_status(f"Error: {exc}")
        finally:
            self._syncing = False

    def _set_status(self, text: str) -> None:
        self.menu["Status: Idle"].title = f"Status: {text}"

    @rumps.clicked("Open Sync Folder")
    def open_sync_folder(self, _) -> None:
        if not self.settings.sync_dir:
            rumps.alert("Encore", "Choose a music folder first.")
            return
        import subprocess

        subprocess.run(["open", str(self.settings.sync_dir)])

    @rumps.clicked("Choose Music Folder...")
    def choose_music_folder(self, _) -> None:
        import subprocess

        result = subprocess.run(
            [
                "osascript",
                "-e",
                'POSIX path of (choose folder with prompt "Select Dropbox Music folder")',
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return
        path = Path(result.stdout.strip())
        self.settings.music_root = path
        self.settings.save()
        self._start_services()
        rumps.notification("Encore", "", f"Music folder: {path}")

    def _toggle_launch_at_login(self, sender) -> None:
        from encore.services.launch_at_login import set_launch_at_login

        self.settings.launch_at_login = not self.settings.launch_at_login
        sender.state = self.settings.launch_at_login
        self.settings.save()
        set_launch_at_login(self.settings.launch_at_login)

    @rumps.clicked("Quit")
    def quit_app(self, _) -> None:
        if self._watcher:
            self._watcher.stop()
        rumps.quit_application()
