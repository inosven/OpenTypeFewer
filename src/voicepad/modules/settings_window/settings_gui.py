"""Settings window GUI for VoicePad."""

import logging

logger = logging.getLogger("voicepad.settings")

MODIFIER_SORT_ORDER = {"ctrl": 0, "alt": 1, "shift": 2, "windows": 3}


def _sort_hotkey_keys(key_set: set) -> list:
    modifier_keys = []
    regular_keys = []
    for key_name in key_set:
        if key_name in MODIFIER_SORT_ORDER:
            modifier_keys.append(key_name)
        else:
            regular_keys.append(key_name)
    modifier_keys.sort(key=lambda m: MODIFIER_SORT_ORDER.get(m, 99))
    return modifier_keys + sorted(regular_keys)


class SettingsGui:
    def __init__(self, config_manager, i18n_manager, on_save_callback, tk_root=None):
        self.config_manager = config_manager
        self.i18n_manager = i18n_manager
        self.on_save_callback = on_save_callback
        self.tk_root = tk_root
        self.settings_window = None
        self.window_open = False

    def show_window(self) -> None:
        if self.window_open:
            if self.settings_window:
                self.settings_window.lift()
                self.settings_window.focus_force()
            return

        self._create_window()

    def close_window(self) -> None:
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None
        self.window_open = False

    def _create_window(self) -> None:
        import customtkinter

        self.window_open = True
        i18n = self.i18n_manager

        self.settings_window = customtkinter.CTkToplevel(self.tk_root)
        self.settings_window.title(i18n.translate("settings.title"))
        self.settings_window.geometry("600x580")
        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_window)
        self.settings_window.after(100, self.settings_window.lift)

        tab_view = customtkinter.CTkTabview(self.settings_window)
        tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        general_tab = tab_view.add(i18n.translate("settings.tab.general"))
        asr_tab = tab_view.add(i18n.translate("settings.tab.asr"))
        llm_tab = tab_view.add(i18n.translate("settings.tab.llm"))
        output_tab = tab_view.add(i18n.translate("settings.tab.output"))
        presets_tab = tab_view.add(i18n.translate("settings.tab.presets"))
        hotkeys_tab = tab_view.add(i18n.translate("settings.tab.hotkeys"))
        about_tab = tab_view.add(i18n.translate("settings.tab.about"))

        self._build_general_tab(general_tab)
        self._build_asr_tab(asr_tab)
        self._build_llm_tab(llm_tab)
        self._build_output_tab(output_tab)
        self._build_presets_tab(presets_tab)
        self._build_hotkeys_tab(hotkeys_tab)
        self._build_about_tab(about_tab)

        button_frame = customtkinter.CTkFrame(self.settings_window)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        save_button = customtkinter.CTkButton(
            button_frame,
            text=i18n.translate("settings.save"),
            command=self._save_settings,
        )
        save_button.pack(side="right", padx=5)

        cancel_button = customtkinter.CTkButton(
            button_frame,
            text=i18n.translate("settings.cancel"),
            command=self.close_window,
        )
        cancel_button.pack(side="right", padx=5)

    def _build_general_tab(self, parent_frame) -> None:
        import customtkinter

        i18n = self.i18n_manager
        config = self.config_manager

        row_index = 0

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.language")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.language_var = customtkinter.StringVar(
            value=config.get_value("language", "en")
        )
        language_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.language_var,
            values=["en", "zh"],
        )
        language_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.trigger_mode")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.trigger_mode_var = customtkinter.StringVar(
            value=config.get_value("trigger_mode", "hold")
        )
        trigger_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.trigger_mode_var,
            values=["hold", "toggle"],
        )
        trigger_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)
        row_index += 1

        self.sound_enabled_var = customtkinter.BooleanVar(
            value=config.get_value("notification.sound_enabled", True)
        )
        sound_checkbox = customtkinter.CTkCheckBox(
            parent_frame,
            text=i18n.translate("settings.sound.enabled"),
            variable=self.sound_enabled_var,
        )
        sound_checkbox.grid(
            row=row_index, column=0, columnspan=2, sticky="w", padx=10, pady=5
        )
        row_index += 1

        self.notification_enabled_var = customtkinter.BooleanVar(
            value=config.get_value("notification.enabled", True)
        )
        notification_checkbox = customtkinter.CTkCheckBox(
            parent_frame,
            text=i18n.translate("settings.notification.enabled"),
            variable=self.notification_enabled_var,
        )
        notification_checkbox.grid(
            row=row_index, column=0, columnspan=2, sticky="w", padx=10, pady=5
        )

    def _build_asr_tab(self, parent_frame) -> None:
        import customtkinter

        i18n = self.i18n_manager
        config = self.config_manager

        row_index = 0
        model_sizes = ["tiny", "base", "small", "medium", "large-v3"]

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.asr.model_size")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.model_size_var = customtkinter.StringVar(
            value=config.get_value("asr.model_size", "large-v3")
        )
        model_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.model_size_var,
            values=model_sizes,
        )
        model_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.asr.device")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.device_var = customtkinter.StringVar(
            value=config.get_value("asr.device", "auto")
        )
        device_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.device_var,
            values=["auto", "cpu", "cuda"],
        )
        device_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)

    def _build_llm_tab(self, parent_frame) -> None:
        import customtkinter

        i18n = self.i18n_manager
        config = self.config_manager

        row_index = 0

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.llm.backend")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.backend_var = customtkinter.StringVar(
            value=config.get_value("llm.backend", "ollama")
        )
        backend_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.backend_var,
            values=["ollama", "remote"],
        )
        backend_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.llm.ollama.model")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.ollama_model_var = customtkinter.StringVar(
            value=config.get_value("llm.ollama.model", "qwen3.5")
        )
        ollama_model_entry = customtkinter.CTkEntry(
            parent_frame, textvariable=self.ollama_model_var
        )
        ollama_model_entry.grid(row=row_index, column=1, sticky="ew", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.llm.ollama.url")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.ollama_url_var = customtkinter.StringVar(
            value=config.get_value("llm.ollama.base_url", "http://localhost:11434")
        )
        ollama_url_entry = customtkinter.CTkEntry(
            parent_frame, textvariable=self.ollama_url_var
        )
        ollama_url_entry.grid(row=row_index, column=1, sticky="ew", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.llm.remote.provider")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.remote_provider_var = customtkinter.StringVar(
            value=config.get_value("llm.remote.provider", "anthropic")
        )
        provider_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.remote_provider_var,
            values=["anthropic", "openai"],
        )
        provider_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.llm.remote.model")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.remote_model_var = customtkinter.StringVar(
            value=config.get_value("llm.remote.model", "claude-sonnet-4-20250514")
        )
        remote_model_entry = customtkinter.CTkEntry(
            parent_frame, textvariable=self.remote_model_var
        )
        remote_model_entry.grid(row=row_index, column=1, sticky="ew", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.llm.remote.api_key")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.api_key_var = customtkinter.StringVar(
            value=config.get_value("llm.remote.api_key", "")
        )
        api_key_entry = customtkinter.CTkEntry(
            parent_frame, textvariable=self.api_key_var, show="*"
        )
        api_key_entry.grid(row=row_index, column=1, sticky="ew", padx=10, pady=5)

    def _build_output_tab(self, parent_frame) -> None:
        import customtkinter

        i18n = self.i18n_manager
        config = self.config_manager

        row_index = 0

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.output.processing")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.processing_var = customtkinter.StringVar(
            value=config.get_value("output.processing", "direct")
        )
        processing_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.processing_var,
            values=["direct", "polish", "custom"],
        )
        processing_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.output.language")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        available_langs = config.get_value("languages", [])
        language_keys = [lang["key"] for lang in available_langs]

        self.output_language_var = customtkinter.StringVar(
            value=config.get_value("output.language", "source")
        )
        language_dropdown = customtkinter.CTkOptionMenu(
            parent_frame,
            variable=self.output_language_var,
            values=language_keys if language_keys else ["source"],
        )
        language_dropdown.grid(row=row_index, column=1, sticky="w", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.output.custom_prompt")
        ).grid(row=row_index, column=0, sticky="nw", padx=10, pady=5)

        self.custom_prompt_textbox = customtkinter.CTkTextbox(
            parent_frame, height=120
        )
        self.custom_prompt_textbox.grid(
            row=row_index, column=1, sticky="ew", padx=10, pady=5
        )
        current_prompt = config.get_value("output.custom_prompt", "")
        if current_prompt:
            self.custom_prompt_textbox.insert("1.0", current_prompt)

    def _build_presets_tab(self, parent_frame) -> None:
        import customtkinter

        i18n = self.i18n_manager
        config = self.config_manager

        self.preset_widgets = []
        saved_presets = config.get_value("presets", [])

        self.presets_scroll_frame = customtkinter.CTkScrollableFrame(parent_frame)
        self.presets_scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.presets_scroll_frame.columnconfigure(1, weight=1)

        for preset_data in saved_presets:
            self._add_preset_row(preset_data)

        add_button = customtkinter.CTkButton(
            parent_frame,
            text=i18n.translate("settings.presets.add"),
            command=self._add_empty_preset_row,
        )
        add_button.pack(pady=5)

    def _add_preset_row(self, preset_data: dict = None) -> None:
        import customtkinter

        i18n = self.i18n_manager
        scroll_frame = self.presets_scroll_frame
        preset_index = len(self.preset_widgets)

        row_frame = customtkinter.CTkFrame(scroll_frame)
        row_frame.pack(fill="x", pady=(0, 10), padx=5)
        row_frame.columnconfigure(1, weight=1)

        name_var = customtkinter.StringVar(
            value=preset_data.get("name", "") if preset_data else ""
        )
        customtkinter.CTkLabel(
            row_frame, text=i18n.translate("settings.presets.name")
        ).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        customtkinter.CTkEntry(
            row_frame, textvariable=name_var
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        hotkey_var = customtkinter.StringVar(
            value=preset_data.get("hotkey", "") if preset_data else ""
        )
        customtkinter.CTkLabel(
            row_frame, text=i18n.translate("settings.presets.hotkey")
        ).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        preset_hotkey_entry = self._create_hotkey_entry(row_frame, hotkey_var)
        preset_hotkey_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        processing_var = customtkinter.StringVar(
            value=preset_data.get("processing", "polish") if preset_data else "polish"
        )
        customtkinter.CTkLabel(
            row_frame, text=i18n.translate("settings.presets.processing")
        ).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        customtkinter.CTkOptionMenu(
            row_frame,
            variable=processing_var,
            values=["direct", "polish", "custom"],
        ).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        available_langs = self.config_manager.get_value("languages", [])
        language_keys = [lang["key"] for lang in available_langs]
        language_var = customtkinter.StringVar(
            value=preset_data.get("language", "source") if preset_data else "source"
        )
        customtkinter.CTkLabel(
            row_frame, text=i18n.translate("settings.presets.language")
        ).grid(row=3, column=0, sticky="w", padx=5, pady=2)
        customtkinter.CTkOptionMenu(
            row_frame,
            variable=language_var,
            values=language_keys if language_keys else ["source"],
        ).grid(row=3, column=1, sticky="w", padx=5, pady=2)

        customtkinter.CTkLabel(
            row_frame, text=i18n.translate("settings.presets.custom_prompt")
        ).grid(row=4, column=0, sticky="nw", padx=5, pady=2)
        prompt_textbox = customtkinter.CTkTextbox(row_frame, height=60)
        prompt_textbox.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        if preset_data and preset_data.get("custom_prompt"):
            prompt_textbox.insert("1.0", preset_data["custom_prompt"])

        delete_button = customtkinter.CTkButton(
            row_frame,
            text=i18n.translate("settings.presets.delete"),
            width=80,
            fg_color="red",
            hover_color="darkred",
            command=lambda idx=preset_index: self._delete_preset_row(idx),
        )
        delete_button.grid(row=0, column=2, rowspan=2, padx=5, pady=2)

        widget_group = {
            "frame": row_frame,
            "name_var": name_var,
            "hotkey_var": hotkey_var,
            "processing_var": processing_var,
            "language_var": language_var,
            "prompt_textbox": prompt_textbox,
            "deleted": False,
        }
        self.preset_widgets.append(widget_group)

    def _add_empty_preset_row(self) -> None:
        self._add_preset_row()

    def _delete_preset_row(self, preset_index: int) -> None:
        if preset_index >= len(self.preset_widgets):
            return

        widget_group = self.preset_widgets[preset_index]
        widget_group["deleted"] = True
        widget_group["frame"].pack_forget()
        widget_group["frame"].destroy()

    def _collect_presets_data(self) -> list:
        collected_presets = []
        for widget_group in self.preset_widgets:
            if widget_group["deleted"]:
                continue
            collected_presets.append({
                "name": widget_group["name_var"].get(),
                "hotkey": widget_group["hotkey_var"].get(),
                "processing": widget_group["processing_var"].get(),
                "language": widget_group["language_var"].get(),
                "custom_prompt": widget_group["prompt_textbox"].get("1.0", "end").strip(),
            })
        return collected_presets

    def _build_hotkeys_tab(self, parent_frame) -> None:
        import customtkinter

        i18n = self.i18n_manager
        config = self.config_manager

        row_index = 0

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.hotkey.record")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.record_hotkey_var = customtkinter.StringVar(
            value=config.get_value("hotkey", "ctrl+shift+space")
        )
        record_hotkey_entry = self._create_hotkey_entry(
            parent_frame, self.record_hotkey_var
        )
        record_hotkey_entry.grid(row=row_index, column=1, sticky="ew", padx=10, pady=5)
        row_index += 1

        customtkinter.CTkLabel(
            parent_frame, text=i18n.translate("settings.hotkey.switch_mode")
        ).grid(row=row_index, column=0, sticky="w", padx=10, pady=5)

        self.switch_hotkey_var = customtkinter.StringVar(
            value=config.get_value("mode_switch_hotkey", "ctrl+shift+m")
        )
        switch_hotkey_entry = self._create_hotkey_entry(
            parent_frame, self.switch_hotkey_var
        )
        switch_hotkey_entry.grid(row=row_index, column=1, sticky="ew", padx=10, pady=5)

    def _build_about_tab(self, parent_frame) -> None:
        import customtkinter

        customtkinter.CTkLabel(
            parent_frame,
            text="VoicePad",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        ).pack(pady=(20, 5))

        from voicepad import __version__
        customtkinter.CTkLabel(
            parent_frame, text=f"v{__version__}"
        ).pack(pady=5)

        customtkinter.CTkLabel(
            parent_frame,
            text="Local, open-source voice-to-clipboard tool.",
        ).pack(pady=5)

        customtkinter.CTkLabel(
            parent_frame, text="License: MIT"
        ).pack(pady=5)

    def _save_settings(self) -> None:
        config = self.config_manager

        config.set_value("language", self.language_var.get())
        config.set_value("trigger_mode", self.trigger_mode_var.get())
        config.set_value("notification.sound_enabled", self.sound_enabled_var.get())
        config.set_value("notification.enabled", self.notification_enabled_var.get())

        config.set_value("asr.model_size", self.model_size_var.get())
        config.set_value("asr.device", self.device_var.get())

        config.set_value("llm.backend", self.backend_var.get())
        config.set_value("llm.ollama.model", self.ollama_model_var.get())
        config.set_value("llm.ollama.base_url", self.ollama_url_var.get())
        config.set_value("llm.remote.provider", self.remote_provider_var.get())
        config.set_value("llm.remote.model", self.remote_model_var.get())
        config.set_value("llm.remote.api_key", self.api_key_var.get())

        config.set_value("output.processing", self.processing_var.get())
        config.set_value("output.language", self.output_language_var.get())
        config.set_value(
            "output.custom_prompt",
            self.custom_prompt_textbox.get("1.0", "end").strip(),
        )

        config.set_value("presets", self._collect_presets_data())

        config.set_value("hotkey", self.record_hotkey_var.get())
        config.set_value("mode_switch_hotkey", self.switch_hotkey_var.get())

        config.save_config()

        if self.on_save_callback:
            self.on_save_callback()

        self._show_saved_label()

    def _create_hotkey_entry(self, parent_frame, text_variable):
        import customtkinter

        entry = customtkinter.CTkEntry(parent_frame, textvariable=text_variable)

        MODIFIER_KEYSYMS = {
            "Control_L": "ctrl", "Control_R": "ctrl",
            "Shift_L": "shift", "Shift_R": "shift",
            "Alt_L": "alt", "Alt_R": "alt",
            "Super_L": "windows", "Super_R": "windows",
        }

        SPECIAL_KEYSYMS = {
            "space": "space", "Return": "enter", "Escape": "esc",
            "BackSpace": "backspace", "Tab": "tab", "Delete": "delete",
            "Up": "up", "Down": "down", "Left": "left", "Right": "right",
        }

        pressed_keys = []
        capture_state = {"original": ""}

        def _resolve_key_name(event):
            if event.keysym in MODIFIER_KEYSYMS:
                return MODIFIER_KEYSYMS[event.keysym]
            if event.keysym in SPECIAL_KEYSYMS:
                return SPECIAL_KEYSYMS[event.keysym]
            keycode = event.keycode
            if 0x30 <= keycode <= 0x39:
                return str(keycode - 0x30)
            if 0x41 <= keycode <= 0x5A:
                return chr(keycode).lower()
            if 0x70 <= keycode <= 0x87:
                return f"f{keycode - 0x70 + 1}"
            return event.keysym.lower()

        def on_key_press(event):
            key_name = _resolve_key_name(event)
            if key_name not in pressed_keys:
                pressed_keys.append(key_name)
            display_parts = _sort_hotkey_keys(set(pressed_keys))
            text_variable.set("+".join(display_parts))
            return "break"

        def on_key_release(event):
            pressed_keys.clear()

        def on_focus_in(event):
            capture_state["original"] = text_variable.get()
            pressed_keys.clear()
            text_variable.set("...")

        def on_focus_out(event):
            if text_variable.get() == "...":
                text_variable.set(capture_state["original"])
            pressed_keys.clear()

        entry.bind("<KeyPress>", on_key_press)
        entry.bind("<KeyRelease>", on_key_release)
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        return entry

    def _show_saved_label(self) -> None:
        import customtkinter

        if not self.settings_window:
            return

        saved_label = customtkinter.CTkLabel(
            self.settings_window,
            text=self.i18n_manager.translate("settings.saved"),
            text_color="green",
        )
        saved_label.pack(pady=(0, 5))
        self.settings_window.after(2000, saved_label.destroy)
