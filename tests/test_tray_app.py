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
        app.persona = MagicMock()
        app.persona.rewrite.return_value = "REWRITTEN"
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


def test_send_demo_notification_routes_through_persona_rewriter():
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
        app.cfg = AppConfig(dnd_enabled=True, plane_preset_key="airplane", persona_enabled=True)
        app.persona = MagicMock()
        app.persona.rewrite.return_value = "机长：演示消息已重写"

        app._send_demo_notification()

        # persona.rewrite was called with a non-empty demo text
        assert app.persona.rewrite.call_count == 1
        called_text = app.persona.rewrite.call_args[0][0]
        assert isinstance(called_text, str) and called_text

        # Sync path: _on_persona_rewritten invoked with the rewritten text
        app.tts.speak.assert_called_once_with("机长：演示消息已重写")
        app.widget.enqueue_notification.assert_called_once_with("机长：演示消息已重写")


def test_send_demo_notification_async_path_does_not_speak_yet():
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
        app.persona = MagicMock()
        app.persona.rewrite.return_value = None  # async path

        app._send_demo_notification()

        app.persona.rewrite.assert_called_once()
        # TTS/widget not yet called — waiting on rewrite_finished
        app.tts.speak.assert_not_called()
        app.widget.enqueue_notification.assert_not_called()


# ---------------------------------------------------------------------------
# Task 13: click on plane cycles to next preset
# ---------------------------------------------------------------------------


def test_on_plane_clicked_cycles_to_next_preset():
    """Clicking the plane should cycle airplane → rocket → ufo → bird → airplane."""
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager") as mock_tts_cls, \
         patch("message_flight.tray_app.TrayApplication._apply_preset_to_widget") as mock_apply, \
         patch("message_flight.tray_app.save_config"):
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        app = TrayApplication()
        app.cfg = AppConfig(plane_preset_key="airplane", plane_preset_params_json="")
        app.persona = MagicMock()

        app._on_plane_clicked()

        assert app.cfg.plane_preset_key == "rocket"
        # params reset to default on cycle
        assert app.cfg.plane_preset_params_json == ""
        mock_apply.assert_called_once_with("rocket", "")
        # TTS voice profile updated to rocket preset
        mock_tts.set_voice.assert_called_once()
        voice_args = mock_tts.set_voice.call_args.args
        assert voice_args[0] == "male-qn-jingying"  # rocket voice_id (see preset)
        # Persona rewriter reconfigured for the new preset
        app.persona.set_config.assert_called_once()
        assert app.persona.set_config.call_args.kwargs["preset_key"] == "rocket"


def test_on_plane_clicked_wraps_around():
    """The last preset in the cycle should wrap back to the first."""
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager") as mock_tts_cls, \
         patch("message_flight.tray_app.TrayApplication._apply_preset_to_widget") as mock_apply, \
         patch("message_flight.tray_app.save_config"):
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        app = TrayApplication()
        app.cfg = AppConfig(plane_preset_key="bird", plane_preset_params_json="")
        app.persona = MagicMock()

        app._on_plane_clicked()

        assert app.cfg.plane_preset_key == "airplane"
        mock_apply.assert_called_once_with("airplane", "")


def test_on_plane_clicked_clears_custom_params():
    """Switching preset via click must drop any user-tuned params_json."""
    from message_flight.config import AppConfig
    from message_flight.tray_app import TrayApplication

    with patch("message_flight.tray_app.QApplication"), \
         patch("message_flight.tray_app.QSystemTrayIcon"), \
         patch("message_flight.tray_app.FlightWidget"), \
         patch("message_flight.tray_app.QMenu"), \
         patch("message_flight.tray_app.QAction"), \
         patch("message_flight.tray_app.WINSOK_AVAILABLE", False), \
         patch("message_flight.tray_app.TrayApplication._create_tray_icon", return_value=MagicMock()), \
         patch("message_flight.tray_app.TTSManager"), \
         patch("message_flight.tray_app.TrayApplication._apply_preset_to_widget") as mock_apply, \
         patch("message_flight.tray_app.save_config"):
        app = TrayApplication()
        app.cfg = AppConfig(
            plane_preset_key="airplane",
            plane_preset_params_json='{"plane_color": "#000000"}',
        )
        app.persona = MagicMock()

        app._on_plane_clicked()

        assert app.cfg.plane_preset_params_json == ""
        mock_apply.assert_called_once()
        # _apply_preset_to_widget must be invoked with empty params to use defaults
        assert mock_apply.call_args.args[1] == ""


def test_tray_app_connects_banner_clicked_signal():
    """The TrayApplication must wire plane.clicked so click cycles preset."""
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
        # widget.plane is a MagicMock (FlightWidget is mocked)
        # Verify the .clicked signal of the banner was connected to a slot
        app.widget.plane.clicked.connect.assert_called_once_with(app._on_plane_clicked)
