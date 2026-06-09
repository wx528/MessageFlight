"""MessageFlight entry point.

Run with: python message_flight.py
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from message_flight.tray_app import TrayApplication


if __name__ == "__main__":
    TrayApplication().run()
