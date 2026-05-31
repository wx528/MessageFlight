import sys
import os
import subprocess
import random
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMenu, QSystemTrayIcon
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer, pyqtProperty, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QFontMetrics, QAction, QIcon, QPixmap

# ============ Windows Notification ============
try:
    from winsdk.windows.ui.notifications.management import UserNotificationListener
    from winsdk.windows.ui.notifications import NotificationKinds, KnownNotificationBindings
    WINSOK_AVAILABLE = True
except ImportError:
    WINSOK_AVAILABLE = False


# ============ 辅助函数 ============
def _startup_folder():
    return os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")


def _shortcut_path():
    return os.path.join(_startup_folder(), "MessageFlight.lnk")


def _exe_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def is_auto_start_enabled():
    return os.path.exists(_shortcut_path())


def set_auto_start(enabled: bool):
    shortcut = _shortcut_path()
    if enabled:
        target = _exe_path()
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{shortcut}"); '
            f'$s.TargetPath = "{target}"; '
            f'$s.WorkingDirectory = "{os.path.dirname(target)}"; '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-Command", ps_cmd], check=True, capture_output=True)
    else:
        if os.path.exists(shortcut):
            os.remove(shortcut)


# ============ 模拟通知消息池 ============
NOTIFICATIONS = [
    "Meeting with Andrew in 5 min",
    "You have a new message from Mom",
    "Lunch time!",
    "Stand-up meeting starts now",
    "Don't forget to drink water",
    "Code review requested by Tom",
    "Daily report due in 30 min",
    "New email: Project Update",
]


# ============ 通知监听线程 ============
class NotificationWorker(QThread):
    """后台线程：轮询 Windows 通知中心，发现新通知时发射信号"""
    notification_received = pyqtSignal(str, str)  # app_name, message_text
    access_status_changed = pyqtSignal(int)  # 0=Unspecified, 1=Allowed, 2=Denied

    def __init__(self):
        super().__init__()
        self._running = True
        self._seen_ids = set()
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
                        next(it, None)

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


