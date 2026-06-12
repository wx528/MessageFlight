import logging
import os

from message_flight.tray_app import TrayApplication


def main() -> None:
    level_name = os.environ.get("MESSAGEFLIGHT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s.%(msecs)03d %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    TrayApplication().run()
