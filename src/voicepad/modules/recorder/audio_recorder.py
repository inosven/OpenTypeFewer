"""Audio recording module for VoicePad."""

import os
import sys
import time
import logging
import threading

import numpy as np

logger = logging.getLogger("voicepad.recorder")


def _get_temp_dir() -> str:
    if hasattr(sys, "_MEIPASS"):
        import tempfile
        return tempfile.gettempdir()
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "temp"
    )


class AudioRecorder:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.sample_rate = config_manager.get_value("audio.sample_rate", 16000)
        self.audio_channels = config_manager.get_value("audio.channels", 1)
        self.silence_threshold = config_manager.get_value("audio.silence_threshold", 500)
        self.silence_duration = config_manager.get_value("audio.silence_duration", 2.0)
        self.recording_active = False
        self.audio_frames = []
        self.recording_stream = None
        self.recording_lock = threading.Lock()

    def start_recording(self) -> bool:
        if self.recording_active:
            return False

        import sounddevice

        self.audio_frames = []
        self.recording_active = True

        try:
            self.recording_stream = sounddevice.InputStream(
                samplerate=self.sample_rate,
                channels=self.audio_channels,
                dtype="int16",
                callback=self._audio_callback,
            )
            self.recording_stream.start()
            logger.info("Recording started")
            return True
        except sounddevice.PortAudioError as audio_error:
            logger.error(f"Failed to start recording: {audio_error}")
            self.recording_active = False
            return False

    def stop_recording(self) -> str:
        if not self.recording_active:
            return None

        self.recording_active = False

        if self.recording_stream:
            try:
                self.recording_stream.stop()
                self.recording_stream.close()
            except Exception as stop_error:
                logger.error(f"Error stopping stream: {stop_error}")
            self.recording_stream = None

        with self.recording_lock:
            if not self.audio_frames:
                logger.warning("No audio frames captured")
                return None
            audio_data = np.concatenate(self.audio_frames, axis=0)

        temp_dir = _get_temp_dir()
        os.makedirs(temp_dir, exist_ok=True)
        output_path = os.path.join(temp_dir, f"voicepad_{int(time.time())}.wav")

        from scipy.io import wavfile
        wavfile.write(output_path, self.sample_rate, audio_data)
        logger.info(f"Recording saved to {output_path}")
        return output_path

    def is_recording(self) -> bool:
        return self.recording_active

    def check_silence(self) -> bool:
        with self.recording_lock:
            if not self.audio_frames:
                return False
            frames_for_duration = int(
                self.silence_duration * self.sample_rate / 1024
            )
            recent_frames = self.audio_frames[-frames_for_duration:]

        if not recent_frames:
            return False

        combined_audio = np.concatenate(recent_frames, axis=0)
        amplitude_value = np.abs(combined_audio).mean()
        return amplitude_value < self.silence_threshold

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            logger.warning(f"Audio callback status: {status}")
        with self.recording_lock:
            self.audio_frames.append(indata.copy())
