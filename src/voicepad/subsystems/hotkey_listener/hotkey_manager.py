"""Global hotkey listener for VoicePad using keyboard library."""

import logging

import keyboard

logger = logging.getLogger("voicepad.hotkey")


class HotkeyManager:
    def __init__(
        self,
        config_manager,
        on_start_recording,
        on_stop_recording,
        on_switch_mode,
        on_activate_preset=None,
    ):
        self.config_manager = config_manager
        self.on_start_recording = on_start_recording
        self.on_stop_recording = on_stop_recording
        self.on_switch_mode = on_switch_mode
        self.on_activate_preset = on_activate_preset

        self.trigger_mode = config_manager.get_value("trigger_mode", "hold")
        self.record_hotkey = config_manager.get_value("hotkey", "ctrl+shift+space")
        self.switch_hotkey = config_manager.get_value("mode_switch_hotkey", "ctrl+shift+m")
        self.preset_list = config_manager.get_value("presets", [])

        self.record_key_held = False
        self.toggle_recording = False
        self.running = False

    def start_listening(self) -> None:
        if self.running:
            return

        self.running = True
        self._register_hotkeys()
        logger.info(
            f"Hotkey listener started (record={self.record_hotkey}, "
            f"switch={self.switch_hotkey}, mode={self.trigger_mode})"
        )

    def stop_listening(self) -> None:
        self.running = False
        self._unregister_hotkeys()
        logger.info("Hotkey listener stopped")

    def update_hotkeys(self, config_manager) -> None:
        self._unregister_hotkeys()
        self.trigger_mode = config_manager.get_value("trigger_mode", "hold")
        self.record_hotkey = config_manager.get_value("hotkey", "ctrl+shift+space")
        self.switch_hotkey = config_manager.get_value("mode_switch_hotkey", "ctrl+shift+m")
        self.preset_list = config_manager.get_value("presets", [])
        if self.running:
            self._register_hotkeys()
        logger.info("Hotkeys updated")

    def _register_hotkeys(self) -> None:
        self._unregister_hotkeys()

        try:
            keyboard.add_hotkey(
                self.switch_hotkey,
                self._handle_switch_mode,
                suppress=False,
            )
            logger.info(f"Registered switch hotkey: {self.switch_hotkey}")
        except Exception as register_error:
            logger.error(f"Failed to register switch hotkey: {register_error}")

        self._register_preset_hotkeys()

        if self.trigger_mode == "hold":
            self._register_hold_mode()
        else:
            self._register_toggle_mode()

    def _register_hold_mode(self) -> None:
        try:
            keyboard.add_hotkey(
                self.record_hotkey,
                self._handle_hold_press,
                suppress=False,
                trigger_on_release=False,
            )
            logger.info(f"Registered hold-mode hotkey: {self.record_hotkey}")

            keyboard.on_release(self._handle_hold_release)
            logger.info("Registered release handler for hold mode")
        except Exception as register_error:
            logger.error(f"Failed to register hold hotkey: {register_error}")

    def _register_toggle_mode(self) -> None:
        try:
            keyboard.add_hotkey(
                self.record_hotkey,
                self._handle_toggle_press,
                suppress=False,
            )
            logger.info(f"Registered toggle-mode hotkey: {self.record_hotkey}")
        except Exception as register_error:
            logger.error(f"Failed to register toggle hotkey: {register_error}")

    def _register_preset_hotkeys(self) -> None:
        if not self.on_activate_preset:
            return

        for preset_index, preset_entry in enumerate(self.preset_list):
            preset_hotkey = preset_entry.get("hotkey", "")
            if not preset_hotkey:
                continue
            try:
                keyboard.add_hotkey(
                    preset_hotkey,
                    self._handle_preset_activate,
                    args=(preset_index,),
                    suppress=False,
                )
                logger.info(
                    f"Registered preset hotkey: {preset_hotkey} "
                    f"-> {preset_entry.get('name', f'Preset {preset_index + 1}')}"
                )
            except Exception as register_error:
                logger.error(
                    f"Failed to register preset hotkey {preset_hotkey}: {register_error}"
                )

    def _handle_preset_activate(self, preset_index: int) -> None:
        if not self.running:
            return

        if preset_index >= len(self.preset_list):
            return

        preset_entry = self.preset_list[preset_index]
        logger.info(f"Preset hotkey pressed: {preset_entry.get('name', 'unnamed')}")
        try:
            self.on_activate_preset(preset_entry)
        except Exception as callback_error:
            logger.error(f"Preset activation callback failed: {callback_error}")

    def _unregister_hotkeys(self) -> None:
        try:
            keyboard.unhook_all()
        except Exception as unregister_error:
            logger.warning(f"Error unregistering hotkeys: {unregister_error}")

    def _handle_hold_press(self) -> None:
        if not self.running:
            return
        if self.record_key_held:
            return

        self.record_key_held = True
        logger.info("Record hotkey pressed (hold mode)")
        try:
            self.on_start_recording()
        except Exception as callback_error:
            logger.error(f"Start recording callback failed: {callback_error}")

    def _handle_hold_release(self, key_event) -> None:
        if not self.running:
            return
        if not self.record_key_held:
            return

        if not keyboard.is_pressed(self.record_hotkey):
            self.record_key_held = False
            logger.info("Record hotkey released (hold mode)")
            try:
                self.on_stop_recording()
            except Exception as callback_error:
                logger.error(f"Stop recording callback failed: {callback_error}")

    def _handle_toggle_press(self) -> None:
        if not self.running:
            return

        if not self.toggle_recording:
            self.toggle_recording = True
            logger.info("Record hotkey pressed (toggle start)")
            try:
                self.on_start_recording()
            except Exception as callback_error:
                logger.error(f"Start recording callback failed: {callback_error}")
        else:
            self.toggle_recording = False
            logger.info("Record hotkey pressed (toggle stop)")
            try:
                self.on_stop_recording()
            except Exception as callback_error:
                logger.error(f"Stop recording callback failed: {callback_error}")

    def _handle_switch_mode(self) -> None:
        if not self.running:
            return

        logger.info("Switch mode hotkey pressed")
        try:
            self.on_switch_mode()
        except Exception as callback_error:
            logger.error(f"Switch mode callback failed: {callback_error}")
