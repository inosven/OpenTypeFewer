"""Standalone settings window process.

Launched as a subprocess on macOS where pystray owns the main thread,
so tkinter/customtkinter must run in a separate process.

Usage: python -m voicepad.settings_subprocess <config_path> <language>
"""

import sys
import tkinter as tk


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    language = sys.argv[2] if len(sys.argv) > 2 else "en"

    from voicepad.config.config_manager import ConfigManager
    from voicepad.modules.i18n.i18n_manager import I18nManager
    from voicepad.modules.settings_window.settings_gui import SettingsGui

    config_manager = ConfigManager(config_path)
    config_manager.load_config()
    i18n_manager = I18nManager(language)

    root = tk.Tk()
    root.withdraw()

    gui = SettingsGui(
        config_manager,
        i18n_manager,
        on_save_callback=lambda: None,  # config already saved by SettingsGui
        tk_root=root,
    )
    gui.show_window()

    def _check_closed():
        if gui.window_open:
            root.after(200, _check_closed)
        else:
            root.quit()

    root.after(200, _check_closed)
    root.mainloop()


if __name__ == "__main__":
    main()
