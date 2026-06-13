from setuptools import setup

APP = ["src/encore/__main__.py"]
DATA_FILES = []
ICON_FILE = "assets/icons/encore.icns"
OPTIONS = {
    "argv_emulation": False,
    "iconfile": ICON_FILE,
    "plist": {
        "CFBundleName": "Encore",
        "CFBundleDisplayName": "Encore",
        "CFBundleIdentifier": "com.encore.app",
        "CFBundleVersion": "0.1.0",
        "LSUIElement": True,
        "NSAppleEventsUsageDescription": "Encore needs to control Music to sync playlists.",
    },
    "packages": ["encore", "rumps", "watchdog"],
}

setup(
    app=APP,
    name="Encore",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
