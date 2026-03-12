"""Standalone ASR subprocess.

Runs faster-whisper transcription in an isolated process so that ctranslate2
native crashes do not take down the main app bundle.

Usage (internal):
    sys.executable --asr-only <audio_path> <model_size> <device> <compute_type>
        [--language <lang>] [--model-cache <dir>]

Output: one JSON line to stdout with keys:
    text, language, confidence, error
"""

import json
import sys


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path")
    parser.add_argument("model_size")
    parser.add_argument("device")
    parser.add_argument("compute_type")
    parser.add_argument("--language", default=None)
    parser.add_argument("--model-cache", default=None)
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel
        import os

        model_kwargs = dict(
            device=args.device,
            compute_type=args.compute_type,
            cpu_threads=1,
            num_workers=1,
        )
        if args.model_cache:
            model_kwargs["download_root"] = args.model_cache

        model = WhisperModel(args.model_size, **model_kwargs)

        transcribe_kwargs = {
            "beam_size": 5,
            "vad_filter": True,
            "vad_parameters": {"threshold": 0.3},
        }
        if args.language and args.language != "auto":
            transcribe_kwargs["language"] = args.language

        segments, info = model.transcribe(args.audio_path, **transcribe_kwargs)
        text = " ".join(s.text.strip() for s in segments).strip()

        result = {
            "text": text,
            "language": info.language if info else "",
            "confidence": info.language_probability if info else 0.0,
            "error": None,
        }
    except Exception as e:
        result = {"text": "", "language": "", "confidence": 0.0, "error": str(e)}

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
