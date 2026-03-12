"""Ollama LLM backend for local inference."""

import logging

logger = logging.getLogger("voicepad.llm.ollama")


class OllamaBackend:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.model_name = config_manager.get_value("llm.ollama.model", "qwen3.5")
        self.base_url = config_manager.get_value(
            "llm.ollama.base_url", "http://localhost:11434"
        )
        self.temperature = config_manager.get_value("llm.ollama.temperature", 0.3)
        self.extra_params = config_manager.get_value(
            "llm.ollama.extra_params", {"think": False}
        )

    def update_config(self, config_manager) -> None:
        self.model_name = config_manager.get_value("llm.ollama.model", "qwen3.5")
        self.base_url = config_manager.get_value(
            "llm.ollama.base_url", "http://localhost:11434"
        )
        self.temperature = config_manager.get_value("llm.ollama.temperature", 0.3)
        self.extra_params = config_manager.get_value(
            "llm.ollama.extra_params", {"think": False}
        )

    def generate_response(self, prompt_text: str) -> str:
        if not prompt_text:
            return ""

        try:
            import ollama
            import httpx

            logger.info(f"Calling Ollama model: {self.model_name}")

            client = ollama.Client(
                host=self.base_url,
                timeout=httpx.Timeout(timeout=60.0),
            )

            response = client.generate(
                model=self.model_name,
                prompt=prompt_text,
                think=False,
                options={"temperature": self.temperature},
            )
            # ollama>=0.3 returns a GenerateResponse object, not a dict
            text = response.response if hasattr(response, "response") else response["response"]
            logger.info(f"Ollama response received ({len(text)} chars): {text[:100]!r}")
            return text
        except Exception as generate_error:
            logger.error(f"Ollama generation failed: {generate_error}")
            return ""

    def warm_up_model(self) -> bool:
        try:
            import ollama
            import httpx

            logger.info(f"Warming up Ollama model: {self.model_name}")
            client = ollama.Client(
                host=self.base_url,
                timeout=httpx.Timeout(timeout=120.0),
            )
            client.generate(
                model=self.model_name,
                prompt="hi",
                think=False,
                options={"temperature": 0.3, "num_predict": 1},
            )
            logger.info(f"Ollama model warmed up: {self.model_name}")
            return True
        except Exception as warmup_error:
            logger.warning(f"Ollama warm-up failed: {warmup_error}")
            return False

    def check_availability(self) -> bool:
        try:
            import ollama

            client = ollama.Client(host=self.base_url)
            client.list()
            return True
        except Exception:
            return False

    def check_model_exists(self) -> bool:
        try:
            import ollama

            client = ollama.Client(host=self.base_url)
            model_list = client.list()
            available_models = [
                model_entry.model for model_entry in model_list.models
            ]
            return any(self.model_name in model_id for model_id in available_models)
        except Exception:
            return False
