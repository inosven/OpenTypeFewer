"""Main application controller for VoicePad."""

import os
import sys
import logging
import platform
import threading
import tkinter as tk
from datetime import datetime

IS_MACOS = platform.system() == "Darwin"

from voicepad.config.config_manager import ConfigManager
from voicepad.modules.i18n.i18n_manager import I18nManager
from voicepad.modules.notify.notifier import Notifier
from voicepad.modules.clipboard.clipboard_writer import copy_to_clipboard
from voicepad.modules.recorder.audio_recorder import AudioRecorder
from voicepad.modules.tray.tray_app import TrayApp
from voicepad.modules.settings_window.settings_gui import SettingsGui
from voicepad.subsystems.asr.asr_engine import ASREngine
from voicepad.subsystems.llm_engine.llm_router import LLMRouter
from voicepad.subsystems.hotkey_listener.hotkey_manager import HotkeyManager

PROCESSING_CYCLE = ["direct", "polish", "custom"]

logger = logging.getLogger("voicepad.app")


def _setup_logging(verbose_mode: bool = False) -> None:
    import platform
    if getattr(sys, "frozen", False) and platform.system() == "Darwin":
        # In the macOS bundle, __file__ points inside the temp extraction dir.
        # Write logs to ~/Library/Logs/OpenTypeFewer/ so they persist.
        log_dir = os.path.join(
            os.path.expanduser("~"), "Library", "Logs", "OpenTypeFewer"
        )
    else:
        log_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
        )
    os.makedirs(log_dir, exist_ok=True)

    log_filename = f"voicepad_{datetime.now().strftime('%Y%m%d')}.log"
    log_path = os.path.join(log_dir, log_filename)

    log_level = logging.DEBUG if verbose_mode else logging.INFO
    log_format = "%(asctime)s [%(name)s] %(message)s"
    date_format = "%H:%M:%S"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)

    if verbose_mode:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
        root_logger.addHandler(console_handler)


