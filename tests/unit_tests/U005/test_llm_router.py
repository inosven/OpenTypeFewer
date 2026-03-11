import pytest
from unittest.mock import MagicMock

from voicepad.subsystems.llm_engine.llm_router import LLMRouter


def _create_mock_config():
    mock_config = MagicMock()
    mock_config.get_value.return_value = "ollama"
    return mock_config


def test_direct_source_returns_none_prompt():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt("hello", "direct", "source")
    assert prompt_result is None


def test_direct_source_returns_original_text():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    result_text = router.process_text("hello world", "direct", "source")
    assert result_text == "hello world"


def test_polish_source_builds_prompt():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt("test input", "polish", "source")
    assert prompt_result is not None
    assert "Clean up" in prompt_result
    assert "same language as the input" in prompt_result
    assert "test input" in prompt_result


def test_polish_zh_builds_prompt():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt("test input", "polish", "zh")
    assert "Clean up" in prompt_result
    assert "Chinese" in prompt_result


def test_polish_en_builds_prompt():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt("test input", "polish", "en")
    assert "Clean up" in prompt_result
    assert "English" in prompt_result


def test_direct_en_translation_prompt():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt("test input", "direct", "en")
    assert prompt_result is not None
    assert "English" in prompt_result
    assert "Clean up" not in prompt_result


def test_direct_zh_translation_prompt():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt("test input", "direct", "zh")
    assert prompt_result is not None
    assert "Chinese" in prompt_result


def test_custom_prompt_included():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    custom_text = "Summarize in bullet points"
    prompt_result = router.build_prompt(
        "test input", "custom", "source", custom_prompt=custom_text
    )
    assert custom_text in prompt_result


def test_custom_with_language():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt(
        "test", "custom", "en", custom_prompt="Make it formal"
    )
    assert "Make it formal" in prompt_result
    assert "English" in prompt_result


def test_unknown_language_uses_name():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    prompt_result = router.build_prompt("test", "polish", "japanese")
    assert "japanese" in prompt_result


def test_strip_thinking_tags():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    text_with_tags = "<think>reasoning here</think>Final answer"
    cleaned_text = router._strip_thinking_tags(text_with_tags)
    assert cleaned_text == "Final answer"


def test_empty_input_returns_empty():
    mock_config = _create_mock_config()
    router = LLMRouter(mock_config)

    result_text = router.process_text("", "polish", "source")
    assert result_text == ""
