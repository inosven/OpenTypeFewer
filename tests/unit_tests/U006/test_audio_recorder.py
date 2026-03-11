import pytest
from unittest.mock import MagicMock, patch

from voicepad.modules.recorder.audio_recorder import AudioRecorder


def _create_mock_config():
    mock_config = MagicMock()
    def mock_get_value(key, default=None):
        config_values = {
            "audio.sample_rate": 16000,
            "audio.channels": 1,
            "audio.silence_threshold": 500,
            "audio.silence_duration": 2.0,
        }
        return config_values.get(key, default)
    mock_config.get_value = mock_get_value
    return mock_config


def test_initial_state_not_recording():
    mock_config = _create_mock_config()
    recorder = AudioRecorder(mock_config)
    assert recorder.is_recording() is False


def test_stop_without_start_returns_none():
    mock_config = _create_mock_config()
    recorder = AudioRecorder(mock_config)
    result_path = recorder.stop_recording()
    assert result_path is None


def test_double_start_returns_false():
    mock_config = _create_mock_config()
    recorder = AudioRecorder(mock_config)
    recorder.recording_active = True
    result = recorder.start_recording()
    assert result is False


@pytest.mark.hardware
def test_start_and_stop_creates_wav():
    import time

    mock_config = _create_mock_config()
    recorder = AudioRecorder(mock_config)

    started = recorder.start_recording()
    assert started is True
    assert recorder.is_recording() is True

    time.sleep(0.5)
    output_path = recorder.stop_recording()

    assert output_path is not None
    assert output_path.endswith(".wav")
    assert recorder.is_recording() is False

    import os
    if output_path and os.path.exists(output_path):
        os.remove(output_path)
