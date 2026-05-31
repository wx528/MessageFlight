import sys
import os
import subprocess
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMenu, QSystemTrayIcon
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QFontMetrics, QAction, QIcon, QPixmap

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


def _startup_folder():
    """Windows 启动文件夹路径"""
    return os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")


def _shortcut_path():
    """开机自启快捷方式路径"""
    return os.path.join(_startup_folder(), "MessageFlight.lnk")


def _exe_path():
    """当前运行的可执行文件/脚本路径"""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def is_auto_start_enabled():
    """检查是否已设置开机自启"""
    return os.path.exists(_shortcut_path())


def set_auto_start(enabled: bool):
    """设置/取消开机自启（通过创建/删除启动文件夹快捷方式）"""
    shortcut = _shortcut_path()
    if enabled:
        target = _exe_path()
        # 用 PowerShell 创建快捷方式
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


# ============ 飞机+横幅 组件 ============
class PlaneBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._banner_width = 280
        self._banner_height = 50
        self._text = ""
        self._plane_color = QColor("#FF69B4")  # 热粉色
        self._banner_color = QColor("#FFB6C1")  # 浅粉色
        self._text_color = QColor("#FFFFFF")
        self._plane_offset = 0.0  # 0~1 用于做轻微上下浮动
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

        # 绘制飞机
        painter.save()
        painter.translate(self._banner_width + 10, 15 + float_y)
        self._draw_plane(painter)
        painter.restore()

        # 绘制横幅背景
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

        # 绘制文字
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
        """ESC 隐藏到托盘"""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()

    def set_paused(self, paused: bool):
        """暂停/继续动画"""
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


# ============ 托盘应用 ============
class TrayApplication:
    def __init__(self):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(sys.argv)
        # 关闭窗口时不退出程序，只有托盘菜单退出才结束
        self.app.setQuitOnLastWindowClosed(False)

        self.widget = FlightWidget()
        self.widget.show()

        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self._create_tray_icon(), self.app)
        self.tray_icon.setToolTip("MessageFlight")

        # 构建右键菜单
        self.menu = QMenu()

        self.action_show = QAction("显示飞机", self.menu)
        self.action_show.triggered.connect(self._show_widget)
        self.menu.addAction(self.action_show)

        self.action_pause = QAction("暂停飞行", self.menu)
        self.action_pause.setCheckable(True)
        self.action_pause.triggered.connect(self._toggle_pause)
        self.menu.addAction(self.action_pause)

        self.menu.addSeparator()

        self.action_autostart = QAction("开机自启", self.menu)
        self.action_autostart.setCheckable(True)
        self.action_autostart.setChecked(is_auto_start_enabled())
        self.action_autostart.triggered.connect(self._toggle_autostart)
        self.menu.addAction(self.action_autostart)

        self.menu.addSeparator()

        self.action_quit = QAction("退出", self.menu)
        self.action_quit.triggered.connect(self.app.quit)
        self.menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _create_tray_icon(self) -> QIcon:
        """绘制一个粉色小飞机作为托盘图标"""
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

    def run(self):
        print("MessageFlight started!")
        print("ESC: 隐藏窗口  |  托盘图标: 右键菜单 / 双击显示")
        sys.exit(self.app.exec())


# ============ 启动 ============
if __name__ == "__main__":
    tray_app = TrayApplication()
    tray_app.run()
