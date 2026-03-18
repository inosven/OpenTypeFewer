"""Standalone settings window subprocess.

Launched as a subprocess on macOS where pystray owns the main thread,
so pywebview must run in a separate process that has its own main thread.

Usage: python -m voicepad.settings_subprocess <config_path>
"""

import sys
from pathlib import Path


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    from voicepad.config.config_manager import ConfigManager
    from voicepad.modules.main_window.window_api import WindowApi

    config_manager = ConfigManager(config_path)
    config_manager.load_config()

    settings_html_path = _resolve_frontend_path("settings.html")

    window_api = WindowApi(
        config_manager=config_manager,
        status_file_path="temp/ui_status.json",
        open_settings_callback=None,
    )

    import webview

    webview.create_window(
        title="OpenTypeFewer — Settings",
        url=settings_html_path,
        js_api=window_api,
        width=780,
        height=720,
        resizable=True,
        background_color="#1c1c1e",
    )

    webview.start(debug=False)


def _resolve_frontend_path(filename: str) -> str:
    frontend_dir = Path(__file__).parent / "modules" / "main_window" / "frontend"
    return str(frontend_dir / filename)


if __name__ == "__main__":
    main()
