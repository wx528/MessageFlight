"""Tests for lightweight UI translations."""

from message_flight.i18n import LANGUAGES, detect_system_language, language_name, tr


def test_supported_languages_include_target_locales():
    assert set(LANGUAGES) == {"zh", "en", "ja", "ko", "id", "th", "vi", "ms"}
    assert language_name("ja") == "日本語"
    assert language_name("ko") == "한국어"
    assert language_name("id") == "Bahasa Indonesia"
    assert language_name("th") == "ไทย"
    assert language_name("vi") == "Tiếng Việt"
    assert language_name("ms") == "Bahasa Melayu"


def test_translates_core_tray_labels():
    assert tr("tray.show", "en") == "Show plane"
    assert tr("tray.show", "ja") == "飛行機を表示"
    assert tr("tray.show", "ko") == "비행기 표시"
    assert tr("tray.show", "id") == "Tampilkan pesawat"
    assert tr("tray.show", "th") == "แสดงเครื่องบิน"
    assert tr("tray.show", "vi") == "Hiển thị máy bay"
    assert tr("tray.show", "ms") == "Tunjukkan pesawat"
    assert tr("tray.show", "zh") == "显示飞机"


def test_unknown_language_falls_back_to_chinese():
    assert tr("tray.quit", "xx") == "退出"


def test_detect_system_language_maps_locale_prefixes():
    assert detect_system_language("en_US") == "en"
    assert detect_system_language("ja_JP") == "ja"
    assert detect_system_language("ko_KR") == "ko"
    assert detect_system_language("id_ID") == "id"
    assert detect_system_language("th_TH") == "th"
    assert detect_system_language("vi_VN") == "vi"
    assert detect_system_language("ms_MY") == "ms"
    assert detect_system_language("fr_FR") == "zh"
