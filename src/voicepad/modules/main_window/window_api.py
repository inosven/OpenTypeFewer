"""Python API class exposed to JS via pywebview bridge."""

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("voicepad.window_api")


def _resolve_signal_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path.home() / ".opentypefewer"
    return Path(__file__).parent.parent.parent.parent.parent / "temp"


class WindowApi:
    def __init__(self, config_manager, status_file_path: str, open_settings_callback=None):
        self._config_manager = config_manager
        self._status_file_path = status_file_path
        self._open_settings_callback = open_settings_callback
        self._window = None

    def minimize_window(self) -> None:
        if self._window:
            self._window.hide()

    def restore_window(self) -> None:
        if self._window:
            self._window.show()
            self._window.on_top = True

    def get_status(self) -> dict:
        try:
            status_path = Path(self._status_file_path)
            if not status_path.exists():
                return {"state": "ready"}
            with open(status_path, "r", encoding="utf-8") as status_file:
                return json.loads(status_file.read())
        except Exception as read_error:
            logger.warning(f"Failed to read status file: {read_error}")
            return {"state": "ready"}

    def minimize_window(self) -> None:
        try:
            import webview
            if webview.windows:
                webview.windows[0].minimize()
        except Exception as minimize_error:
            logger.warning(f"Failed to minimize window: {minimize_error}")

    def open_settings(self) -> None:
        if self._open_settings_callback:
            try:
                self._open_settings_callback()
            except Exception as callback_error:
                logger.error(f"Failed to open settings: {callback_error}")

    def get_config(self) -> dict:
        import copy
        config_copy = copy.deepcopy(self._config_manager.config_data)
        self._redact_sensitive_fields(config_copy)
        return config_copy

    def save_config(self, config_data: dict) -> bool:
        try:
            if not isinstance(config_data, dict):
                logger.error(f"save_config received non-dict: {type(config_data)}")
                return False
            import copy
            self._restore_sensitive_fields(config_data)
            self._config_manager.config_data = copy.deepcopy(config_data)
            save_success = self._config_manager.save_config()
            if save_success:
                logger.info(f"Config saved via window API to {self._config_manager.config_path}")
                self._write_reload_signal()
            else:
                logger.error("Config save returned False")
            return save_success
        except Exception as save_error:
            logger.error(f"Failed to save config: {save_error}", exc_info=True)
            return False

    def list_ollama_models(self) -> list:
        try:
            from voicepad.subsystems.llm_engine.ollama_backend import list_ollama_models
            base_url = self._config_manager.get_value("llm.ollama.base_url", "http://localhost:11434")
            return list_ollama_models(base_url)
        except Exception as list_error:
            logger.warning(f"Failed to list Ollama models: {list_error}")
            return []

    def list_microphones(self) -> list:
        try:
            import sounddevice
            device_list = sounddevice.query_devices()
            input_devices = []
            for device_index, device_info in enumerate(device_list):
                if device_info["max_input_channels"] > 0:
                    input_devices.append({
                        "index": device_index,
                        "name": device_info["name"],
                    })
            return input_devices
        except Exception as list_error:
            logger.warning(f"Failed to list microphones: {list_error}")
            return []

    def start_mic_test(self, device_index=None) -> bool:
        self.stop_mic_test()
        try:
            import sounddevice
            import numpy

            self._mic_test_buffer = numpy.zeros(0, dtype=numpy.float32)
            self._mic_test_warmup = 3

            stream_kwargs = {
                "samplerate": 16000,
                "channels": 1,
                "dtype": "float32",
                "blocksize": int(0.05 * 16000),
                "callback": self._mic_test_callback,
            }
            if device_index is not None:
                stream_kwargs["device"] = int(device_index)

            self._mic_test_stream = sounddevice.InputStream(**stream_kwargs)
            self._mic_test_stream.start()
            return True
        except Exception as mic_error:
            logger.warning(f"Mic test start failed: {mic_error}")
            return False

    def _mic_test_callback(self, indata, frames, time_info, status):
        import numpy
        if self._mic_test_warmup > 0:
            self._mic_test_warmup -= 1
            return
        audio_float = indata[:, 0].astype(numpy.float64)
        rms_volume = float(numpy.sqrt(numpy.mean(audio_float ** 2)))
        if numpy.isnan(rms_volume) or numpy.isinf(rms_volume):
            rms_volume = 0.0
        self._mic_test_level = min(rms_volume * 3.0, 1.0)

    def get_mic_test_level(self) -> float:
        return getattr(self, "_mic_test_level", 0.0)

    def stop_mic_test(self) -> None:
        stream = getattr(self, "_mic_test_stream", None)
        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
            self._mic_test_stream = None
        self._mic_test_level = 0.0

    def test_microphone(self, device_index=None) -> float:
        return self.get_mic_test_level()

    def check_for_updates(self) -> dict:
        try:
            import urllib.request
            import json as json_lib

            releases_url = "https://api.github.com/repos/OpenTypeFewer/OpenTypeFewer/releases/latest"
            request = urllib.request.Request(
                releases_url,
                headers={"User-Agent": "OpenTypeFewer"},
            )
            with urllib.request.urlopen(request, timeout=5) as response_data:
                release_info = json_lib.loads(response_data.read())

            latest_version = release_info.get("tag_name", "").lstrip("v")
            from voicepad import __version__
            current_version = __version__

            has_update = latest_version and latest_version != current_version
            return {
                "has_update": has_update,
                "latest_version": latest_version,
                "current_version": current_version,
            }
        except Exception as update_error:
            logger.warning(f"Update check failed: {update_error}")
            return {"has_update": False, "latest_version": "", "current_version": ""}

    def capture_hotkey(self) -> str:
        import platform
        if platform.system() == "Darwin":
            return ""

        import keyboard as kb
        hotkey_str = kb.read_hotkey(suppress=False)
        return hotkey_str

    def open_github(self) -> None:
        import webbrowser
        webbrowser.open("https://github.com/inosven/OpenTypeFewer")

    def _write_reload_signal(self) -> None:
        try:
            signal_dir = _resolve_signal_dir()
            signal_dir.mkdir(parents=True, exist_ok=True)
            signal_path = signal_dir / "reload_config.signal"
            signal_path.write_text("reload")
        except OSError as signal_error:
            logger.warning(f"Failed to write reload signal: {signal_error}")

    def _redact_sensitive_fields(self, config_data: dict) -> None:
        llm_data = config_data.get("llm", {})
        remote_data = llm_data.get("remote", {})
        if remote_data.get("api_key"):
            remote_data["api_key"] = "••••••••"
        compatible_data = llm_data.get("compatible", {})
        if compatible_data.get("api_key"):
            compatible_data["api_key"] = "••••••••"

    def _restore_sensitive_fields(self, incoming_config: dict) -> None:
        current_remote_key = self._config_manager.get_value("llm.remote.api_key", "")
        current_compatible_key = self._config_manager.get_value("llm.compatible.api_key", "")

        llm_data = incoming_config.get("llm", {})
        remote_data = llm_data.get("remote", {})
        if remote_data.get("api_key") == "••••••••":
            remote_data["api_key"] = current_remote_key

        compatible_data = llm_data.get("compatible", {})
        if compatible_data.get("api_key") == "••••••••":
            compatible_data["api_key"] = current_compatible_key
