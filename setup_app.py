from setuptools import Distribution, setup

from encore import __version__

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
        "CFBundleVersion": __version__,
        "LSUIElement": True,
        "NSAppleEventsUsageDescription": "Encore needs to control Music to sync playlists.",
    },
    "packages": ["encore", "rumps", "watchdog"],
}


class Py2appDistribution(Distribution):
    def parse_config_files(self, filenames=None, ignore_option_errors=False):
        super().parse_config_files(filenames, ignore_option_errors)
        # py2app 0.28.9+ rejects non-empty install_requires; setuptools
        # loads dependencies from pyproject.toml after Distribution.__init__.
        self.install_requires = []


setup(
    app=APP,
    name="Encore",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    distclass=Py2appDistribution,
)
