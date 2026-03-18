"""LLM prompt construction and backend dispatch."""

import logging
import re

logger = logging.getLogger("voicepad.llm")


class LLMRouter:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.ollama_backend = None
        self.remote_backend = None

    def initialize_backends(self) -> None:
        from voicepad.subsystems.llm_engine.ollama_backend import OllamaBackend
        from voicepad.subsystems.llm_engine.remote_backend import RemoteBackend

        self.ollama_backend = OllamaBackend(self.config_manager)
        self.remote_backend = RemoteBackend(self.config_manager)

    def update_config(self, config_manager) -> None:
        self.config_manager = config_manager
        if self.ollama_backend:
            self.ollama_backend.update_config(config_manager)
        if self.remote_backend:
            self.remote_backend.update_config(config_manager)

    def process_text(
        self,
        input_text: str,
        processing_style: str,
        output_language: str,
        custom_prompt: str = None,
    ) -> str:
        if not input_text:
            return ""

        constructed_prompt = self.build_prompt(
            input_text, processing_style, output_language, custom_prompt
        )

        if constructed_prompt is None:
            return input_text

        active_backend = self.config_manager.get_value("llm.backend", "ollama")
        thinking_enabled = self.config_manager.get_value("llm.thinking_enabled", False)

        if active_backend == "ollama":
            if not self.ollama_backend:
                self.initialize_backends()
            self.ollama_backend.extra_params["think"] = thinking_enabled
            raw_response = self.ollama_backend.generate_response(constructed_prompt)
        else:
            if not self.remote_backend:
                self.initialize_backends()
            self.remote_backend.thinking_enabled = thinking_enabled
            raw_response = self.remote_backend.generate_response(constructed_prompt)

        if not raw_response:
            logger.warning("LLM returned empty response, using original text")
            return input_text

        cleaned_response = self._strip_thinking_tags(raw_response).strip()

        # Small models often echo back the surrounding quotes from the prompt.
        # Strip a single pair of double quotes wrapping the entire response.
        if len(cleaned_response) >= 2 and cleaned_response[0] == '"' and cleaned_response[-1] == '"':
            cleaned_response = cleaned_response[1:-1].strip()

        return cleaned_response

    def build_prompt(
        self,
        input_text: str,
        processing_style: str,
        output_language: str,
        custom_prompt: str = None,
    ) -> str:
        if processing_style == "direct":
            return None

        if processing_style == "polish":
            base = (
                "You are a text processor. Your ONLY job is to clean up speech-to-text output.\n"
                "Rules:\n"
                "- Fix grammar, filler words, repetitions, and spoken-language patterns\n"
                "- Keep the original meaning exactly\n"
                "- Do NOT add any commentary, explanation, or extra content\n"
                "- Output ONLY the cleaned text, nothing else"
            )
        elif processing_style == "custom":
            if not custom_prompt:
                return None
            base = custom_prompt
        else:
            return None

        if output_language == "source":
            lang = "Keep the output in the same language as the input."
        elif output_language == "zh":
            lang = "用中文输出结果。"
        elif output_language == "en":
            lang = "Output the result in English."
        else:
            lang = f"Output the result in {output_language}."

        return f"{base}\n\n{lang}\n\nInput:\n\"{input_text}\"\n\nOutput:"

    def _strip_thinking_tags(self, response_text: str) -> str:
        return re.sub(
            r"<think>.*?</think>", "", response_text, flags=re.DOTALL
        ).strip()
