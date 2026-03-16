"""Python API class exposed to JS via pywebview bridge."""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("voicepad.window_api")


class WindowApi:
    def __init__(self, config_manager, status_file_path: str, open_settings_callback=None):
        self.config_manager = config_manager
        self.status_file_path = status_file_path
        self.open_settings_callback = open_settings_callback

    def get_status(self) -> dict:
        try:
            status_path = Path(self.status_file_path)
            if not status_path.exists():
                return {"state": "ready"}
            with open(status_path, "r", encoding="utf-8") as status_file:
                return json.loads(status_file.read())
        except Exception as read_error:
            logger.warning(f"Failed to read status file: {read_error}")
            return {"state": "ready"}

    def open_settings(self) -> None:
        if self.open_settings_callback:
            try:
                self.open_settings_callback()
            except Exception as callback_error:
                logger.error(f"Failed to open settings: {callback_error}")

    def get_config(self) -> dict:
        import copy
        config_copy = copy.deepcopy(self.config_manager.config_data)
        self._redact_sensitive_fields(config_copy)
        return config_copy

    def save_config(self, config_data: dict) -> bool:
        try:
            import copy
            self._restore_sensitive_fields(config_data)
            self.config_manager.config_data = copy.deepcopy(config_data)
            save_success = self.config_manager.save_config()
            if save_success:
                logger.info("Config saved via window API")
            return save_success
        except Exception as save_error:
            logger.error(f"Failed to save config: {save_error}")
            return False

    def list_ollama_models(self) -> list:
        try:
            from voicepad.subsystems.llm_engine.ollama_backend import list_ollama_models
            base_url = self.config_manager.get_value("llm.ollama.base_url", "http://localhost:11434")
            return list_ollama_models(base_url)
        except Exception as list_error:
            logger.warning(f"Failed to list Ollama models: {list_error}")
            return []

    def test_microphone(self) -> float:
        try:
            import sounddevice
            import numpy

            audio_block = sounddevice.rec(
                int(0.05 * 16000),
                samplerate=16000,
                channels=1,
                dtype="float32",
            )
            sounddevice.wait()
            rms_volume = float(numpy.sqrt(numpy.mean(audio_block ** 2)))
            return min(rms_volume * 10.0, 1.0)
        except Exception as mic_error:
            logger.warning(f"Mic test failed: {mic_error}")
            return 0.0

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

    def open_github(self) -> None:
        import webbrowser
        webbrowser.open("https://github.com/OpenTypeFewer/OpenTypeFewer")

    def _redact_sensitive_fields(self, config_data: dict) -> None:
        llm_data = config_data.get("llm", {})
        remote_data = llm_data.get("remote", {})
        if remote_data.get("api_key"):
            remote_data["api_key"] = "••••••••"
        compatible_data = llm_data.get("compatible", {})
        if compatible_data.get("api_key"):
            compatible_data["api_key"] = "••••••••"

    def _restore_sensitive_fields(self, incoming_config: dict) -> None:
        current_remote_key = self.config_manager.get_value("llm.remote.api_key", "")
        current_compatible_key = self.config_manager.get_value("llm.compatible.api_key", "")

        llm_data = incoming_config.get("llm", {})
        remote_data = llm_data.get("remote", {})
        if remote_data.get("api_key") == "••••••••":
            remote_data["api_key"] = current_remote_key

        compatible_data = llm_data.get("compatible", {})
        if compatible_data.get("api_key") == "••••••••":
            compatible_data["api_key"] = current_compatible_key
