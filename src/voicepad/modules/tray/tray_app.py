"""System tray application for VoicePad."""

import logging
import threading

from PIL import Image, ImageDraw

logger = logging.getLogger("voicepad.tray")

ICON_SIZE = 64

ICON_COLORS = {
    "idle": (128, 128, 128),
    "recording": (220, 50, 50),
    "processing": (50, 120, 220),
}


def _create_tray_icon(icon_state: str) -> Image.Image:
    icon_image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw_context = ImageDraw.Draw(icon_image)

    fill_color = ICON_COLORS.get(icon_state, ICON_COLORS["idle"])

    draw_context.ellipse(
        [ICON_SIZE // 4, ICON_SIZE // 8, 3 * ICON_SIZE // 4, 5 * ICON_SIZE // 8],
        fill=fill_color,
    )
    draw_context.rectangle(
        [
            ICON_SIZE // 4 + 4,
            ICON_SIZE // 2,
            3 * ICON_SIZE // 4 - 4,
            3 * ICON_SIZE // 4,
        ],
        fill=fill_color,
    )
    draw_context.arc(
        [ICON_SIZE // 6, ICON_SIZE // 4, 5 * ICON_SIZE // 6, 3 * ICON_SIZE // 4],
        start=0,
        end=180,
        fill=fill_color,
        width=2,
    )
    draw_context.line(
        [ICON_SIZE // 2, 3 * ICON_SIZE // 4, ICON_SIZE // 2, 7 * ICON_SIZE // 8],
        fill=fill_color,
        width=3,
    )
    draw_context.line(
        [
            ICON_SIZE // 3,
            7 * ICON_SIZE // 8,
            2 * ICON_SIZE // 3,
            7 * ICON_SIZE // 8,
        ],
        fill=fill_color,
        width=3,
    )
    return icon_image


class TrayApp:
    def __init__(self, voicepad_app):
        self.voicepad_app = voicepad_app
        self.tray_icon = None
        self.current_state = "idle"

    def run_tray(self) -> None:
        import pystray

        self.tray_icon = pystray.Icon(
            "OpenTypeFewer",
            icon=_create_tray_icon("idle"),
            title="OpenTypeFewer",
            menu=self._build_tray_menu(),
        )
        self.tray_icon.run(setup=self._on_tray_ready)

    def _on_tray_ready(self, icon) -> None:
        icon.visible = True
        self.voicepad_app.on_tray_ready()

    def rebuild_menu(self) -> None:
        if not self.tray_icon:
            return
        try:
            self.tray_icon.menu = self._build_tray_menu()
            self.tray_icon.update_menu()
        except Exception as menu_error:
            logger.warning(f"Menu rebuild failed: {menu_error}")

    def update_icon(self, icon_state: str) -> None:
        self.current_state = icon_state
        if not self.tray_icon:
            return
        try:
            self.tray_icon.icon = _create_tray_icon(icon_state)
        except Exception as icon_error:
            logger.warning(f"Icon update failed: {icon_error}")

    def quit_tray(self) -> None:
        if self.tray_icon:
            self.tray_icon.stop()

    def _build_tray_menu(self):
        import pystray

        i18n = self.voicepad_app.i18n_manager
        config = self.voicepad_app.config_manager

        def get_processing():
            return config.get_value("output.processing", "direct")

        def get_language():
            return config.get_value("output.language", "source")

        def get_backend():
            return config.get_value("llm.backend", "ollama")

        def get_trigger():
            return config.get_value("trigger_mode", "hold")

        def make_processing_handler(style):
            def handler(icon, item):
                config.set_value("output.processing", style)
                config.save_config()
                self.rebuild_menu()
            return handler

        def make_language_handler(lang):
            def handler(icon, item):
                config.set_value("output.language", lang)
                config.save_config()
                self.rebuild_menu()
            return handler

        def make_backend_handler(backend):
            def handler(icon, item):
                config.set_value("llm.backend", backend)
                config.save_config()
                self.rebuild_menu()
            return handler

        def make_trigger_handler(mode):
            def handler(icon, item):
                config.set_value("trigger_mode", mode)
                config.save_config()
                self.voicepad_app.hotkey_manager.update_hotkeys(config)
                self.rebuild_menu()
            return handler

        available_languages = config.get_value("languages", [])
        ui_language = config.get_value("language", "en")

        language_items = []
        for lang_entry in available_languages:
            lang_key = lang_entry["key"]
            if ui_language == "zh":
                lang_label = lang_entry.get("name_zh", lang_entry.get("name_en", lang_key))
            else:
                lang_label = lang_entry.get("name_en", lang_key)

            language_items.append(
                pystray.MenuItem(
                    lang_label,
                    make_language_handler(lang_key),
                    checked=lambda item, lk=lang_key: get_language() == lk,
                    radio=True,
                )
            )

        processing_menu = pystray.Menu(
            pystray.MenuItem(
                i18n.translate("tray.processing.direct"),
                make_processing_handler("direct"),
                checked=lambda item: get_processing() == "direct",
                radio=True,
            ),
            pystray.MenuItem(
                i18n.translate("tray.processing.polish"),
                make_processing_handler("polish"),
                checked=lambda item: get_processing() == "polish",
                radio=True,
            ),
            pystray.MenuItem(
                i18n.translate("tray.processing.custom"),
                make_processing_handler("custom"),
                checked=lambda item: get_processing() == "custom",
                radio=True,
            ),
        )

        language_menu = pystray.Menu(*language_items)

        backend_menu = pystray.Menu(
            pystray.MenuItem(
                i18n.translate("tray.llm_backend.ollama"),
                make_backend_handler("ollama"),
                checked=lambda item: get_backend() == "ollama",
                radio=True,
            ),
            pystray.MenuItem(
                i18n.translate("tray.llm_backend.remote"),
                make_backend_handler("remote"),
                checked=lambda item: get_backend() == "remote",
                radio=True,
            ),
        )

        trigger_menu = pystray.Menu(
            pystray.MenuItem(
                i18n.translate("tray.trigger_mode.hold"),
                make_trigger_handler("hold"),
                checked=lambda item: get_trigger() == "hold",
                radio=True,
            ),
            pystray.MenuItem(
                i18n.translate("tray.trigger_mode.toggle"),
                make_trigger_handler("toggle"),
                checked=lambda item: get_trigger() == "toggle",
                radio=True,
            ),
        )

        return pystray.Menu(
            pystray.MenuItem(
                "Show Panel",
                lambda icon, item: self.voicepad_app.show_panel(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                i18n.translate("tray.processing"), processing_menu
            ),
            pystray.MenuItem(
                i18n.translate("tray.output_language"), language_menu
            ),
            pystray.MenuItem(
                i18n.translate("tray.llm_backend"), backend_menu
            ),
            pystray.MenuItem(
                i18n.translate("tray.trigger_mode"), trigger_menu
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                i18n.translate("tray.settings"),
                lambda icon, item: self.voicepad_app.open_settings(),
            ),
            pystray.MenuItem(
                i18n.translate("tray.quit"),
                lambda icon, item: self.voicepad_app.shutdown(),
            ),
        )