# ============ 飞机+横幅 组件 ============
class PlaneBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._banner_width = 280
        self._banner_height = 50
        self._text = ""
        self._plane_color = QColor("#FF69B4")
        self._banner_color = QColor("#FFB6C1")
        self._text_color = QColor("#FFFFFF")
        self._plane_offset = 0.0
        self.setFixedSize(self._banner_width + 80, 80)

    def set_text(self, text: str):
        self._text = text
        fm = QFontMetrics(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        tw = fm.horizontalAdvance(text) + 40
        self._banner_width = max(200, tw)
        self.setFixedSize(self._banner_width + 80, 80)
        self.update()

    def get_plane_offset(self):
        return self._plane_offset

    def set_plane_offset(self, val: float):
        self._plane_offset = val
        self.update()

    plane_offset = pyqtProperty(float, get_plane_offset, set_plane_offset)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        float_y = int(self._plane_offset * 6)

        painter.save()
        painter.translate(self._banner_width + 10, 15 + float_y)
        self._draw_plane(painter)
        painter.restore()

        banner_y = 20 + float_y
        path = QPainterPath()
        rect_w = self._banner_width
        rect_h = self._banner_height
        radius = 12

        path.moveTo(radius, banner_y)
        path.lineTo(rect_w - radius, banner_y)
        path.arcTo(rect_w - radius * 2, banner_y, radius * 2, radius * 2, 90, -90)
        path.lineTo(rect_w, banner_y + rect_h - radius)
        path.arcTo(rect_w - radius * 2, banner_y + rect_h - radius * 2, radius * 2, radius * 2, 0, -90)
        path.lineTo(radius, banner_y + rect_h)
        path.arcTo(0, banner_y + rect_h - radius * 2, radius * 2, radius * 2, -90, -90)
        path.lineTo(0, banner_y + radius)
        path.arcTo(0, banner_y, radius * 2, radius * 2, 180, -90)
        path.closeSubpath()

        tail_x = rect_w
        tail_y = banner_y + rect_h // 2
        path.moveTo(tail_x, tail_y - 6)
        path.lineTo(tail_x + 10, tail_y)
        path.lineTo(tail_x, tail_y + 6)
        path.closeSubpath()

        painter.fillPath(path, self._banner_color)

        painter.setPen(self._text_color)
        font = QFont("Microsoft YaHei", 12, QFont.Weight.Bold)
        painter.setFont(font)
        fm = QFontMetrics(font)
        text_y = banner_y + (rect_h + fm.ascent() - fm.descent()) // 2
        painter.drawText(20, text_y, self._text)
        painter.end()

    def _draw_plane(self, painter: QPainter):
        c = self._plane_color
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(c)
        painter.drawEllipse(10, 18, 45, 22)
        painter.drawEllipse(48, 19, 14, 20)

        wing_color = QColor("#FF1493")
        painter.setBrush(wing_color)
        wing_path = QPainterPath()
        wing_path.moveTo(25, 25)
        wing_path.lineTo(15, 8)
        wing_path.lineTo(35, 8)
        wing_path.lineTo(40, 25)
        wing_path.closeSubpath()
        painter.drawPath(wing_path)

        tail_path = QPainterPath()
        tail_path.moveTo(12, 28)
        tail_path.lineTo(2, 18)
        tail_path.lineTo(12, 22)
        tail_path.closeSubpath()
        painter.drawPath(tail_path)

        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(52, 24, 6, 6)
        painter.drawEllipse(38, 24, 5, 5)

        painter.setBrush(QColor("#FF69B4"))
        painter.drawEllipse(60, 26, 4, 6)
        painter.setBrush(QColor("#FFB6C1"))
        painter.drawEllipse(56, 22, 12, 3)
        painter.drawEllipse(56, 33, 12, 3)


# ============ 主窗口 ============
class FlightWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen().geometry()
        self.screen_w = screen.width()
        self.screen_h = screen.height()
        self.setGeometry(0, 0, self.screen_w, self.screen_h)

        self.plane = PlaneBanner(self)
        self.plane.set_text(NOTIFICATIONS[0])

        start_y = self.screen_h // 4 + random.randint(-100, 100)
        self.plane.move(-self.plane.width(), start_y)

        self._setup_float_animation()
        self._setup_fly_animation()

        self.msg_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_message)
        self.timer.start(5000)

        self._paused = False

    def _setup_float_animation(self):
        self.float_anim = QPropertyAnimation(self.plane, b"plane_offset")
        self.float_anim.setDuration(1500)
        self.float_anim.setStartValue(0.0)
        self.float_anim.setEndValue(1.0)
        self.float_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.float_anim.setLoopCount(-1)
        self.float_anim.start()

    def _setup_fly_animation(self):
        start_y = self.screen_h // 4 + random.randint(-80, 80)
        end_y = start_y + random.randint(-30, 30)
        self.fly_anim = QPropertyAnimation(self.plane, b"pos")
        self.fly_anim.setDuration(8000)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.fly_anim.finished.connect(self._on_fly_finished)
        self.fly_anim.start()

    def _on_fly_finished(self):
        start_y = self.screen_h // 5 + random.randint(-120, 150)
        end_y = start_y + random.randint(-40, 40)
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.start()

    def _next_message(self):
        self.msg_index = (self.msg_index + 1) % len(NOTIFICATIONS)
        self.plane.set_text(NOTIFICATIONS[self.msg_index])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()

    def set_paused(self, paused: bool):
        self._paused = paused
        if paused:
            self.fly_anim.pause()
            self.float_anim.pause()
            self.timer.stop()
        else:
            self.fly_anim.resume()
            self.float_anim.resume()
            self.timer.start()

    def is_paused(self):
        return self._paused

    def show_notification(self, text: str):
        """显示一条真实通知，并重置飞行动画让飞机立刻从左侧飞出"""
        self.plane.set_text(text)
        # 重置位置到左侧外，确保用户能立刻看到
        start_y = self.screen_h // 5 + random.randint(-100, 100)
        end_y = start_y + random.randint(-40, 40)
        self.fly_anim.stop()
        self.fly_anim.setStartValue(QPoint(-self.plane.width(), start_y))
        self.fly_anim.setEndValue(QPoint(self.screen_w + 50, end_y))
        self.fly_anim.start()
        # 暂停假数据轮播 15 秒，让用户看清真实通知
        self.timer.stop()
        QTimer.singleShot(15000, self.timer.start)


