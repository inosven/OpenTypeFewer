"""Internationalization manager for VoicePad."""

import logging

from voicepad.modules.i18n.locales import en, zh

LOCALE_MAP = {
    "en": en.STRINGS,
    "zh": zh.STRINGS,
}

logger = logging.getLogger("voicepad.i18n")


class I18nManager:
    def __init__(self, language: str = "en"):
        self.current_language = language
        self.active_strings = LOCALE_MAP.get(language, LOCALE_MAP["en"])
        self.fallback_strings = LOCALE_MAP["en"]

    def translate(self, string_key: str, **format_kwargs) -> str:
        raw_string = self.active_strings.get(string_key)
        if raw_string is None:
            raw_string = self.fallback_strings.get(string_key)
        if raw_string is None:
            logger.warning(f"Missing i18n key: {string_key}")
            return string_key

        if format_kwargs:
            try:
                return raw_string.format(**format_kwargs)
            except KeyError as format_error:
                logger.warning(f"Format error for key {string_key}: {format_error}")
                return raw_string

        return raw_string

    def set_language(self, language: str) -> None:
        if language not in LOCALE_MAP:
            logger.warning(f"Unknown language: {language}, falling back to en")
            language = "en"
        self.current_language = language
        self.active_strings = LOCALE_MAP[language]

    def get_language(self) -> str:
        return self.current_language
