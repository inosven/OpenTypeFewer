import os
import pytest

from voicepad.config.config_manager import ConfigManager, DEFAULT_CONFIG


def test_load_creates_default_when_missing(tmp_path):
    config_path = tmp_path / "nonexistent" / "config.yaml"
    config_manager = ConfigManager(str(config_path))
    loaded_config = config_manager.load_config()

    assert loaded_config is not None
    assert loaded_config["language"] == "en"
    assert loaded_config["trigger_mode"] == "hold"
    assert config_path.exists()


def test_load_existing_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        'language: "zh"\ntrigger_mode: "toggle"\n', encoding="utf-8"
    )

    config_manager = ConfigManager(str(config_path))
    loaded_config = config_manager.load_config()

    assert loaded_config["language"] == "zh"
    assert loaded_config["trigger_mode"] == "toggle"


def test_missing_fields_filled_with_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text('language: "zh"\n', encoding="utf-8")

    config_manager = ConfigManager(str(config_path))
    loaded_config = config_manager.load_config()

    assert loaded_config["language"] == "zh"
    assert loaded_config["trigger_mode"] == "hold"
    assert loaded_config["asr"]["model_size"] == "large-v3"


def test_get_value_dot_notation(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_manager = ConfigManager(str(config_path))
    config_manager.load_config()

    model_size = config_manager.get_value("asr.model_size")
    assert model_size == "large-v3"

    ollama_model = config_manager.get_value("llm.ollama.model")
    assert ollama_model == "qwen3.5"


def test_get_value_with_default(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_manager = ConfigManager(str(config_path))
    config_manager.load_config()

    missing_value = config_manager.get_value("nonexistent.key", "fallback")
    assert missing_value == "fallback"


def test_set_value_dot_notation(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_manager = ConfigManager(str(config_path))
    config_manager.load_config()

    config_manager.set_value("asr.model_size", "small")
    assert config_manager.get_value("asr.model_size") == "small"


def test_save_and_reload(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_manager = ConfigManager(str(config_path))
    config_manager.load_config()

    config_manager.set_value("language", "zh")
    save_success = config_manager.save_config()
    assert save_success is True

    reloaded_manager = ConfigManager(str(config_path))
    reloaded_config = reloaded_manager.load_config()
    assert reloaded_config["language"] == "zh"


def test_env_var_overrides_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("VOICEPAD_API_KEY", "test_key_from_env")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        'llm:\n  remote:\n    api_key: "old_key"\n', encoding="utf-8"
    )

    config_manager = ConfigManager(str(config_path))
    config_manager.load_config()

    assert config_manager.get_value("llm.remote.api_key") == "test_key_from_env"


def test_invalid_yaml_falls_back_to_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("{{invalid yaml: [", encoding="utf-8")

    config_manager = ConfigManager(str(config_path))
    loaded_config = config_manager.load_config()

    assert loaded_config["language"] == "en"
    assert loaded_config["trigger_mode"] == "hold"


def test_deep_merge_preserves_nested_defaults(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        'llm:\n  ollama:\n    model: "llama3"\n', encoding="utf-8"
    )

    config_manager = ConfigManager(str(config_path))
    loaded_config = config_manager.load_config()

    assert loaded_config["llm"]["ollama"]["model"] == "llama3"
    assert loaded_config["llm"]["ollama"]["base_url"] == "http://localhost:11434"
    assert loaded_config["llm"]["remote"]["provider"] == "anthropic"
