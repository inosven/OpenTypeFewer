"""Speech recognition engine using faster-whisper."""

import os
import sys
import platform
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("voicepad.asr")

MODEL_CACHE_DIR = str(Path.home() / ".voicepad" / "models")


_preloaded_dlls = []


def _preload_nvidia_dlls() -> None:
    if sys.platform != "win32":
        return

    import ctypes
    import site

    search_roots = site.getsitepackages() + [site.getusersitepackages()]
    target_prefixes = ("cublas", "cublaslt", "cudnn")

    for site_root in search_roots:
        nvidia_dir = Path(site_root) / "nvidia"
        if not nvidia_dir.exists():
            continue
        for dll_file in nvidia_dir.rglob("*.dll"):
            if any(dll_file.name.lower().startswith(p) for p in target_prefixes):
                try:
                    handle = ctypes.WinDLL(str(dll_file))
                    _preloaded_dlls.append(handle)
                except OSError:
                    pass


_preload_nvidia_dlls()


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

            model_dir = os.path.join(MODEL_CACHE_DIR, f"models--Systran--faster-whisper-{self.model_size}")
            model_cached = os.path.exists(model_dir)

            if model_cached:
                logger.info(
                    f"Loading ASR model: {self.model_size} "
                    f"on {resolved_device} with {resolved_compute}"
                )
            else:
                logger.info(
                    f"Downloading ASR model: {self.model_size} "
                    f"(first time, this may take a while)"
                )

            os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

            # cpu_threads=1 prevents ctranslate2 thread-pool crashes in
            # PyInstaller bundles caused by multiple dylib copies being loaded.
            import sys
            cpu_threads = 1 if getattr(sys, "frozen", False) else 0  # 0 = auto
            self.whisper_model = WhisperModel(
                self.model_size,
                device=resolved_device,
                compute_type=resolved_compute,
                download_root=MODEL_CACHE_DIR,
                cpu_threads=cpu_threads,
                num_workers=1,
            )
            logger.info("ASR model loaded successfully")
            return True
        except Exception as load_error:
            logger.error(f"Failed to load ASR model: {load_error}")
            return False

    def transcribe_audio(self, audio_path: str) -> ASRResult:
        if not audio_path or not os.path.exists(audio_path):
            return ASRResult(transcribed_text="", detected_language="", confidence_score=0.0)

        # On macOS frozen bundles, run ASR in an isolated subprocess to avoid
        # ctranslate2 worker-thread crashes (SIGSEGV at 0x4 in JobQueue::get).
        # This crash is macOS-specific; Windows frozen builds use direct inference.
        if getattr(sys, "frozen", False) and platform.system() == "Darwin":
            return self._transcribe_via_subprocess(audio_path)

        if not self.whisper_model:
            model_loaded = self.load_model()
            if not model_loaded:
                return ASRResult(
                    transcribed_text="", detected_language="", confidence_score=0.0
                )

        try:
            import threading
            import time

            transcribe_kwargs = {
                "beam_size": 5,
                "vad_filter": True,
                "vad_parameters": {"threshold": 0.3},
            }
            if self.forced_language:
                transcribe_kwargs["language"] = self.forced_language

            logger.info(f"Starting transcription on {self._resolve_device()}...")

            segments, detection_info = self.whisper_model.transcribe(
                audio_path, **transcribe_kwargs
            )

            segment_texts = []
            transcribe_start = time.monotonic()
            for segment in segments:
                segment_texts.append(segment.text.strip())
                if time.monotonic() - transcribe_start > 30:
                    logger.error("Transcription timed out after 30s")
                    break

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
            if self.device_type == "auto" and self._resolve_device() != "cpu":
                logger.info("CUDA inference failed, falling back to CPU")
                self.whisper_model = None
                self.device_type = "cpu"
                return self.transcribe_audio(audio_path)
            return ASRResult(transcribed_text="", detected_language="", confidence_score=0.0)

    def _transcribe_via_subprocess(self, audio_path: str) -> ASRResult:
        """Run transcription in an isolated subprocess (used when frozen)."""
        import json
        import subprocess

        resolved_device = self._resolve_device()
        resolved_compute = self._resolve_compute_type(resolved_device)

        cmd = [
            sys.executable,
            "--asr-only",
            audio_path,
            self.model_size,
            resolved_device,
            resolved_compute,
        ]
        if self.forced_language:
            cmd += ["--language", self.forced_language]
        cmd += ["--model-cache", MODEL_CACHE_DIR]

        logger.info(f"Running ASR subprocess: {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0:
                logger.error(f"ASR subprocess stderr: {proc.stderr}")
                return ASRResult(transcribed_text="", detected_language="", confidence_score=0.0)

            result = json.loads(proc.stdout.strip())
            if result.get("error"):
                logger.error(f"ASR subprocess error: {result['error']}")
                return ASRResult(transcribed_text="", detected_language="", confidence_score=0.0)

            full_text = result.get("text", "")
            detected_lang = result.get("language", "")
            lang_probability = result.get("confidence", 0.0)

            if full_text:
                logger.info(
                    f"Transcribed: {full_text[:80]}... "
                    f"(lang={detected_lang}, conf={lang_probability:.2f})"
                )
            else:
                logger.info("No speech detected in audio")

            return ASRResult(
                transcribed_text=full_text,
                detected_language=detected_lang,
                confidence_score=lang_probability,
            )
        except subprocess.TimeoutExpired:
            logger.error("ASR subprocess timed out")
            return ASRResult(transcribed_text="", detected_language="", confidence_score=0.0)
        except Exception as sub_error:
            logger.error(f"ASR subprocess failed: {sub_error}")
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
            self._warmup_inference()

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
        # On macOS frozen bundles, int8 can cause ctranslate2 worker-thread
        # crashes; use float32 instead. Windows frozen builds are unaffected.
        if getattr(sys, "frozen", False) and platform.system() == "Darwin":
            return "float32"
        return "int8"

    def _warmup_inference(self) -> None:
        if not self.whisper_model:
            return
        try:
            import numpy
            import time
            logger.info("Warming up ASR model with dummy inference...")
            warmup_start = time.monotonic()
            dummy_audio = numpy.zeros(16000, dtype=numpy.float32)
            segments, _ = self.whisper_model.transcribe(dummy_audio, beam_size=1)
            for _ in segments:
                pass
            warmup_elapsed = time.monotonic() - warmup_start
            logger.info(f"ASR warmup complete in {warmup_elapsed:.1f}s")
        except Exception as warmup_error:
            logger.warning(f"ASR warmup failed: {warmup_error}")