class VoicePadApp:
    def __init__(self, config_path: str = None, verbose_mode: bool = False):
        _setup_logging(verbose_mode)
        logger.info("OpenTypeFewer starting up")

        self.config_manager = ConfigManager(config_path)
        self.config_manager.load_config()

        ui_language = self.config_manager.get_value("language", "en")
        self.i18n_manager = I18nManager(ui_language)

        self.notifier = Notifier(self.config_manager, self.i18n_manager)
        self.audio_recorder = AudioRecorder(self.config_manager)
        self.asr_engine = ASREngine(self.config_manager)
        self.llm_router = LLMRouter(self.config_manager)

        self.hotkey_manager = HotkeyManager(
            self.config_manager,
            on_start_recording=self.on_start_recording,
            on_stop_recording=self.on_stop_recording,
            on_switch_mode=self.on_switch_mode,
            on_activate_preset=self.on_activate_preset,
        )

        self.tray_app = TrayApp(self)

        # Prevents a second pipeline from starting while ASR/LLM is still running.
        # Without this, pressing the hotkey again during processing spawns concurrent
        # ASR subprocesses that compete for CPU and often both return "no speech".
        self._pipeline_lock = threading.Lock()

        self.tk_root = None
        self.settings_gui = None

    def run(self) -> None:
        if IS_MACOS:
            # On macOS, AppKit (used by pystray) must run on the main thread.
            # We run pystray directly here and skip tkinter mainloop.
            warmup_thread = threading.Thread(target=self._warmup_models, daemon=True)
            warmup_thread.start()

            self.hotkey_manager.start_listening()

            logger.info("OpenTypeFewer running (macOS mode)")
            self.tray_app.run_tray()  # blocks main thread via AppKit run loop
        else:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()

            self.settings_gui = SettingsGui(
                self.config_manager,
                self.i18n_manager,
                on_save_callback=self.reload_config,
                tk_root=self.tk_root,
            )

            tray_thread = threading.Thread(target=self.tray_app.run_tray, daemon=True)
            tray_thread.start()

            warmup_thread = threading.Thread(target=self._warmup_models, daemon=True)
            warmup_thread.start()

            self.hotkey_manager.start_listening()

            logger.info("OpenTypeFewer running (main loop started)")
            self.tk_root.mainloop()

    def _warmup_models(self) -> None:
        logger.info("Pre-loading models at startup")
        self.asr_engine.load_model()

        active_backend = self.config_manager.get_value("llm.backend", "ollama")
        if active_backend == "ollama":
            self.llm_router.initialize_backends()
            self.llm_router.ollama_backend.warm_up_model()

    def on_tray_ready(self) -> None:
        logger.info("Tray ready")

    def on_start_recording(self) -> None:
        logger.info("Recording started")
        try:
            self.notifier.play_sound("start")
            self.tray_app.update_icon("recording")
            self.audio_recorder.start_recording()
        except Exception as start_error:
            logger.error(f"Failed to start recording: {start_error}")

    def on_stop_recording(self) -> None:
        logger.info("Recording stopped")
        try:
            audio_file_path = self.audio_recorder.stop_recording()
            self.notifier.play_sound("stop")
            self.tray_app.update_icon("processing")
        except Exception as stop_error:
            logger.error(f"Failed to stop recording: {stop_error}")
            self.tray_app.update_icon("idle")
            return

        if not audio_file_path:
            self.tray_app.update_icon("idle")
            return

        # Prevent concurrent pipelines: if ASR/LLM is still running from a
        # previous recording, drop this one rather than spawning a second
        # subprocess that will compete for CPU and likely return "no speech".
        if not self._pipeline_lock.acquire(blocking=False):
            logger.warning("Pipeline already running, dropping this recording")
            self.tray_app.update_icon("idle")
            self.notifier.play_sound("error")
            self._cleanup_temp_audio(audio_file_path)
            return

        # Snapshot the output config right now so that a preset switch
        # happening during the (potentially slow) ASR step doesn't change
        # which LLM processing is applied to this recording.
        processing_style = self.config_manager.get_value("output.processing", "direct")
        output_language = self.config_manager.get_value("output.language", "source")
        custom_prompt = self.config_manager.get_value("output.custom_prompt", "")
        logger.info(
            f"Pipeline config snapshot: processing={processing_style}, "
            f"language={output_language}"
        )

        processing_thread = threading.Thread(
            target=self._process_audio_pipeline,
            args=(audio_file_path, processing_style, output_language, custom_prompt),
            daemon=True,
        )
        processing_thread.start()

    def on_switch_mode(self) -> None:
        try:
            current_processing = self.config_manager.get_value("output.processing", "direct")
            current_index = PROCESSING_CYCLE.index(current_processing)
            next_processing = PROCESSING_CYCLE[(current_index + 1) % len(PROCESSING_CYCLE)]

            self.config_manager.set_value("output.processing", next_processing)
            self.config_manager.save_config()

            current_language = self.config_manager.get_value("output.language", "source")
            mode_message = self.i18n_manager.translate(
                "notify.mode_switched",
                processing=next_processing,
                language=current_language,
            )

            self.notifier.send_notification(
                self.i18n_manager.translate("tray.title"),
                mode_message,
            )
            self.tray_app.rebuild_menu()
            logger.info(f"Mode switched to: {next_processing} | {current_language}")
        except Exception as switch_error:
            logger.error(f"Mode switch failed: {switch_error}")

    def on_activate_preset(self, preset_entry: dict) -> None:
        try:
            preset_name = preset_entry.get("name", "Unnamed")
            preset_processing = preset_entry.get("processing", "direct")
            preset_language = preset_entry.get("language", "source")
            preset_prompt = preset_entry.get("custom_prompt", "")

            self.config_manager.set_value("output.processing", preset_processing)
            self.config_manager.set_value("output.language", preset_language)
            self.config_manager.set_value("output.custom_prompt", preset_prompt)
            self.config_manager.save_config()

            self.notifier.send_notification(
                self.i18n_manager.translate("tray.title"),
                self.i18n_manager.translate(
                    "notify.preset_activated", name=preset_name
                ),
            )
            self.notifier.play_sound("done")
            self.tray_app.rebuild_menu()
            self.tray_app.flash_preset_name(preset_name)
            logger.info(
                f"Preset activated: {preset_name} "
                f"(processing={preset_processing}, language={preset_language})"
            )
        except Exception as preset_error:
            logger.error(f"Preset activation failed: {preset_error}")

    def open_settings(self) -> None:
        if IS_MACOS:
            # On macOS, pystray owns the main thread (AppKit), so tkinter must
            # run in a separate process that has its own main thread.
            import subprocess
            config_path = str(self.config_manager.config_path)
            language = self.config_manager.get_value("language", "en")
            if getattr(sys, "frozen", False):
                # PyInstaller bundle: use the bundled executable with an internal flag
                cmd = [sys.executable, "--settings-only", config_path, language]
            else:
                # Development: run the settings module directly
                cmd = [sys.executable, "-m", "voicepad.settings_subprocess", config_path, language]
            proc = subprocess.Popen(cmd)
            # Reload config after the settings window closes.
            def _watch_settings_proc():
                proc.wait()
                self.reload_config()
            threading.Thread(target=_watch_settings_proc, daemon=True).start()
        elif self.tk_root and self.settings_gui:
            self.tk_root.after(0, self.settings_gui.show_window)

    def reload_config(self) -> None:
        logger.info("Reloading configuration")
        self.config_manager.load_config()

        new_language = self.config_manager.get_value("language", "en")
        self.i18n_manager.set_language(new_language)

        self.asr_engine.update_config(self.config_manager)
        self.llm_router.update_config(self.config_manager)
        self.hotkey_manager.update_hotkeys(self.config_manager)
        self.tray_app.rebuild_menu()
        logger.info("Configuration reloaded")

    def shutdown(self) -> None:
        logger.info("OpenTypeFewer shutting down")
        self.hotkey_manager.stop_listening()
        self.tray_app.quit_tray()
        if self.tk_root:
            self.tk_root.after(0, self.tk_root.destroy)

    def _process_audio_pipeline(
        self,
        audio_file_path: str,
        processing_style: str = "direct",
        output_language: str = "source",
        custom_prompt: str = "",
    ) -> None:
        try:
            asr_result = self.asr_engine.transcribe_audio(audio_file_path)

            if not asr_result.transcribed_text:
                self.notifier.send_notification(
                    self.i18n_manager.translate("tray.title"),
                    self.i18n_manager.translate("notify.no_speech"),
                )
                self.notifier.play_sound("error")
                self.tray_app.update_icon("idle")
                return

            logger.info(
                f"ASR result: {asr_result.transcribed_text[:120]} "
                f"(lang={asr_result.detected_language}, conf={asr_result.confidence_score:.2f})"
            )

            final_text = self.llm_router.process_text(
                asr_result.transcribed_text,
                processing_style,
                output_language,
                custom_prompt,
            )

            clipboard_success = copy_to_clipboard(final_text)
            if clipboard_success:
                import time
                time.sleep(0.05)
                if IS_MACOS:
                    from pynput.keyboard import Controller as KbController, Key
                    _kb = KbController()
                    with _kb.pressed(Key.cmd):
                        _kb.press('v')
                        _kb.release('v')
                else:
                    import keyboard
                    keyboard.send("ctrl+v")
                logger.info("Auto-pasted to cursor position")

                preview_text = final_text[:50]
                if len(final_text) > 50:
                    preview_text += "..."
                self.notifier.send_notification(
                    self.i18n_manager.translate("notify.done"),
                    preview_text,
                )
                self.notifier.play_sound("done")
            else:
                self.notifier.send_notification(
                    self.i18n_manager.translate("tray.title"),
                    self.i18n_manager.translate("notify.error"),
                )
                self.notifier.play_sound("error")

        except Exception as pipeline_error:
            logger.error(f"Pipeline failed: {pipeline_error}")
            self.notifier.send_notification(
                self.i18n_manager.translate("tray.title"),
                self.i18n_manager.translate("notify.error"),
            )
            self.notifier.play_sound("error")
        finally:
            self._pipeline_lock.release()
            self.tray_app.update_icon("idle")
            self._cleanup_temp_audio(audio_file_path)

    def _cleanup_temp_audio(self, audio_file_path: str) -> None:
        try:
            if audio_file_path and os.path.exists(audio_file_path):
                os.remove(audio_file_path)
        except OSError as cleanup_error:
            logger.warning(f"Failed to clean up temp audio: {cleanup_error}")
