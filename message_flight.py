"""MessageFlight entry point.

Run with: python message_flight.py
"""
import logging
import os

from message_flight.tray_app import TrayApplication


def _setup_logging() -> None:
    """Configure logging for the application."""
    level_name = os.environ.get("MESSAGEFLIGHT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


if __name__ == "__main__":
    _setup_logging()
    TrayApplication().run()
