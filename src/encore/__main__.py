import logging

from encore.app import EncoreApp
from encore.settings import SETTINGS_DIR


def main() -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(SETTINGS_DIR / "encore.log"),
            logging.StreamHandler(),
        ],
    )
    EncoreApp().run()


if __name__ == "__main__":
    main()
