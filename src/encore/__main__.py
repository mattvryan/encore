from encore.app import EncoreApp
from encore.logging_config import configure_logging
from encore.settings import SETTINGS_DIR


def main() -> None:
    configure_logging(SETTINGS_DIR / "encore.log")
    EncoreApp().run()


if __name__ == "__main__":
    main()
