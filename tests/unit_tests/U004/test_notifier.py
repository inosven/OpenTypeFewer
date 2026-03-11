import pytest
from unittest.mock import patch, MagicMock

from voicepad.modules.notify.notifier import Notifier


def _create_mock_config(notification_enabled=True, sound_enabled=True):
    mock_config = MagicMock()
    def mock_get_value(key, default=None):
        config_values = {
            "notification.enabled": notification_enabled,
            "notification.sound_enabled": sound_enabled,
            "notification.sound_start": "start.wav",
            "notification.sound_stop": "stop.wav",
            "notification.sound_done": "done.wav",
            "notification.sound_error": "error.wav",
        }
        return config_values.get(key, default)
    mock_config.get_value = mock_get_value
    return mock_config


def _create_mock_i18n():
    mock_i18n = MagicMock()
    mock_i18n.translate.return_value = "Test notification"
    return mock_i18n


def test_send_notification_calls_plyer():
    mock_config = _create_mock_config()
    mock_i18n = _create_mock_i18n()
    notifier = Notifier(mock_config, mock_i18n)

    mock_notification = MagicMock()
    with patch.dict("sys.modules", {"plyer": MagicMock(notification=mock_notification)}):
        notifier.send_notification("Test Title", "Test Message")
        mock_notification.notify.assert_called_once()


def test_notification_disabled_skips():
    mock_config = _create_mock_config(notification_enabled=False)
    mock_i18n = _create_mock_i18n()
    notifier = Notifier(mock_config, mock_i18n)

    mock_notification = MagicMock()
    with patch.dict("sys.modules", {"plyer": MagicMock(notification=mock_notification)}):
        notifier.send_notification("Title", "Message")
        mock_notification.notify.assert_not_called()


def test_play_sound_disabled_skips():
    mock_config = _create_mock_config(sound_enabled=False)
    mock_i18n = _create_mock_i18n()
    notifier = Notifier(mock_config, mock_i18n)

    with patch.object(notifier, "_play_sound_file") as mock_play:
        notifier.play_sound("start")
        mock_play.assert_not_called()


def test_play_sound_missing_file_logs_warning():
    mock_config = _create_mock_config()
    mock_i18n = _create_mock_i18n()
    notifier = Notifier(mock_config, mock_i18n)

    with patch("os.path.exists", return_value=False):
        notifier.play_sound("start")
