from encore import __version__
from encore.icons import app_icon_path

ABOUT_MESSAGE = (
    f"Sync Apple Music playlists across Macs via Dropbox.\n\nVersion {__version__}"
)


def show_about() -> None:
    import rumps

    icon = app_icon_path()
    rumps.alert(
        "Encore",
        ABOUT_MESSAGE,
        icon_path=str(icon) if icon.is_file() else None,
    )
