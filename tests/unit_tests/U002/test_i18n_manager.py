import pytest

from voicepad.modules.i18n.i18n_manager import I18nManager


def test_english_string_lookup():
    i18n_manager = I18nManager("en")
    result_text = i18n_manager.translate("tray.title")
    assert result_text == "VoicePad"


def test_chinese_string_lookup():
    i18n_manager = I18nManager("zh")
    result_text = i18n_manager.translate("tray.processing")
    assert result_text == "处理方式"


def test_fallback_to_english_for_unknown_language():
    i18n_manager = I18nManager("fr")
    result_text = i18n_manager.translate("tray.title")
    assert result_text == "VoicePad"


def test_missing_key_returns_key_string():
    i18n_manager = I18nManager("en")
    result_text = i18n_manager.translate("nonexistent.key")
    assert result_text == "nonexistent.key"


def test_format_placeholders():
    i18n_manager = I18nManager("en")
    result_text = i18n_manager.translate(
        "notify.mode_switched", processing="polish", language="zh"
    )
    assert result_text == "Processing: polish | Language: zh"


def test_chinese_format_placeholders():
    i18n_manager = I18nManager("zh")
    result_text = i18n_manager.translate(
        "notify.mode_switched", processing="润色", language="中文"
    )
    assert result_text == "处理：润色 | 语言：中文"


def test_switch_language_at_runtime():
    i18n_manager = I18nManager("en")
    assert i18n_manager.translate("tray.settings") == "Settings"

    i18n_manager.set_language("zh")
    assert i18n_manager.translate("tray.settings") == "设置"
    assert i18n_manager.get_language() == "zh"


def test_switch_to_unknown_falls_back():
    i18n_manager = I18nManager("en")
    i18n_manager.set_language("ja")
    assert i18n_manager.get_language() == "en"
    assert i18n_manager.translate("tray.title") == "VoicePad"


def test_all_english_keys_present():
    from voicepad.modules.i18n.locales.en import STRINGS as en_strings
    from voicepad.modules.i18n.locales.zh import STRINGS as zh_strings

    for string_key in en_strings:
        assert string_key in zh_strings, f"Key '{string_key}' missing from zh locale"

    for string_key in zh_strings:
        assert string_key in en_strings, f"Key '{string_key}' missing from en locale"
