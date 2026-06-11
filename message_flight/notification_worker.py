"""Background thread for listening to the Windows notification center."""
import asyncio
from typing import Set

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from winsdk.windows.ui.notifications import KnownNotificationBindings, NotificationKinds
    from winsdk.windows.ui.notifications.management import UserNotificationListener
    WINSOK_AVAILABLE = True
except ImportError:
    WINSOK_AVAILABLE = False


class NotificationWorker(QThread):
    """后台线程：轮询 Windows 通知中心，发现新通知时发射信号"""
    notification_received = pyqtSignal(str, str)  # app_name, message_text
    access_status_changed = pyqtSignal(int)  # 0=Unspecified, 1=Allowed, 2=Denied

    def __init__(self) -> None:
        super().__init__()
        self._running = True
        self._seen_ids: Set[int] = set()
        self._initialized = False

    def run(self):
        if not WINSOK_AVAILABLE:
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while self._running:
                try:
                    access, notifications = loop.run_until_complete(self._poll())
                    self.access_status_changed.emit(access)

                    if access == 1:
                        if not self._initialized:
                            # 第一次：把当前所有通知标记为已见过，避免历史通知刷屏
                            for n in notifications:
                                self._seen_ids.add(n['id'])
                            self._initialized = True
                        else:
                            for n in notifications:
                                if n['id'] not in self._seen_ids:
                                    self._seen_ids.add(n['id'])
                                    self.notification_received.emit(n['app'], n['text'])

                            # 定期清理旧 ID，防止无限增长
                            if len(self._seen_ids) > 500:
                                current_ids = {n['id'] for n in notifications}
                                self._seen_ids = current_ids | set(
                                    list(self._seen_ids)[-200:]
                                )
                except Exception as e:
                    print(f"Notification poll error: {e}")

                self.msleep(2000)
        finally:
            loop.close()

    async def _poll(self):
        listener = UserNotificationListener.current
        access = listener.get_access_status()
        if access != 1:
            return access, []

        notifications = await listener.get_notifications_async(NotificationKinds.TOAST)
        result = []
        for n in notifications:
            try:
                app_name = "Unknown"
                if hasattr(n, 'app_info') and n.app_info:
                    app_name = n.app_info.display_info.display_name

                binding = n.notification.visual.get_binding(KnownNotificationBindings.toast_generic)
                lines = []
                if binding:
                    texts = binding.get_text_elements()
                    it = iter(texts)
                    while it.has_current:
                        lines.append(it.current.text)
                        it.move_next()

                if lines:
                    result.append({
                        'id': n.id,
                        'app': app_name,
                        'text': ' | '.join(lines)
                    })
            except Exception:
                pass
        return access, result

    def stop(self):
        self._running = False
        self.wait(1500)
