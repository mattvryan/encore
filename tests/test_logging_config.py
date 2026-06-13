import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from encore.logging_config import LOG_BACKUP_COUNT, configure_logging


def test_configure_logging_uses_daily_rotation(tmp_path: Path) -> None:
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    try:
        log_path = tmp_path / "encore.log"
        configure_logging(log_path)

        file_handlers = [
            handler
            for handler in root.handlers
            if isinstance(handler, TimedRotatingFileHandler)
        ]

        assert len(file_handlers) == 1
        handler = file_handlers[0]
        assert handler.baseFilename == str(log_path)
        assert handler.when == "D"
        assert handler.backupCount == LOG_BACKUP_COUNT
        assert handler.encoding == "utf-8"

        logging.info("hello")
        assert log_path.read_text(encoding="utf-8").endswith("hello\n")
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
