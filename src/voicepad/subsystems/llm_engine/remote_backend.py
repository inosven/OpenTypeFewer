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

    def generate_response(self, prompt_text: str) -> str:
        if not prompt_text:
            return ""

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
            message = client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt_text}],
            )
            return message.content[0].text
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
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt_text}],
            )
            return completion.choices[0].message.content
        except Exception as openai_error:
            logger.error(f"OpenAI API call failed: {openai_error}")
            return ""
