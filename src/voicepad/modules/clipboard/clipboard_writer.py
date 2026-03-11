"""Clipboard write operations for VoicePad."""

import logging

import pyperclip

logger = logging.getLogger("voicepad.clipboard")


def copy_to_clipboard(text_content: str) -> bool:
    if not text_content:
        return False

    if not isinstance(text_content, str):
        return False

    try:
        pyperclip.copy(text_content)
    except Exception as clipboard_error:
        logger.error(f"Clipboard write failed: {clipboard_error}")
        return False

    return True
