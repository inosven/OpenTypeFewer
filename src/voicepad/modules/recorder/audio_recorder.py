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
        self.input_device = config_manager.get_value("audio.input_device", None)
        self.recording_active = False
        self.audio_frames = []
        self.recording_stream = None
        self.recording_lock = threading.Lock()
        self._stream_ready = threading.Event()

    def start_recording(self) -> bool:
        # If recording_active is stuck True (e.g. from a previous race condition),
        # force-reset before starting a new recording.
        if self.recording_active:
            logger.warning("start_recording: recording_active stuck, force-resetting")
            self.recording_active = False
            if self.recording_stream:
                try:
                    self.recording_stream.stop()
                    self.recording_stream.close()
                except Exception:
                    pass
                self.recording_stream = None
            self.audio_frames = []

        import sounddevice

        self.audio_frames = []
        self._stream_ready.clear()
        self.recording_active = True

        device_id = int(self.input_device) if self.input_device is not None else None
        device_info = self._query_device_info(sounddevice, device_id)
        device_max_channels = device_info.get("max_input_channels", 0) if device_info else 0
        device_native_rate = device_info.get("default_samplerate", 0) if device_info else 0

        channels_to_try = self.audio_channels
        if device_max_channels and channels_to_try > device_max_channels:
            logger.info(
                f"Requested {channels_to_try}ch but device supports {device_max_channels}ch, adapting"
            )
            channels_to_try = device_max_channels

        rate_to_try = self.sample_rate
        if device_native_rate and device_native_rate != self.sample_rate:
            rate_to_try = int(device_native_rate)
            logger.info(
                f"Device native rate {rate_to_try}Hz differs from config {self.sample_rate}Hz, "
                f"using native rate (will resample on save)"
            )

        self._actual_sample_rate = rate_to_try

        try:
            self.recording_stream = self._open_input_stream(
                sounddevice, channels_to_try, device_id, rate_to_try
            )
            self.recording_stream.start()
            self._stream_ready.set()
            if not self.recording_active:
                logger.info("Stream opened but stop already requested, leaving cleanup to stop_recording")
                return False
            logger.info(f"Recording started ({channels_to_try}ch, {rate_to_try}Hz)")
            return True
        except sounddevice.PortAudioError:
            fallback_channels = device_max_channels or (2 if channels_to_try == 1 else 1)
            if fallback_channels == channels_to_try:
                fallback_channels = 2 if channels_to_try == 1 else 1
            logger.warning(
                f"Failed with {channels_to_try}ch/{rate_to_try}Hz, "
                f"retrying with {fallback_channels}ch"
            )
            try:
                self.recording_stream = self._open_input_stream(
                    sounddevice, fallback_channels, device_id, rate_to_try
                )
                self.recording_stream.start()
                self._stream_ready.set()
                if not self.recording_active:
                    logger.info("Fallback stream opened but stop already requested, leaving cleanup to stop_recording")
                    return False
                logger.info(f"Recording started ({fallback_channels}ch, {rate_to_try}Hz, fallback)")
                return True
            except sounddevice.PortAudioError as audio_error:
                logger.error(f"Failed to start recording: {audio_error}")
                self._stream_ready.set()
                self.recording_active = False
                return False

    def stop_recording(self) -> str:
        if not self.recording_active:
            deadline = time.time() + 0.4
            while not self.recording_active and time.time() < deadline:
                time.sleep(0.02)

        if not self.recording_active:
            logger.warning("stop_recording: not recording (start may not have run yet)")
            return None

        self.recording_active = False

        stream_opened = self._stream_ready.wait(timeout=3.0)
        if not stream_opened:
            logger.warning("stop_recording: stream never opened within timeout")

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

        if audio_data.ndim == 2 and audio_data.shape[1] > 1:
            audio_data = audio_data.mean(axis=1).astype(np.int16)

        actual_rate = getattr(self, "_actual_sample_rate", self.sample_rate)
        if actual_rate != self.sample_rate:
            audio_data = self._resample_audio(audio_data, actual_rate, self.sample_rate)
            logger.info(f"Resampled audio from {actual_rate}Hz to {self.sample_rate}Hz")

        duration = len(audio_data) / self.sample_rate
        if duration < 0.5:
            logger.warning(f"Recording too short ({duration:.2f}s), discarding")
            return None

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
            actual_rate = getattr(self, "_actual_sample_rate", self.sample_rate)
            frames_for_duration = int(
                self.silence_duration * actual_rate / 1024
            )
            recent_frames = self.audio_frames[-frames_for_duration:]

        if not recent_frames:
            return False

        combined_audio = np.concatenate(recent_frames, axis=0)
        amplitude_value = np.abs(combined_audio).mean()
        return amplitude_value < self.silence_threshold

    def _open_input_stream(self, sounddevice_module, channel_count, device_id, sample_rate=None):
        stream_kwargs = {
            "samplerate": sample_rate or self.sample_rate,
            "channels": channel_count,
            "dtype": "int16",
            "callback": self._audio_callback,
        }
        if device_id is not None:
            stream_kwargs["device"] = device_id
        return sounddevice_module.InputStream(**stream_kwargs)

    def _query_device_info(self, sounddevice_module, device_id) -> dict:
        try:
            query_id = device_id if device_id is not None else sounddevice_module.default.device[0]
            return sounddevice_module.query_devices(query_id)
        except Exception:
            return {}

    def _resample_audio(self, audio_data, source_rate: int, target_rate: int):
        from scipy.signal import resample
        target_length = int(len(audio_data) * target_rate / source_rate)
        resampled = resample(audio_data.astype(np.float64), target_length)
        return resampled.astype(np.int16)

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            logger.warning(f"Audio callback status: {status}")
        with self.recording_lock:
            self.audio_frames.append(indata.copy())
