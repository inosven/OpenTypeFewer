import pytest
from unittest.mock import patch, MagicMock

from voicepad.modules.clipboard.clipboard_writer import copy_to_clipboard


def test_copy_english_text():
    with patch("voicepad.modules.clipboard.clipboard_writer.pyperclip") as mock_pyperclip:
        success = copy_to_clipboard("Hello world")
        assert success is True
        mock_pyperclip.copy.assert_called_once_with("Hello world")


def test_copy_chinese_text():
    with patch("voicepad.modules.clipboard.clipboard_writer.pyperclip") as mock_pyperclip:
        success = copy_to_clipboard("你好世界")
        assert success is True
        mock_pyperclip.copy.assert_called_once_with("你好世界")


def test_copy_mixed_text():
    with patch("voicepad.modules.clipboard.clipboard_writer.pyperclip") as mock_pyperclip:
        mixed_text = "Hello 你好 World 世界"
        success = copy_to_clipboard(mixed_text)
        assert success is True
        mock_pyperclip.copy.assert_called_once_with(mixed_text)


def test_copy_empty_string_returns_false():
    success = copy_to_clipboard("")
    assert success is False


def test_copy_none_returns_false():
    success = copy_to_clipboard(None)
    assert success is False


def test_copy_non_string_returns_false():
    success = copy_to_clipboard(12345)
    assert success is False


def test_clipboard_exception_returns_false():
    with patch("voicepad.modules.clipboard.clipboard_writer.pyperclip") as mock_pyperclip:
        mock_pyperclip.copy.side_effect = RuntimeError("No clipboard available")
        success = copy_to_clipboard("test")
        assert success is False
