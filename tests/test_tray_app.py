"""Tests for tray app (TTS integration in Task 04, preset editor menu in Task 12)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock, patch


def test_tray_app_starts_hidden_in_tray():
    """Starting the tray app must not show the flight widget until a notification or user action."""
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget") as mock_widget_cls, \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        _ = TrayApplication()

    mock_widget_cls.return_value.show.assert_not_called()


def test_on_real_notification_calls_tts_speak():
    """When a real notification arrives, tray_app must call tts.speak() with the display text."""
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        app = TrayApplication()
        app.cfg = AppConfig(dnd_enabled=False)
        app.persona = MagicMock()
        app.persona.rewrite.return_value = "[WeChat] hello"
        app._on_real_notification("WeChat", "hello")
        mock_tts.speak.assert_called_once_with("[WeChat] hello")


def test_on_real_notification_drops_when_dnd_enabled():
    """When DND is on, real notifications must NOT trigger TTS or the widget."""
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        app = TrayApplication()
        app.cfg = AppConfig(dnd_enabled=True)
        app._on_real_notification("WeChat", "hello")
        mock_tts.speak.assert_not_called()
        app.widget.enqueue_notification.assert_not_called()


def test_send_demo_notification_bypasses_dnd():
    """Demo notifications must NOT be filtered by DND."""
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        app = TrayApplication()
        app.cfg = AppConfig(dnd_enabled=True)
        app._send_demo_notification()
        mock_tts.speak.assert_called_once()
        app.widget.enqueue_notification.assert_called_once()


def test_tray_app_uses_configured_language_for_menu_labels():
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction") as mock_action, \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.load_config", return_value=AppConfig(language="en")), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        _ = TrayApplication()

    action_texts = [call.args[0] for call in mock_action.call_args_list if call.args]
    assert "Show plane" in action_texts
    assert "Do Not Disturb" in action_texts
    assert "Quit" in action_texts


def test_tray_app_has_dnd_menu_item():
    """免打扰 menu item must be present and checkable."""
    from message_flight.tray_app import TrayApplication
    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction") as mock_action, \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        _ = TrayApplication()
    # Find the QAction("免打扰", ...) instance by checking the construction call
    dnd_constructed = any(
        call.args and call.args[0] == "免打扰"
        for call in mock_action.call_args_list
    )
    assert dnd_constructed, "免打扰 menu item not created"
    # The QAction instance must have had setCheckable(True) called on it
    set_checkable_calls = [
        call for call in mock_action.return_value.setCheckable.call_args_list
        if call.args and call.args[0] is True
    ]
    assert set_checkable_calls, "免打扰 action not marked checkable"


def test_tray_app_has_preset_editor_menu_item():
    from message_flight.tray_app import TrayApplication
    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction") as mock_action, \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        _ = TrayApplication()
    action_texts = [call.args[0] for call in mock_action.call_args_list if call.args]
    assert "飞船编辑器" in action_texts


def test_apply_preset_to_widget():
    """Test that _apply_preset_to_widget correctly deserializes and applies presets."""
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget") as mock_widget_cls, \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        app = TrayApplication()
        app.widget = mock_widget_cls.return_value
        app.widget.plane = MagicMock()

        # Test with airplane preset and custom params
        params_json = '{"plane_color": "#FF0000", "wing_color": "#00FF00"}'
        app._apply_preset_to_widget("airplane", params_json)

        # Verify apply_preset was called
        assert app.widget.plane.apply_preset.called
        args = app.widget.plane.apply_preset.call_args
        assert args[0][1].plane_color == "#FF0000"
        assert args[0][1].wing_color == "#00FF00"


def test_real_notification_uses_persona_rewriter_async_path():
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        app = TrayApplication()
        app.cfg = AppConfig(dnd_enabled=False, plane_preset_key="airplane", persona_enabled=True)
        app.persona = MagicMock()
        app.persona.rewrite.return_value = None

        app._on_real_notification("WeChat", "hello")

        # persona.rewrite was called with the formatted display
        app.persona.rewrite.assert_called_once_with("[WeChat] hello")
        # TTS and widget NOT yet called (waiting on async signal)
        app.tts.speak.assert_not_called()
        app.widget.enqueue_notification.assert_not_called()


def test_real_notification_synchronous_fallback_when_rewrite_returns_string():
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        app = TrayApplication()
        app.cfg = AppConfig(dnd_enabled=False, plane_preset_key="airplane", persona_enabled=True)
        app.persona = MagicMock()
        app.persona.rewrite.return_value = "[WeChat] hello (rewritten)"

        app._on_real_notification("WeChat", "hello")

        app.persona.rewrite.assert_called_once_with("[WeChat] hello")
        app.tts.speak.assert_called_once_with("[WeChat] hello (rewritten)")
        app.widget.enqueue_notification.assert_called_once_with("[WeChat] hello (rewritten)")


def test_on_persona_rewritten_falls_back_to_original_on_empty():
    """When the async path somehow fires the slot with empty content, the
    slot must NOT call TTS. The original-fallback is the caller's job (it
    passes ``result or display`` to the slot from the sync return value).
    """
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        app = TrayApplication()
        app.cfg = AppConfig(dnd_enabled=False, plane_preset_key="airplane")
        app._on_persona_rewritten("")
        app.tts.speak.assert_not_called()
        app.widget.enqueue_notification.assert_not_called()


def test_tray_app_initializes_persona_rewriter():
    from message_flight.persona_rewriter import PersonaRewriter
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"):
        app = TrayApplication()
        assert isinstance(app.persona, PersonaRewriter)
