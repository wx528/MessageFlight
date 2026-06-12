"""Minimal wake-word test script.

Loads OpenWakeWordListener, opens the default mic, listens for the
configured wake word, and prints each detection. Runs for
WAKE_WORD_TEST_SECS seconds (default 30) then exits.

Usage:
    uv run python scripts/test_wake_word.py
    uv run python scripts/test_wake_word.py --wake-word alexa --seconds 60

This script does NOT touch the rest of the app — it isolates the
wake-word pipeline so you can debug whether the issue is with the
listener, the mic, the model, or downstream wiring.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

# Configure logging to show what the listener is doing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("wake_word_test")


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal wake-word test")
    parser.add_argument(
        "--wake-word",
        default="hey_jarvis",
        choices=["hey_jarvis", "alexa", "hey_mycroft"],
        help="Wake-word model to use (default: hey_jarvis)",
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=30,
        help="How long to listen before exiting (default: 30)",
    )
    args = parser.parse_args()

    from PyQt6.QtCore import QCoreApplication, QTimer

    from message_flight.wake_word import OpenWakeWordListener, WakeWordInitError

    app = QCoreApplication(sys.argv)

    detection_count = 0
    start_time = time.monotonic()

    def on_wake_word() -> None:
        nonlocal detection_count
        detection_count += 1
        elapsed = time.monotonic() - start_time
        logger.info(">>> WAKE WORD DETECTED (#%d) at t=%.1fs <<<", detection_count, elapsed)

    def on_error(msg: str) -> None:
        logger.error("listener error: %s", msg)

    logger.info("Constructing OpenWakeWordListener(model=%r)...", args.wake_word)
    try:
        listener = OpenWakeWordListener(model_name=args.wake_word, debounce_seconds=1.0)
    except WakeWordInitError as e:
        logger.error("Failed to init listener: %s", e)
        return 1

    listener.wake_word_detected.connect(on_wake_word)
    listener.error_occurred.connect(on_error)

    logger.info("Starting mic... speak the wake word now.")
    listener.start()
    if not listener.is_running:
        logger.error("Listener failed to start. Check mic permissions and try again.")
        return 1

    logger.info("Listening for %d seconds. Press Ctrl+C to stop early.", args.seconds)
    logger.info("Wake word: '%s'", args.wake_word)
    logger.info("Sensitivity: default 0.5 (lower = more sensitive)")

    def shutdown():
        logger.info("Stopping listener...")
        listener.stop()
        logger.info("Total detections: %d", detection_count)
        app.quit()

    QTimer.singleShot(args.seconds * 1000, shutdown)

    try:
        return app.exec()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        shutdown()
        return 0


if __name__ == "__main__":
    sys.exit(main())
