"""Configuration management for VoicePad."""

import os
import copy
import logging
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "language": "en",
    "trigger_mode": "hold",
    "hotkey": "ctrl+shift+space",
    "mode_switch_hotkey": "ctrl+shift+m",
    "auto_stop_on_focus_loss": True,
    "asr": {
        "model_size": "large-v3",
        "language": None,
        "device": "auto",
        "compute_type": "auto",
    },
    "output": {
        "processing": "direct",
        "language": "source",
        "custom_prompt": "",
    },
    "languages": [
        {"key": "source", "name_en": "Original Language", "name_zh": "原文语言"},
        {"key": "zh", "name_en": "Chinese", "name_zh": "中文"},
        {"key": "en", "name_en": "English", "name_zh": "英文"},
    ],
    "llm": {
        "backend": "ollama",
        "ollama": {
            "model": "qwen3.5",
            "base_url": "http://localhost:11434",
            "temperature": 0.3,
            "extra_params": {"think": False},
        },
        "remote": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key": "",
            "base_url": "",
        },
    },
    "presets": [],
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "silence_threshold": 500,
        "silence_duration": 2.0,
    },
    "notification": {
        "enabled": True,
        "sound_enabled": True,
        "sound_start": "start.wav",
        "sound_stop": "stop.wav",
        "sound_done": "done.wav",
        "sound_error": "error.wav",
    },
}

logger = logging.getLogger("voicepad.config")


def _deep_merge(base_dict: dict, override_dict: dict) -> dict:
    merged_result = copy.deepcopy(base_dict)
    for merge_key, merge_value in override_dict.items():
        if (
            merge_key in merged_result
            and isinstance(merged_result[merge_key], dict)
            and isinstance(merge_value, dict)
        ):
            merged_result[merge_key] = _deep_merge(merged_result[merge_key], merge_value)
        else:
            merged_result[merge_key] = copy.deepcopy(merge_value)
    return merged_result


class ConfigManager:
    def __init__(self, config_path: str = None):
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path.home() / ".voicepad" / "config.yaml"
        self.config_data = {}

    def load_config(self) -> dict:
        self.config_data = copy.deepcopy(DEFAULT_CONFIG)

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as config_file:
                    file_data = yaml.safe_load(config_file)
            except (OSError, yaml.YAMLError) as load_error:
                logger.error(f"Failed to load config: {load_error}")
                file_data = None

            if file_data and isinstance(file_data, dict):
                self.config_data = _deep_merge(self.config_data, file_data)
        else:
            self._write_default_config()

        self._apply_env_overrides()
        return self.config_data

    def save_config(self) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as config_file:
                yaml.dump(
                    self.config_data,
                    config_file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            return True
        except OSError as save_error:
            logger.error(f"Failed to save config: {save_error}")
            return False

    def get_value(self, dot_key: str, default_value=None):
        key_parts = dot_key.split(".")
        current_level = self.config_data
        for part in key_parts:
            if not isinstance(current_level, dict):
                return default_value
            if part not in current_level:
                return default_value
            current_level = current_level[part]
        return current_level

    def set_value(self, dot_key: str, new_value) -> None:
        key_parts = dot_key.split(".")
        current_level = self.config_data
        for part in key_parts[:-1]:
            if part not in current_level or not isinstance(current_level[part], dict):
                current_level[part] = {}
            current_level = current_level[part]
        current_level[key_parts[-1]] = new_value

    def _write_default_config(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as config_file:
                yaml.dump(
                    self.config_data,
                    config_file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            logger.info(f"Created default config at {self.config_path}")
        except OSError as write_error:
            logger.error(f"Failed to write default config: {write_error}")

    def _apply_env_overrides(self) -> None:
        env_api_key = os.environ.get("VOICEPAD_API_KEY")
        if env_api_key:
            self.set_value("llm.remote.api_key", env_api_key)
