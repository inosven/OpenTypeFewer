"""Remote LLM backend for API-based inference."""

import os
import logging

logger = logging.getLogger("voicepad.llm.remote")


class RemoteBackend:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.provider_name = config_manager.get_value("llm.remote.provider", "anthropic")
        self.model_name = config_manager.get_value(
            "llm.remote.model", "claude-sonnet-4-20250514"
        )
        self.api_key = (
            os.environ.get("VOICEPAD_API_KEY")
            or config_manager.get_value("llm.remote.api_key", "")
        )
        self.base_url = config_manager.get_value("llm.remote.base_url", "")
        self.thinking_enabled = config_manager.get_value("llm.thinking_enabled", False)
        self.compatible_base_url = config_manager.get_value(
            "llm.compatible.base_url", "http://localhost:1234/v1"
        )
        self.compatible_model = config_manager.get_value("llm.compatible.model", "")
        self.compatible_api_key = config_manager.get_value("llm.compatible.api_key", "")
        self.compatible_temperature = config_manager.get_value(
            "llm.compatible.temperature", 0.3
        )

    def update_config(self, config_manager) -> None:
        self.provider_name = config_manager.get_value("llm.remote.provider", "anthropic")
        self.model_name = config_manager.get_value(
            "llm.remote.model", "claude-sonnet-4-20250514"
        )
        self.api_key = (
            os.environ.get("VOICEPAD_API_KEY")
            or config_manager.get_value("llm.remote.api_key", "")
        )
        self.base_url = config_manager.get_value("llm.remote.base_url", "")
        self.thinking_enabled = config_manager.get_value("llm.thinking_enabled", False)
        self.compatible_base_url = config_manager.get_value(
            "llm.compatible.base_url", "http://localhost:1234/v1"
        )
        self.compatible_model = config_manager.get_value("llm.compatible.model", "")
        self.compatible_api_key = config_manager.get_value("llm.compatible.api_key", "")
        self.compatible_temperature = config_manager.get_value(
            "llm.compatible.temperature", 0.3
        )

    def generate_response(self, prompt_text: str) -> str:
        if not prompt_text:
            return ""

        if self.provider_name == "compatible":
            return self._generate_compatible(prompt_text)

        if not self.api_key:
            logger.error("No API key configured for remote LLM")
            return ""

        if self.provider_name == "anthropic":
            return self._generate_anthropic(prompt_text)
        elif self.provider_name == "openai":
            return self._generate_openai(prompt_text)
        else:
            logger.error(f"Unknown remote provider: {self.provider_name}")
            return ""

    def _generate_anthropic(self, prompt_text: str) -> str:
        try:
            import anthropic

            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            client = anthropic.Anthropic(**client_kwargs)

            create_kwargs = {
                "model": self.model_name,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt_text}],
            }
            if self.thinking_enabled:
                create_kwargs["thinking"] = {"type": "enabled", "budget_tokens": 8000}
                create_kwargs["max_tokens"] = max(4096, 8000 + 1024)

            message = client.messages.create(**create_kwargs)
            text_blocks = [block.text for block in message.content if hasattr(block, "text")]
            return "\n".join(text_blocks)
        except Exception as anthropic_error:
            logger.error(f"Anthropic API call failed: {anthropic_error}")
            return ""

    def _generate_openai(self, prompt_text: str) -> str:
        try:
            import openai

            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            client = openai.OpenAI(**client_kwargs)

            create_kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt_text}],
            }
            if self.thinking_enabled:
                try:
                    create_kwargs["reasoning_effort"] = "high"
                except Exception:
                    pass

            completion = client.chat.completions.create(**create_kwargs)
            return completion.choices[0].message.content
        except Exception as openai_error:
            logger.error(f"OpenAI API call failed: {openai_error}")
            return ""

    def _generate_compatible(self, prompt_text: str) -> str:
        if not self.compatible_model:
            logger.error("No model configured for compatible provider")
            return ""

        try:
            import openai

            client = openai.OpenAI(
                api_key=self.compatible_api_key or "none",
                base_url=self.compatible_base_url,
            )

            create_kwargs = {
                "model": self.compatible_model,
                "messages": [{"role": "user", "content": prompt_text}],
                "temperature": self.compatible_temperature,
            }
            if self.thinking_enabled:
                try:
                    create_kwargs["reasoning_effort"] = "high"
                except Exception:
                    pass

            completion = client.chat.completions.create(**create_kwargs)
            return completion.choices[0].message.content
        except Exception as compatible_error:
            logger.error(f"Compatible API call failed: {compatible_error}")
            return ""
