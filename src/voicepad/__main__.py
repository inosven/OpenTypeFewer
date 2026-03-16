"""CLI entry point for VoicePad."""

import argparse
import sys

# ── PyInstaller + multiprocessing fix ─────────────────────────────────────────
# When frozen, sys.executable is our binary. Python's multiprocessing spawns
# subprocesses via: our_binary -c "some python code"
# We must intercept -c before argparse sees it and crashes.
if getattr(sys, "frozen", False):
    import multiprocessing
    multiprocessing.freeze_support()
    try:
        c_idx = sys.argv.index("-c")
        exec(" ".join(sys.argv[c_idx + 1:]))  # noqa: S102
        sys.exit(0)
    except ValueError:
        pass


def _run_settings_only() -> None:
    """Show only the settings window. Used as subprocess on macOS."""
    from voicepad.settings_subprocess import main as settings_main
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    settings_main()


def _run_panel_only() -> None:
    """Show only the mini panel. Used as subprocess."""
    from voicepad.panel_subprocess import main as panel_main
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    panel_main()


def main() -> None:
    # Internal flag used when spawning settings window as a subprocess on macOS
    if len(sys.argv) >= 2 and sys.argv[1] == "--settings-only":
        _run_settings_only()
        return

    # Internal flag used when spawning mini panel as a subprocess
    if len(sys.argv) >= 2 and sys.argv[1] == "--panel-only":
        _run_panel_only()
        return

    # Internal flag used when running ASR in an isolated subprocess
    if len(sys.argv) >= 2 and sys.argv[1] == "--asr-only":
        sys.argv = [sys.argv[0]] + sys.argv[2:]  # strip the flag for argparse inside
        from voicepad.asr_subprocess import main as asr_main
        asr_main()
        return

    arg_parser = argparse.ArgumentParser(
        prog="voicepad",
        description="VoicePad - Local voice-to-clipboard tool",
    )

    arg_parser.add_argument(
        "--config", type=str, default=None, help="Config file path"
    )
    arg_parser.add_argument(
        "--processing",
        type=str,
        choices=["direct", "polish", "custom"],
        help="Set processing style",
    )
    arg_parser.add_argument(
        "--language", type=str, help="Set output language (source/zh/en)"
    )
    arg_parser.add_argument(
        "--ui-language",
        type=str,
        choices=["en", "zh"],
        help="Set interface language",
    )
    arg_parser.add_argument(
        "--list-devices", action="store_true", help="List audio input devices"
    )
    arg_parser.add_argument(
        "--test-mic", action="store_true", help="Test microphone (3 second recording)"
    )
    arg_parser.add_argument(
        "--test-asr", action="store_true", help="Test ASR (5 second recording)"
    )
    arg_parser.add_argument(
        "--test-llm", action="store_true", help="Test LLM connection"
    )
    arg_parser.add_argument(
        "--download-model", type=str, metavar="SIZE", help="Download faster-whisper model"
    )
    arg_parser.add_argument(
        "--version", action="store_true", help="Show version"
    )
    arg_parser.add_argument(
        "--verbose", action="store_true", help="Verbose logging"
    )

    parsed_args = arg_parser.parse_args()

    if parsed_args.version:
        from voicepad import __version__
        print(f"VoicePad v{__version__}")
        return

    if parsed_args.list_devices:
        _list_audio_devices()
        return

    if parsed_args.download_model:
        _download_model(parsed_args.download_model)
        return

    if parsed_args.test_mic:
        _test_microphone(parsed_args.config)
        return

    if parsed_args.test_asr:
        _test_asr(parsed_args.config)
        return

    if parsed_args.test_llm:
        _test_llm(parsed_args.config)
        return

    from voicepad.app import VoicePadApp
    from voicepad.config.config_manager import ConfigManager

    voicepad_app = VoicePadApp(
        config_path=parsed_args.config,
        verbose_mode=parsed_args.verbose,
    )

    if parsed_args.processing:
        voicepad_app.config_manager.set_value("output.processing", parsed_args.processing)
    if parsed_args.language:
        voicepad_app.config_manager.set_value("output.language", parsed_args.language)
    if parsed_args.ui_language:
        voicepad_app.config_manager.set_value("language", parsed_args.ui_language)
        voicepad_app.i18n_manager.set_language(parsed_args.ui_language)

    voicepad_app.run()


def _list_audio_devices() -> None:
    try:
        import sounddevice
        print(sounddevice.query_devices())
    except Exception as device_error:
        print(f"Failed to list devices: {device_error}")


def _download_model(model_size: str) -> None:
    print(f"Downloading faster-whisper model: {model_size}")
    try:
        from voicepad.subsystems.asr.asr_engine import ASREngine
        from voicepad.config.config_manager import ConfigManager

        config_manager = ConfigManager()
        config_manager.load_config()
        config_manager.set_value("asr.model_size", model_size)

        asr_engine = ASREngine(config_manager)
        success = asr_engine.load_model()
        if success:
            print(f"Model {model_size} downloaded successfully")
        else:
            print(f"Failed to download model {model_size}")
    except Exception as download_error:
        print(f"Download failed: {download_error}")


def _test_microphone(config_path: str = None) -> None:
    import time

    from voicepad.config.config_manager import ConfigManager
    from voicepad.modules.recorder.audio_recorder import AudioRecorder

    config_manager = ConfigManager(config_path)
    config_manager.load_config()

    recorder = AudioRecorder(config_manager)
    print("Testing microphone for 3 seconds...")
    recorder.start_recording()
    time.sleep(3)
    output_path = recorder.stop_recording()

    if output_path:
        print(f"Microphone test complete. Audio saved to: {output_path}")
    else:
        print("Microphone test failed - no audio captured")


def _test_asr(config_path: str = None) -> None:
    import time

    from voicepad.config.config_manager import ConfigManager
    from voicepad.modules.recorder.audio_recorder import AudioRecorder
    from voicepad.subsystems.asr.asr_engine import ASREngine

    config_manager = ConfigManager(config_path)
    config_manager.load_config()

    recorder = AudioRecorder(config_manager)
    print("Recording 5 seconds for ASR test...")
    recorder.start_recording()
    time.sleep(5)
    audio_path = recorder.stop_recording()

    if not audio_path:
        print("Failed to record audio")
        return

    asr_engine = ASREngine(config_manager)
    asr_result = asr_engine.transcribe_audio(audio_path)
    print(f"ASR Result: {asr_result.transcribed_text}")
    print(f"Language: {asr_result.detected_language}")
    print(f"Confidence: {asr_result.confidence_score:.2f}")


def _test_llm(config_path: str = None) -> None:
    from voicepad.config.config_manager import ConfigManager
    from voicepad.subsystems.llm_engine.llm_router import LLMRouter

    config_manager = ConfigManager(config_path)
    config_manager.load_config()

    llm_router = LLMRouter(config_manager)
    llm_router.initialize_backends()

    test_text = "Hello, this is a test of the LLM connection."
    print("Testing LLM connection...")

    result = llm_router.process_text(test_text, "polish", "source")
    if result and result != test_text:
        print(f"LLM Response: {result}")
    else:
        print("LLM connection test failed or returned original text")


if __name__ == "__main__":
    main()
