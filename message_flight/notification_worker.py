"""Background thread for listening to the Windows notification center."""
import asyncio

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from winsdk.windows.ui.notifications.management import UserNotificationListener
    from winsdk.windows.ui.notifications import NotificationKinds, KnownNotificationBindings
    WINSOK_AVAILABLE = True
except ImportError:
    WINSOK_AVAILABLE = False


class NotificationWorker(QThread):
    """后台线程：轮询 Windows 通知中心，发现新通知时发射信号"""
    notification_received = pyqtSignal(str, str)  # app_name, message_text
    access_status_changed = pyqtSignal(int)  # 0=Unspecified, 1=Allowed, 2=Denied

    def __init__(self):
        super().__init__()
        self._running = True
        self._seen_ids = set()
        self._initialized = False
        self._loop = None
        self._access_status = 0