# ============ 托盘应用 ============
class TrayApplication:
    def __init__(self):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.widget = FlightWidget()
        self.widget.show()

        # 系统托盘
        self.tray_icon = QSystemTrayIcon(self._create_tray_icon(), self.app)
        self.tray_icon.setToolTip("MessageFlight")

        self.menu = QMenu()

        self.action_show = QAction("显示飞机", self.menu)
        self.action_show.triggered.connect(self._show_widget)
        self.menu.addAction(self.action_show)

        self.action_pause = QAction("暂停飞行", self.menu)
        self.action_pause.setCheckable(True)
        self.action_pause.triggered.connect(self._toggle_pause)
        self.menu.addAction(self.action_pause)

        self.menu.addSeparator()

        # 通知权限状态
        self.action_notif_status = QAction("通知权限: 检查中...", self.menu)
        self.action_notif_status.setEnabled(False)
        self.menu.addAction(self.action_notif_status)

        self.menu.addSeparator()

        self.action_autostart = QAction("开机自启", self.menu)
        self.action_autostart.setCheckable(True)
        self.action_autostart.setChecked(is_auto_start_enabled())
        self.action_autostart.triggered.connect(self._toggle_autostart)
        self.menu.addAction(self.action_autostart)

        self.menu.addSeparator()

        self.action_quit = QAction("退出", self.menu)
        self.action_quit.triggered.connect(self._quit)
        self.menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

        # 启动通知监听线程
        self.notifier = None
        if WINSOK_AVAILABLE:
            self.notifier = NotificationWorker()
            self.notifier.notification_received.connect(self._on_real_notification)
            self.notifier.access_status_changed.connect(self._on_access_status)
            self.notifier.start()
        else:
            self.action_notif_status.setText("通知权限: winsdk 未安装")

    def _create_tray_icon(self) -> QIcon:
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 80, size / 80)

        c = QColor("#FF69B4")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(c)
        painter.drawEllipse(10, 18, 45, 22)
        painter.drawEllipse(48, 19, 14, 20)

        wing = QColor("#FF1493")
        painter.setBrush(wing)
        wp = QPainterPath()
        wp.moveTo(25, 25)
        wp.lineTo(15, 8)
        wp.lineTo(35, 8)
        wp.lineTo(40, 25)
        wp.closeSubpath()
        painter.drawPath(wp)

        tp = QPainterPath()
        tp.moveTo(12, 28)
        tp.lineTo(2, 18)
        tp.lineTo(12, 22)
        tp.closeSubpath()
        painter.drawPath(tp)

        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(52, 24, 6, 6)
        painter.drawEllipse(38, 24, 5, 5)
        painter.end()
        return QIcon(pixmap)

    def _show_widget(self):
        self.widget.show()
        self.widget.raise_()
        self.widget.activateWindow()

    def _toggle_pause(self, checked: bool):
        self.widget.set_paused(checked)
        self.action_pause.setText("继续飞行" if checked else "暂停飞行")

    def _toggle_autostart(self, checked: bool):
        try:
            set_auto_start(checked)
        except Exception as e:
            self.action_autostart.setChecked(not checked)
            print(f"设置开机自启失败: {e}")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_widget()

    def _on_real_notification(self, app_name: str, text: str):
        """收到真实系统通知"""
        display = f"[{app_name}] {text}"
        # 截断过长的文本
        if len(display) > 80:
            display = display[:77] + "..."
        print(f"[Real Notification] {display}")
        self.widget.show_notification(display)
        self._show_widget()

    def _on_access_status(self, status: int):
        """通知权限状态更新"""
        labels = {0: "未指定", 1: "已允许", 2: "已拒绝"}
        self.action_notif_status.setText(f"通知权限: {labels.get(status, '未知')} ({status})")

    def _quit(self):
        if self.notifier:
            self.notifier.stop()
        self.app.quit()

    def run(self):
        print("MessageFlight started!")
        print("ESC: 隐藏窗口  |  托盘图标: 右键菜单 / 双击显示")
        sys.exit(self.app.exec())


# ============ 启动 ============
if __name__ == "__main__":
    tray_app = TrayApplication()
    tray_app.run()
