"""Notification and sound playback for VoicePad."""

import os
import sys
import logging
import platform
import threading

logger = logging.getLogger("voicepad.notify")


def _get_resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", relative_path
    )


class Notifier:
    def __init__(self, config_manager, i18n_manager):
        self.config_manager = config_manager
        self.i18n_manager = i18n_manager
        self.platform_name = platform.system()

    def send_notification(self, title: str, message: str) -> None:
        if not self.config_manager.get_value("notification.enabled", True):
            return

        try:
            if self.platform_name == "Darwin":
                self._send_notification_macos(title, message)
            else:
                from plyer import notification as plyer_notification
                plyer_notification.notify(
                    title=title,
                    message=message,
                    app_name="OpenTypeFewer",
                    timeout=3,
                )
        except Exception as notify_error:
            logger.error(f"Notification failed: {notify_error}")

    def _send_notification_macos(self, title: str, message: str) -> None:
        import subprocess
        safe_title = title.replace('\\', '\\\\').replace('"', '\\"')
        safe_message = message.replace('\\', '\\\\').replace('"', '\\"')
        script = f'display notification "{safe_message}" with title "{safe_title}"'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                logger.warning(f"osascript notification failed: {result.stderr.strip()}")
        except Exception as e:
            logger.warning(f"osascript notification error: {e}")

    def play_sound(self, sound_type: str) -> None:
        if not self.config_manager.get_value("notification.sound_enabled", True):
            return

        sound_filename = self.config_manager.get_value(
            f"notification.sound_{sound_type}", f"{sound_type}.wav"
        )
        sound_path = _get_resource_path(os.path.join("sounds", sound_filename))

        if not os.path.exists(sound_path):
            logger.warning(f"Sound file not found: {sound_path}")
            return

        playback_thread = threading.Thread(
            target=self._play_sound_file,
            args=(sound_path,),
            daemon=True,
        )
        playback_thread.start()

    def _play_sound_file(self, sound_path: str) -> None:
        try:
            if self.platform_name == "Darwin":
                os.system(f'afplay "{sound_path}" &')
            elif self.platform_name == "Windows":
                import winsound
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                os.system(f'aplay "{sound_path}" &')
        except Exception as play_error:
            logger.error(f"Sound playback failed: {play_error}")
