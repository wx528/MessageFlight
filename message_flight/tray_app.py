"""System tray icon, context menu, and application lifecycle."""
import logging
import random
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QSystemTrayIcon

from message_flight.autostart import is_auto_start_enabled, set_auto_start
from message_flight.config import load_config, save_config
from message_flight.demo_notifications import NOTIFICATIONS
from message_flight.flight_widget import FlightWidget
from message_flight.notification_worker import NotificationWorker, WINSOK_AVAILABLE
from message_flight.settings_dialog import SettingsDialog
from message_flight.tts_manager import TTSManager

logger = logging.getLogger(__name__)


class TrayApplication:
    def __init__(self):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Load persisted color scheme and hand it to the widget
        cfg = load_config()
        self.widget = FlightWidget(plane_colors=cfg.colors, **cfg.flight_kwargs)
        self.widget.show()

        self.tts = TTSManager(cfg)

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

        self.action_demo = QAction("发送演示通知", self.menu)
        self.action_demo.triggered.connect(self._send_demo_notification)
        self.menu.addAction(self.action_demo)

        self.action_settings = QAction("设置...", self.menu)
        self.action_settings.triggered.connect(self._open_settings)
        self.menu.addAction(self.action_settings)

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
        logger.info("[Real Notification] %s", display)
        self.tts.speak(display)
        self.widget.show_notification(display)
        self._show_widget()

    def _on_access_status(self, status: int):
        """通知权限状态更新"""
        labels = {0: "未指定", 1: "已允许", 2: "已拒绝"}
        self.action_notif_status.setText(f"通知权限: {labels.get(status, '未知')} ({status})")

    def _send_demo_notification(self):
        """Pick a random demo notification and fire it on the widget."""
        text = random.choice(NOTIFICATIONS)
        self.widget.show_notification(text)

    def _open_settings(self):
        """Open the settings dialog (color scheme + flight mode). On accept, save config and apply changes."""
        dlg = SettingsDialog(load_config(), self.menu)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_cfg = dlg.get_result()
            save_config(new_cfg)
            self.widget.plane.update_colors(**new_cfg.colors)
            self.widget.set_flight_kwargs(**new_cfg.flight_kwargs)
            self.tts.update_config(new_cfg)

    def _quit(self):
        if self.notifier:
            self.notifier.stop()
        self.app.quit()

    def run(self):
        print("MessageFlight started!")
        print("ESC: 隐藏窗口  |  托盘图标: 右键菜单 / 双击显示")
        sys.exit(self.app.exec())
