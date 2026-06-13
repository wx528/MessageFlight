"""System tray icon, context menu, and application lifecycle."""
import logging
import random
import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPixmap, QPixmapCache
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QSystemTrayIcon

from message_flight.achievement_engine import AchievementEngine
from message_flight.achievements import ACHIEVEMENTS
from message_flight.autostart import is_auto_start_enabled, set_auto_start
from message_flight.config import (
    is_dnd_active,
    load_config,
    load_gamification_state,
    save_config,
    save_gamification_state,
)
from message_flight.demo_notifications import NOTIFICATIONS
from message_flight.flight_widget import FlightWidget
from message_flight.i18n import tr
from message_flight.notification_worker import WINSOK_AVAILABLE, NotificationWorker
from message_flight.persona_rewriter import PersonaRewriter
from message_flight.plane_presets import get_preset, list_available_presets
from message_flight.preset_editor import PresetEditorWindow
from message_flight.settings_dialog import SettingsDialog
from message_flight.stt_manager import STTManager
from message_flight.toast import ToastManager
from message_flight.tts_manager import TTSManager
from message_flight.voice_commands import VoiceCommand
from message_flight.wake_word import WakeWordInitError

logger = logging.getLogger(__name__)


class TrayApplication:
    def __init__(self) -> None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        # Limit Qt internal pixmap cache to prevent memory growth over long runs
        QPixmapCache.setCacheLimit(1024 * 50)  # 50 MB

        # Load persisted color scheme and hand it to the widget
        self.cfg = load_config()
        self.state = load_gamification_state()
        self.language = self.cfg.language
        self.widget: FlightWidget = FlightWidget(plane_colors=self.cfg.colors, **self.cfg.flight_kwargs)

        self.tts = TTSManager(self.cfg)

        self.persona = PersonaRewriter(
            api_key=self.cfg.minimax_subscription_key,
            preset_key=self.cfg.plane_preset_key,
            system_prompt=self._persona_prompt_for(self.cfg.plane_preset_key),
            enabled=self.cfg.persona_enabled,
        )
        self.persona.rewrite_finished.connect(self._on_persona_rewritten)

        # Gamification engine (Task 17)
        self._engine = AchievementEngine(self.state)
        self._toast_manager = ToastManager()
        self._engine.unlocked.connect(self._on_achievement_unlocked)
        self._engine.check_time_based()

        # Click on the plane cycles to the next preset
        self.widget.plane.clicked.connect(self._on_plane_clicked)
        self.widget.plane.clicked.connect(self._engine.record_plane_click)

        # 系统托盘
        self.tray_icon = QSystemTrayIcon(self._create_tray_icon("idle"), self.app)
        self.tray_icon.setToolTip("MessageFlight")

        self.menu = QMenu()

        self.action_show = QAction(tr("tray.show", self.language), self.menu)
        self.action_show.triggered.connect(self._show_widget)
        self.menu.addAction(self.action_show)

        self.action_pause = QAction(tr("tray.pause", self.language), self.menu)
        self.action_pause.setCheckable(True)
        self.action_pause.triggered.connect(self._toggle_pause)
        self.menu.addAction(self.action_pause)

        self.action_demo = QAction(tr("tray.demo", self.language), self.menu)
        self.action_demo.triggered.connect(self._send_demo_notification)
        self.menu.addAction(self.action_demo)

        # 免打扰模式（manual toggle only; scheduled window is read-only here）
        self.action_dnd = QAction(tr("tray.dnd", self.language), self.menu)
        self.action_dnd.setCheckable(True)
        self.action_dnd.setChecked(self.cfg.dnd_enabled)
        self.action_dnd.triggered.connect(self._toggle_dnd)
        self.menu.addAction(self.action_dnd)

        self.action_settings = QAction(tr("tray.settings", self.language), self.menu)
        self.action_settings.triggered.connect(self._open_settings)
        self.menu.addAction(self.action_settings)

        self.action_preset_editor = QAction(tr("tray.preset_editor", self.language), self.menu)
        self.action_preset_editor.triggered.connect(self._open_preset_editor)
        self.menu.addAction(self.action_preset_editor)

        self.menu.addSeparator()

        # 通知权限状态
        self.action_notif_status = QAction(tr("tray.notification_status.checking", self.language), self.menu)
        self.action_notif_status.setEnabled(False)
        self.menu.addAction(self.action_notif_status)

        self.menu.addSeparator()

        self.action_autostart = QAction(tr("tray.autostart", self.language), self.menu)
        self.action_autostart.setCheckable(True)
        self.action_autostart.setChecked(is_auto_start_enabled())
        self.action_autostart.triggered.connect(self._toggle_autostart)
        self.menu.addAction(self.action_autostart)

        self.menu.addSeparator()

        self.action_quit = QAction(tr("tray.quit", self.language), self.menu)
        self.action_quit.triggered.connect(self._quit)
        self.menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

        # 启动通知监听线程
        self.notifier = None

        # Voice input (v0.4.0+) — only construct if enabled in config
        self._stt_manager: Optional[STTManager] = None
        self._voice_icons: dict[str, QIcon] = {}
        if self.cfg.stt_enabled:
            self._init_stt_manager()

        if WINSOK_AVAILABLE:
            self.notifier = NotificationWorker()
            self.notifier.notification_received.connect(self._on_real_notification)
            self.notifier.access_status_changed.connect(self._on_access_status)
            self.notifier.start()
        else:
            self.action_notif_status.setText(tr("tray.notification_status.unavailable", self.language))

    def _init_stt_manager(self) -> None:
        """Construct STTManager + tray icons; wire signals. Logs + disables on failure."""
        if self._stt_manager is not None:
            logger.debug("TrayApplication: STTManager already constructed; skipping")
            return
        if not self.cfg.stt_enabled:
            return
        try:
            self._voice_icons["idle"] = self._create_tray_icon("idle")
            self._voice_icons["listening"] = self._create_tray_icon("listening")
            self._voice_icons["processing"] = self._create_tray_icon("processing")
        except Exception as e:
            logger.error("TrayApplication: failed to build voice icons: %s", e)

        try:
            self._stt_manager = STTManager(self.cfg)
        except WakeWordInitError as e:
            logger.error("TrayApplication: wake word model init failed: %s", e)
            self._toast_manager.show_toast(
                title=tr("voice.init_failed", self.language),
                description="",
                icon="⚠️",
            )
            self._stt_manager = None
            return
        except Exception as e:
            logger.error("TrayApplication: failed to create STTManager: %s", e)
            self._toast_manager.show_toast(
                title=tr("voice.init_failed", self.language),
                description="",
                icon="⚠️",
            )
            self._stt_manager = None
            return

        self._stt_manager.state_changed.connect(self._on_voice_state_changed)
        self._stt_manager.command_recognized.connect(self._on_voice_command)
        self._stt_manager.transcript_failed.connect(self._on_voice_transcript_failed)
        self._stt_manager.listening_started.connect(self._on_voice_listening_started)
        self._stt_manager.start()

    def _on_voice_state_changed(self, state: str) -> None:
        icon = self._voice_icons.get(state)
        if icon is not None:
            self.tray_icon.setIcon(icon)

    def _on_voice_command(self, command_value: str) -> None:
        logger.info("TrayApplication: voice command received: %s", command_value)
        try:
            cmd = VoiceCommand(command_value)
        except ValueError:
            logger.error("TrayApplication: unknown voice command %r", command_value)
            return
        if cmd == VoiceCommand.PAUSE:
            self._toggle_pause(True)
            self._toast_manager.show_toast(
                title=tr("voice.cmd.pause", self.language), description="", icon="⏸",
            )
        elif cmd == VoiceCommand.RESUME:
            self._toggle_pause(False)
            self._toast_manager.show_toast(
                title=tr("voice.cmd.resume", self.language), description="", icon="▶",
            )
        elif cmd == VoiceCommand.NEXT_PRESET:
            self._on_plane_clicked()
            self._toast_manager.show_toast(
                title=tr("voice.cmd.next_preset", self.language), description="", icon="✈",
            )
        elif cmd == VoiceCommand.TOGGLE_DND:
            new_state = not self.action_dnd.isChecked()
            self._toggle_dnd(new_state)
            self.action_dnd.setChecked(new_state)
            key = "voice.cmd.dnd_on" if new_state else "voice.cmd.dnd_off"
            self._toast_manager.show_toast(
                title=tr(key, self.language), description="", icon="🔕" if new_state else "🔔",
            )
        elif cmd == VoiceCommand.SEND_DEMO:
            self._send_demo_notification()

    def _on_voice_transcript_failed(self, reason: str) -> None:
        logger.info("TrayApplication: voice transcript failed: %s", reason)
        if reason == "empty":
            self._toast_manager.show_toast(
                title=tr("voice.no_speech", self.language),
                description="",
                icon="🔇",
            )
        elif reason == "no_match":
            self._toast_manager.show_toast(
                title=tr("voice.not_understood", self.language),
                description="",
                icon="🤔",
            )
        elif reason == "network":
            self._toast_manager.show_toast(
                title=tr("voice.network_error", self.language),
                description="",
                icon="⚠️",
            )
        elif reason == "mic":
            self._toast_manager.show_toast(
                title=tr("voice.mic_unavailable", self.language),
                description="",
                icon="⚠️",
            )

    def _on_voice_listening_started(self) -> None:
        self._toast_manager.show_toast(
            title=tr("voice.listening", self.language),
            description="",
            icon="🎤",
        )

    def _create_tray_icon(self, state: str = "idle") -> QIcon:
        """Build a tray icon for the given voice state.

        ``state`` is "idle" / "listening" / "processing". For non-idle
        states, a colored ring is drawn around the base plane icon to
        indicate that voice input is active.
        """
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

        # Voice state indicator
        if state == "listening":
            painter.setBrush(QColor("#FF0000"))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawEllipse(56, 56, 20, 20)
        elif state == "processing":
            painter.setBrush(QColor("#FFA500"))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawEllipse(56, 56, 20, 20)

        painter.end()
        return QIcon(pixmap)

    def _show_widget(self):
        self.widget.show()
        self.widget.raise_()
        self.widget.activateWindow()

    def _refresh_translated_labels(self) -> None:
        self.action_show.setText(tr("tray.show", self.language))
        self.action_pause.setText(
            tr("tray.resume", self.language) if self.action_pause.isChecked() else tr("tray.pause", self.language)
        )
        self.action_demo.setText(tr("tray.demo", self.language))
        self.action_dnd.setText(tr("tray.dnd", self.language))
        self.action_settings.setText(tr("tray.settings", self.language))
        self.action_preset_editor.setText(tr("tray.preset_editor", self.language))
        self.action_autostart.setText(tr("tray.autostart", self.language))
        self.action_quit.setText(tr("tray.quit", self.language))

    def _toggle_pause(self, checked: bool):
        self.widget.set_paused(checked)
        self.action_pause.setText(
            tr("tray.resume", self.language) if checked else tr("tray.pause", self.language)
        )

    def _toggle_dnd(self, checked: bool):
        """Toggle manual Do-Not-Disturb and persist the choice."""
        self.cfg.dnd_enabled = bool(checked)
        try:
            save_config(self.cfg)
        except Exception as e:
            logger.warning("Failed to persist DND toggle: %s", e)

    def _toggle_autostart(self, checked: bool):
        try:
            set_auto_start(checked)
        except Exception as e:
            self.action_autostart.setChecked(not checked)
            print(f"设置开机自启失败: {e}")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_widget()

    def _on_real_notification(self, app_name: str, text: str) -> None:
        """收到真实系统通知（受 DND 控制；演示通知不受影响）"""
        if is_dnd_active(self.cfg):
            logger.info("[DND] Suppressed real notification from %s", app_name)
            return
        display = f"[{app_name}] {text}"
        if len(display) > 80:
            display = display[:77] + "..."
        logger.info("[Real Notification] %s", display)
        self._engine.record_notification(app_name)
        result = self.persona.rewrite(display)
        if result is not None:
            self._on_persona_rewritten(result or display)

    def _on_persona_rewritten(self, rewritten: str) -> None:
        spoken = rewritten
        if not spoken:
            # The signal may not fire on sync short-circuit, but if it does
            # carry empty content, fall through silently. TTS already spoke
            # the original via the sync return path.
            return
        self.tts.speak(spoken)
        self._engine.record_tts_speak()
        self.widget.enqueue_notification(spoken)
        self._show_widget()

    def _on_achievement_unlocked(self, achievement_id: str) -> None:
        achievement = next((a for a in ACHIEVEMENTS if a.id == achievement_id), None)
        if achievement is None:
            return
        if achievement.unlock_preset_key:
            self.state.unlocked_presets.add(achievement.unlock_preset_key)
        try:
            save_gamification_state(self.state)
        except Exception as e:
            logger.warning("Failed to persist achievement unlock: %s", e)
        name = tr(achievement.name_i18n_key, self.language)
        self._toast_manager.show_toast(
            title=tr("achievement.unlocked.title", self.language),
            description=name,
            icon=achievement.icon or "🏆",
        )

    def _on_plane_clicked(self) -> None:
        """Cycle the active plane preset (airplane → rocket → ufo → bird → airplane).

        Resets the per-preset params to defaults and propagates the change to
        the TTS voice profile and the persona rewriter. Persists the new
        preset key to QSettings.
        """
        cycle_order = [k for k, _, _ in list_available_presets(self.state.unlocked_presets)]
        if not cycle_order:
            return
        try:
            idx = cycle_order.index(self.cfg.plane_preset_key)
            new_key = cycle_order[(idx + 1) % len(cycle_order)]
        except ValueError:
            new_key = cycle_order[0]
        self.cfg.plane_preset_key = new_key
        self.cfg.plane_preset_params_json = ""
        try:
            save_config(self.cfg)
        except Exception as e:
            logger.warning("Failed to persist preset change: %s", e)
        self._apply_preset_to_widget(new_key, "")
        self._engine.record_preset_used(new_key)
        preset = get_preset(new_key)
        self.tts.set_voice(preset.tts_voice_id, preset.tts_speed, preset.tts_pitch)
        self.persona.set_config(
            api_key=self.cfg.minimax_subscription_key,
            preset_key=new_key,
            system_prompt=self._persona_prompt_for(new_key),
            enabled=self.cfg.persona_enabled,
        )

    def _persona_prompt_for(self, preset_key: str) -> str:
        prompts = self._load_persona_prompts()
        if preset_key in prompts:
            return prompts[preset_key]
        return get_preset(preset_key).system_prompt

    def _load_persona_prompts(self) -> dict[str, str]:
        import json
        if not self.cfg.persona_prompts_json:
            return {}
        try:
            data = json.loads(self.cfg.persona_prompts_json)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def _on_access_status(self, status: int):
        """通知权限状态更新"""
        labels = {
            0: tr("status.unspecified", self.language),
            1: tr("status.allowed", self.language),
            2: tr("status.denied", self.language),
        }
        self.action_notif_status.setText(
            tr(
                "tray.notification_status",
                self.language,
                label=labels.get(status, tr("status.unknown", self.language)),
                status=status,
            )
        )

    def _send_demo_notification(self):
        """Pick a random demo notification, route it through PersonaRewriter,
        then speak it and fire it on the widget.

        Demo notifications bypass DND so the user can always test the
        notification path even when real notifications are silenced.
        """
        text = random.choice(NOTIFICATIONS)
        logger.info("[Demo Notification] %s", text)
        result = self.persona.rewrite(text)
        if result is not None:
            self._on_persona_rewritten(result or text)

    def _open_settings(self):
        """Open the settings dialog (color scheme + flight mode). On accept, save config and apply changes.

        Uses the in-memory ``self.cfg`` (which reflects any unsaved
        toggles like DND or preset cycling) rather than re-reading
        from disk, so the dialog never shows stale data.
        """
        dlg = SettingsDialog(self.cfg, self.state.unlocked_presets, self.menu)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_cfg = dlg.get_result()
            persona_enabled, persona_prompts_json = dlg.get_persona_result()
            new_cfg.persona_enabled = persona_enabled
            new_cfg.persona_prompts_json = persona_prompts_json

            # Voice input: construct on enable, tear down on disable,
            # or rebuild if the wake word changed while staying enabled.
            voice_was_enabled = self.cfg.stt_enabled
            voice_now_enabled = new_cfg.stt_enabled
            wake_word_changed = (
                voice_was_enabled
                and voice_now_enabled
                and self.cfg.stt_wake_word != new_cfg.stt_wake_word
            )

            save_config(new_cfg)
            self.cfg = new_cfg
            self.language = new_cfg.language
            self._refresh_translated_labels()
            self.widget.plane.update_colors(**new_cfg.colors)
            self.widget.set_flight_kwargs(**new_cfg.flight_kwargs)
            self.tts.update_config(new_cfg)
            self.persona.set_config(
                api_key=new_cfg.minimax_subscription_key,
                preset_key=new_cfg.plane_preset_key,
                system_prompt=self._persona_prompt_for(new_cfg.plane_preset_key),
                enabled=new_cfg.persona_enabled,
            )

            # Voice input: construct on enable, tear down on disable.
            # Without this, enabling voice in settings required an app
            # restart before the STTManager actually came online.
            if not voice_was_enabled and voice_now_enabled:
                logger.info("TrayApplication: voice input enabled, constructing STTManager")
                self._init_stt_manager()
            elif voice_was_enabled and not voice_now_enabled:
                logger.info("TrayApplication: voice input disabled, tearing down STTManager")
                if self._stt_manager is not None:
                    try:
                        self._stt_manager.stop()
                    except Exception as e:
                        logger.warning("TrayApplication: STTManager.stop() raised: %s", e)
                    self._stt_manager = None
            elif wake_word_changed:
                logger.info(
                    "TrayApplication: wake word changed %s -> %s, rebuilding STTManager",
                    self.cfg.stt_wake_word, new_cfg.stt_wake_word,
                )
                if self._stt_manager is not None:
                    try:
                        self._stt_manager.stop()
                    except Exception as e:
                        logger.warning("TrayApplication: STTManager.stop() raised: %s", e)
                    self._stt_manager = None
                self._init_stt_manager()

    def _open_preset_editor(self):
        dlg = PresetEditorWindow(self.cfg, self.menu)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            preset_key, params_json = dlg.get_result()
            self.cfg.plane_preset_key = preset_key
            self.cfg.plane_preset_params_json = params_json
            save_config(self.cfg)
            self._apply_preset_to_widget(preset_key, params_json)
            self._engine.record_preset_used(preset_key)

    def _apply_preset_to_widget(self, preset_key: str, params_json: str) -> None:
        import dataclasses
        import json

        from message_flight.plane_presets import get_preset
        preset = get_preset(preset_key)
        if params_json:
            try:
                data = json.loads(params_json)
                default = preset.get_default_params()
                params = dataclasses.replace(
                    default,
                    **{k: v for k, v in data.items() if hasattr(default, k)},
                )
            except (json.JSONDecodeError, TypeError):
                params = preset.get_default_params()
        else:
            params = preset.get_default_params()
        self.widget.plane.apply_preset(preset, params)

    def _quit(self):
        if self._stt_manager is not None:
            self._stt_manager.stop()
        if self.notifier:
            self.notifier.stop()
        self.app.quit()

    def run(self):
        print("MessageFlight started!")
        print("ESC: 隐藏窗口  |  托盘图标: 右键菜单 / 双击显示")
        sys.exit(self.app.exec())
