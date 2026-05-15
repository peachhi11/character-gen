#!/usr/bin/env python3
from __future__ import annotations

import logging
from datetime import datetime
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from character_app.config import AppPaths
from character_app.ui import build_main_window


def setup_logging() -> logging.Logger:
    paths = AppPaths()
    paths.ensure_directories()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = paths.logs_dir / f"charactergen_clean_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("charactergen")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Character Generator")
    app.setApplicationVersion("3.0.0")
    app.setOrganizationName("CharacterGen")

    logger = setup_logging()
    logger.info("Starting clean CharacterGen build")

    try:
        window = build_main_window(logger)
        window.show()
        window.raise_()
        window.activateWindow()
        return app.exec()
    except Exception as exc:
        logger.exception("Startup failure")
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Character Generator could not start:\n\n{exc}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
