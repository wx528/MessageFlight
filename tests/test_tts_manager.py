
from message_flight.config import AppConfig


def test_tts_manager_default_provider():
    """TTSManager with default config must use SAPIReader."""
    from message_flight.tts_manager import TTSManager
    cfg = AppConfig(tts_provider="sapi")
    mgr = TTSManager(cfg)
    assert mgr._current_provider_name == "sapi"


def test_tts_manager_switch_provider():
    """update_config must switch the active provider."""
    from message_flight.tts_manager import TTSManager
    cfg = AppConfig(tts_provider="sapi")
    mgr = TTSManager(cfg)

    new_cfg = AppConfig(tts_provider="minimax", minimax_subscription_key="key")
    mgr.update_config(new_cfg)
    assert mgr._current_provider_name == "minimax"


def test_tts_manager_fallback_signal(qtbot):
    """MiniMax error must trigger fallback_triggered signal."""
    from message_flight.tts_manager import TTSManager
    cfg = AppConfig(tts_provider="minimax", minimax_subscription_key="")
    mgr = TTSManager(cfg)

    with qtbot.waitSignal(mgr.fallback_triggered, timeout=1000):
        # Empty key triggers error immediately
        mgr.speak("test")
