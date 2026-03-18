"""Standalone mini panel subprocess.

Launched as a subprocess (macOS and Windows) to show the floating status panel.
pywebview needs the main thread, so it must run in its own process.

Usage: python -m voicepad.panel_subprocess <config_path> <status_file_path>
"""

import os
import sys
import threading
import time
from pathlib import Path


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    status_file_path = sys.argv[2] if len(sys.argv) > 2 else "temp/ui_status.json"

    from voicepad.config.config_manager import ConfigManager
    from voicepad.modules.main_window.window_api import WindowApi

    config_manager = ConfigManager(config_path)
    config_manager.load_config()

    panel_html_path = _resolve_frontend_path("panel.html")

    window_api = WindowApi(
        config_manager=config_manager,
        status_file_path=status_file_path,
        open_settings_callback=_signal_open_settings,
    )

    import webview

    panel_window = webview.create_window(
        title="OpenTypeFewer",
        url=panel_html_path,
        js_api=window_api,
        width=200,
        height=260,
        resizable=False,
        frameless=True,
        on_top=True,
        background_color="#1c1c1e",
    )
    window_api._window = panel_window

    threading.Thread(
        target=_watch_restore_signal, args=(window_api,), daemon=True
    ).start()

    webview.start(debug=False)


def _resolve_frontend_path(filename: str) -> str:
    frontend_dir = Path(__file__).parent / "modules" / "main_window" / "frontend"
    return str(frontend_dir / filename)


def _resolve_signal_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.path.expanduser("~")) / ".opentypefewer" / "open_settings.signal"
    return Path(__file__).parent.parent.parent / "temp" / "open_settings.signal"


def _resolve_restore_signal_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.path.expanduser("~")) / ".opentypefewer" / "restore_panel.signal"
    return Path(__file__).parent.parent.parent / "temp" / "restore_panel.signal"


def _signal_open_settings() -> None:
    signal_file = _resolve_signal_path()
    signal_file.parent.mkdir(parents=True, exist_ok=True)
    signal_file.write_text("open")


def _watch_restore_signal(window_api) -> None:
    restore_path = _resolve_restore_signal_path()
    while True:
        if restore_path.exists():
            try:
                restore_path.unlink()
            except OSError:
                pass
            window_api.restore_window()
        time.sleep(0.3)


if __name__ == "__main__":
    main()
