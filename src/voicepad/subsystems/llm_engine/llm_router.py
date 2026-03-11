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

        if active_backend == "ollama":
            if not self.ollama_backend:
                self.initialize_backends()
            raw_response = self.ollama_backend.generate_response(constructed_prompt)
        else:
            if not self.remote_backend:
                self.initialize_backends()
            raw_response = self.remote_backend.generate_response(constructed_prompt)

        if not raw_response:
            logger.warning("LLM returned empty response, using original text")
            return input_text

        cleaned_response = self._strip_thinking_tags(raw_response)
        return cleaned_response.strip()

    def build_prompt(
        self,
        input_text: str,
        processing_style: str,
        output_language: str,
        custom_prompt: str = None,
    ) -> str:
        if processing_style == "direct" and output_language == "source":
            return None

        prompt_instructions = []

        if processing_style == "polish":
            prompt_instructions.append(
                "Clean up the following speech-to-text transcription into fluent written form. "
                "Fix spoken-language patterns, repetitions, filler words, and grammatical errors. "
                "Keep the original meaning. Do not add content."
            )
        elif processing_style == "custom":
            if custom_prompt:
                prompt_instructions.append(custom_prompt)

        if output_language == "source":
            prompt_instructions.append(
                "Keep the output in the same language as the input."
            )
        elif output_language == "zh":
            prompt_instructions.append("Output the result in Chinese (中文).")
        elif output_language == "en":
            prompt_instructions.append("Output the result in English.")
        else:
            prompt_instructions.append(
                f"Output the result in {output_language}."
            )

        combined_instructions = " ".join(prompt_instructions)
        return (
            f"{combined_instructions}\n\n"
            f"Output the result directly with no explanation.\n\n"
            f"Input:\n{input_text}"
        )

    def _strip_thinking_tags(self, response_text: str) -> str:
        return re.sub(
            r"<think>.*?</think>", "", response_text, flags=re.DOTALL
        ).strip()
