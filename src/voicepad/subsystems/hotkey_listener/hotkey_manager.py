"""Global hotkey listener for VoicePad."""

import logging
import platform
import threading

logger = logging.getLogger("voicepad.hotkey")
IS_MACOS = platform.system() == "Darwin"

# Characters produced by modifier+key → the base key character.
# Covers Shift+digit (ASCII) and macOS Option+digit (Unicode).
_UNSHIFT = {
    # Shift+digit
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
    ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
    '~': '`',
    # macOS Option+digit (US keyboard layout)
    '¡': '1', '™': '2', '£': '3', '¢': '4', '∞': '5',
    '§': '6', '¶': '7', '•': '8', 'ª': '9', 'º': '0',
}


def _parse_hotkey_pynput(hotkey_str: str):
    """Convert 'ctrl+shift+space' style string to a frozenset of pynput keys."""
    from pynput.keyboard import Key, KeyCode

    _SPECIAL = {
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "shift": Key.shift,
        "alt": Key.alt, "option": Key.alt,
        "cmd": Key.cmd, "command": Key.cmd, "super": Key.cmd,
        "space": Key.space,
        "enter": Key.enter, "return": Key.enter,
        "tab": Key.tab,
        "esc": Key.esc, "escape": Key.esc,
        "backspace": Key.backspace,
        "delete": Key.delete,
        "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
        **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 21)},
    }

    keys = set()
    for part in hotkey_str.lower().split("+"):
        part = part.strip()
        if part in _SPECIAL:
            keys.add(_SPECIAL[part])
        elif len(part) == 1:
            keys.add(KeyCode.from_char(part))
        else:
            logger.warning(f"Unknown key token in hotkey: {part!r}")
    return frozenset(keys)


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

        # pynput state (macOS only)
        self._pynput_listener = None
        self._pressed_keys = set()
        self._fired_tags = set()  # prevents repeated fire while combo is held

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    #  Platform dispatch                                                    #
    # ------------------------------------------------------------------ #

    def _register_hotkeys(self) -> None:
        if IS_MACOS:
            self._register_pynput()
        else:
            self._register_keyboard()

    def _unregister_hotkeys(self) -> None:
        if IS_MACOS:
            self._unregister_pynput()
        else:
            self._unregister_keyboard()

    # ------------------------------------------------------------------ #
    #  keyboard library backend (Windows / Linux)                          #
    # ------------------------------------------------------------------ #

    def _register_keyboard(self) -> None:
        import keyboard as kb
        self._unregister_keyboard()

        try:
            kb.add_hotkey(self.switch_hotkey, self._handle_switch_mode, suppress=False)
            logger.info(f"Registered switch hotkey: {self.switch_hotkey}")
        except Exception as e:
            logger.error(f"Failed to register switch hotkey: {e}")

        if self.on_activate_preset:
            for idx, preset in enumerate(self.preset_list):
                hk = preset.get("hotkey", "")
                if not hk:
                    continue
                try:
                    kb.add_hotkey(hk, self._handle_preset_activate, args=(idx,), suppress=False)
                    logger.info(f"Registered preset hotkey: {hk}")
                except Exception as e:
                    logger.error(f"Failed to register preset hotkey {hk}: {e}")

        if self.trigger_mode == "hold":
            try:
                kb.add_hotkey(
                    self.record_hotkey, self._handle_hold_press,
                    suppress=False, trigger_on_release=False,
                )
                kb.on_release(self._handle_hold_release_keyboard)
                logger.info(f"Registered hold-mode hotkey: {self.record_hotkey}")
            except Exception as e:
                logger.error(f"Failed to register hold hotkey: {e}")
        else:
            try:
                kb.add_hotkey(self.record_hotkey, self._handle_toggle_press, suppress=False)
                logger.info(f"Registered toggle-mode hotkey: {self.record_hotkey}")
            except Exception as e:
                logger.error(f"Failed to register toggle hotkey: {e}")

    def _unregister_keyboard(self) -> None:
        try:
            import keyboard as kb
            kb.unhook_all()
        except Exception as e:
            logger.warning(f"Error unregistering hotkeys: {e}")

    # ------------------------------------------------------------------ #
    #  pynput backend (macOS)                                              #
    # ------------------------------------------------------------------ #

    def _register_pynput(self) -> None:
        self._unregister_pynput()
        self._pressed_keys.clear()
        self._fired_tags.clear()
        self.record_key_held = False

        self._record_keys = _parse_hotkey_pynput(self.record_hotkey)
        self._switch_keys = _parse_hotkey_pynput(self.switch_hotkey)
        self._preset_keys = []
        for idx, preset in enumerate(self.preset_list):
            hk = preset.get("hotkey", "")
            if hk:
                self._preset_keys.append((_parse_hotkey_pynput(hk), idx))

        from pynput.keyboard import Listener
        self._pynput_listener = Listener(
            on_press=self._pynput_on_press,
            on_release=self._pynput_on_release,
        )
        self._pynput_listener.daemon = True
        self._pynput_listener.start()
        logger.info("pynput listener started")

    def _unregister_pynput(self) -> None:
        if self._pynput_listener:
            try:
                self._pynput_listener.stop()
            except Exception as e:
                logger.warning(f"Error stopping pynput listener: {e}")
            self._pynput_listener = None

    def _canonical(self, key):
        """Normalize left/right modifier variants and shifted chars to base form."""
        try:
            from pynput.keyboard import Key, KeyCode
            _MODIFIER_MAP = {
                Key.ctrl_l: Key.ctrl, Key.ctrl_r: Key.ctrl,
                Key.shift_l: Key.shift, Key.shift_r: Key.shift,
                Key.alt_l: Key.alt, Key.alt_r: Key.alt,
                Key.cmd_l: Key.cmd, Key.cmd_r: Key.cmd,
            }
            if key in _MODIFIER_MAP:
                return _MODIFIER_MAP[key]
            # Normalize shifted characters (e.g. '!' → '1') so that
            # Ctrl+Shift+1 matches a hotkey stored as "ctrl+shift+1"
            ch = getattr(key, 'char', None)
            if ch and ch in _UNSHIFT:
                return KeyCode.from_char(_UNSHIFT[ch])
        except Exception:
            pass
        return key

    def _pynput_on_press(self, key) -> None:
        if not self.running:
            return
        key = self._canonical(key)
        self._pressed_keys.add(key)
        current = self._pressed_keys

        # Switch mode (toggle-fire)
        if self._switch_keys.issubset(current) and "switch" not in self._fired_tags:
            self._fired_tags.add("switch")
            threading.Thread(target=self._handle_switch_mode, daemon=True).start()

        # Preset hotkeys (toggle-fire)
        for preset_keys, idx in self._preset_keys:
            tag = f"preset_{idx}"
            if preset_keys.issubset(current) and tag not in self._fired_tags:
                self._fired_tags.add(tag)
                threading.Thread(
                    target=self._handle_preset_activate, args=(idx,), daemon=True
                ).start()

        # Record hotkey — only fires if no preset hotkey is currently matched.
        # This prevents an accidental short recording when the user presses a
        # preset combo that starts with the same keys as the record hotkey
        # (e.g. record=ctrl+alt, preset=ctrl+alt+1: pressing '1' completes the
        # preset but also leaves ctrl+alt held, which must not start a new recording).
        preset_taking_over = any(
            pk.issubset(current) for pk, _ in self._preset_keys
        )
        if self._record_keys.issubset(current) and not preset_taking_over:
            if self.trigger_mode == "hold":
                if not self.record_key_held:
                    self.record_key_held = True
                    threading.Thread(target=self._handle_hold_press, daemon=True).start()
            else:
                if "record" not in self._fired_tags:
                    self._fired_tags.add("record")
                    threading.Thread(target=self._handle_toggle_press, daemon=True).start()

    def _pynput_on_release(self, key) -> None:
        if not self.running:
            return
        key = self._canonical(key)

        # Stop hold-mode recording when any key in the combo is released
        if self.trigger_mode == "hold" and self.record_key_held and key in self._record_keys:
            self.record_key_held = False
            threading.Thread(target=self._handle_hold_stop, daemon=True).start()

        self._pressed_keys.discard(key)

        # Reset fired-tag when combo is no longer fully held
        if "switch" in self._fired_tags and not self._switch_keys.issubset(self._pressed_keys):
            self._fired_tags.discard("switch")
        if "record" in self._fired_tags and not self._record_keys.issubset(self._pressed_keys):
            self._fired_tags.discard("record")
        for preset_keys, idx in self._preset_keys:
            tag = f"preset_{idx}"
            if tag in self._fired_tags and not preset_keys.issubset(self._pressed_keys):
                self._fired_tags.discard(tag)

    # ------------------------------------------------------------------ #
    #  Shared action handlers                                              #
    # ------------------------------------------------------------------ #

    def _handle_hold_press(self) -> None:
        if not self.running:
            return
        logger.info("Record hotkey pressed (hold mode)")
        try:
            self.on_start_recording()
        except Exception as e:
            logger.error(f"Start recording callback failed: {e}")

    def _handle_hold_stop(self) -> None:
        logger.info("Record hotkey released (hold mode)")
        try:
            self.on_stop_recording()
        except Exception as e:
            logger.error(f"Stop recording callback failed: {e}")

    def _handle_hold_release_keyboard(self, key_event) -> None:
        """keyboard-library specific: check if combo is still pressed."""
        if not self.running or not self.record_key_held:
            return
        import keyboard as kb
        if not kb.is_pressed(self.record_hotkey):
            self.record_key_held = False
            logger.info("Record hotkey released (hold mode)")
            try:
                self.on_stop_recording()
            except Exception as e:
                logger.error(f"Stop recording callback failed: {e}")

    def _handle_toggle_press(self) -> None:
        if not self.running:
            return
        if not self.toggle_recording:
            self.toggle_recording = True
            logger.info("Record hotkey pressed (toggle start)")
            try:
                self.on_start_recording()
            except Exception as e:
                logger.error(f"Start recording callback failed: {e}")
        else:
            self.toggle_recording = False
            logger.info("Record hotkey pressed (toggle stop)")
            try:
                self.on_stop_recording()
            except Exception as e:
                logger.error(f"Stop recording callback failed: {e}")

    def _handle_switch_mode(self) -> None:
        if not self.running:
            return
        logger.info("Switch mode hotkey pressed")
        try:
            self.on_switch_mode()
        except Exception as e:
            logger.error(f"Switch mode callback failed: {e}")

    def _handle_preset_activate(self, preset_index: int) -> None:
        if not self.running or preset_index >= len(self.preset_list):
            return
        preset_entry = self.preset_list[preset_index]
        logger.info(f"Preset hotkey pressed: {preset_entry.get('name', 'unnamed')}")
        try:
            self.on_activate_preset(preset_entry)
        except Exception as e:
            logger.error(f"Preset activation callback failed: {e}")
