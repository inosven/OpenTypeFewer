"""Speech recognition engine using faster-whisper."""

import os
import sys
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("voicepad.asr")

MODEL_CACHE_DIR = str(Path.home() / ".voicepad" / "models")


def _register_nvidia_dll_paths() -> None:
    if sys.platform != "win32":
        return

    import site
    search_roots = site.getsitepackages() + [site.getusersitepackages()]
    current_path = os.environ.get("PATH", "")

    for site_root in search_roots:
        nvidia_dir = Path(site_root) / "nvidia"
        if not nvidia_dir.exists():
            continue
        for dll_dir in nvidia_dir.rglob("bin"):
            if dll_dir.is_dir():
                dll_path = str(dll_dir)
                if dll_path not in current_path:
                    os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")
                    logger.info(f"Added NVIDIA DLL to PATH: {dll_path}")


_register_nvidia_dll_paths()


@dataclass
class ASRResult:
    transcribed_text: str
    detected_language: str
    confidence_score: float


class ASREngine:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.model_size = config_manager.get_value("asr.model_size", "large-v3")
        self.forced_language = config_manager.get_value("asr.language", None)
        self.device_type = config_manager.get_value("asr.device", "auto")
        self.compute_type = config_manager.get_value("asr.compute_type", "auto")
        self.whisper_model = None

    def load_model(self) -> bool:
        try:
            from faster_whisper import WhisperModel

            resolved_device = self._resolve_device()
            resolved_compute = self._resolve_compute_type(resolved_device)

            logger.info(
                f"Loading ASR model: {self.model_size} "
                f"on {resolved_device} with {resolved_compute}"
            )

            os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

            self.whisper_model = WhisperModel(
                self.model_size,
                device=resolved_device,
                compute_type=resolved_compute,
                download_root=MODEL_CACHE_DIR,
            )
            logger.info("ASR model loaded successfully")
            return True
        except Exception as load_error:
            logger.error(f"Failed to load ASR model: {load_error}")
            return False

    def transcribe_audio(self, audio_path: str) -> ASRResult:
        if not audio_path or not os.path.exists(audio_path):
            return ASRResult(transcribed_text="", detected_language="", confidence_score=0.0)

        if not self.whisper_model:
            model_loaded = self.load_model()
            if not model_loaded:
                return ASRResult(
                    transcribed_text="", detected_language="", confidence_score=0.0
                )

        try:
            transcribe_kwargs = {"beam_size": 5, "vad_filter": True}
            if self.forced_language:
                transcribe_kwargs["language"] = self.forced_language

            segments, detection_info = self.whisper_model.transcribe(
                audio_path, **transcribe_kwargs
            )

            segment_texts = []
            for segment in segments:
                segment_texts.append(segment.text.strip())

            full_text = " ".join(segment_texts).strip()
            detected_lang = detection_info.language if detection_info else ""
            lang_probability = detection_info.language_probability if detection_info else 0.0

            if not full_text:
                logger.info("No speech detected in audio")
                return ASRResult(
                    transcribed_text="",
                    detected_language=detected_lang,
                    confidence_score=lang_probability,
                )

            logger.info(
                f"Transcribed: {full_text[:80]}... "
                f"(lang={detected_lang}, conf={lang_probability:.2f})"
            )
            return ASRResult(
                transcribed_text=full_text,
                detected_language=detected_lang,
                confidence_score=lang_probability,
            )
        except Exception as transcribe_error:
            logger.error(f"Transcription failed: {transcribe_error}")
            return ASRResult(transcribed_text="", detected_language="", confidence_score=0.0)

    def update_config(self, config_manager) -> None:
        new_model_size = config_manager.get_value("asr.model_size", "large-v3")
        new_device_type = config_manager.get_value("asr.device", "auto")
        new_compute_type = config_manager.get_value("asr.compute_type", "auto")
        new_language = config_manager.get_value("asr.language", None)

        model_changed = (
            new_model_size != self.model_size
            or new_device_type != self.device_type
            or new_compute_type != self.compute_type
        )

        self.model_size = new_model_size
        self.device_type = new_device_type
        self.compute_type = new_compute_type
        self.forced_language = new_language

        if model_changed and self.whisper_model:
            logger.info(f"ASR config changed, reloading model: {self.model_size}")
            self.whisper_model = None
            self.load_model()

    def _resolve_device(self) -> str:
        if self.device_type != "auto":
            return self.device_type

        try:
            import ctranslate2
            ctranslate2.get_supported_compute_types("cuda")
            return "cuda"
        except Exception:
            pass

        return "cpu"

    def _resolve_compute_type(self, device_name: str) -> str:
        if self.compute_type != "auto":
            return self.compute_type

        if device_name == "cuda":
            return "float16"
        return "int8"
