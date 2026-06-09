"""MessageFlight entry point.

Run with: python message_flight.py
"""
import logging

from message_flight.tray_app import TrayApplication


def _setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


if __name__ == "__main__":
    _setup_logging()
    TrayApplication().run()
