"""Global hotkey listener for VoicePad — uses pynput on all platforms."""

import logging
import platform
import threading
import time

logger = logging.getLogger("voicepad.hotkey")

IS_WINDOWS = platform.system() == "Windows"

_UNSHIFT = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
    ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
    '~': '`',
    '¡': '1', '™': '2', '£': '3', '¢': '4', '∞': '5',
    '§': '6', '¶': '7', '•': '8', 'ª': '9', 'º': '0',
}


def _key_to_vk_codes(key):
    from pynput.keyboard import Key, KeyCode

    _VK_MAP = {
        Key.ctrl: [0x11, 0xA2, 0xA3],
        Key.shift: [0x10, 0xA0, 0xA1],
        Key.alt: [0x12, 0xA4, 0xA5],
        Key.cmd: [0x5B, 0x5C],
        Key.space: [0x20],
        Key.enter: [0x0D],
        Key.tab: [0x09],
        Key.esc: [0x1B],
        Key.backspace: [0x08],
        Key.delete: [0x2E],
    }
    if key in _VK_MAP:
        return _VK_MAP[key]
    ch = getattr(key, 'char', None)
    if ch and ch.isalpha():
        return [ord(ch.upper())]
    if ch and ch.isdigit():
        return [ord(ch)]
    vk = getattr(key, 'vk', None)
    if vk is not None:
        return [vk]
    return []


def _parse_hotkey_combo(hotkey_str: str):
    from pynput.keyboard import Key, KeyCode

    _SPECIAL = {
        "ctrl": Key.ctrl, "control": Key.ctrl,
        "shift": Key.shift,
        "alt": Key.alt, "option": Key.alt,
        "cmd": Key.cmd, "command": Key.cmd, "super": Key.cmd,
        "win": Key.cmd, "windows": Key.cmd,
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
        self.switch_hotkey = config_manager.get_value("mode_switch_hotkey", "")
        self.preset_list = config_manager.get_value("presets", [])

        self.record_key_held = False
        self.toggle_recording = False
        self.running = False

        self._listener = None
        self._pressed_keys = set()
        self._fired_tags = set()

    def start_listening(self) -> None:
        if self.running:
            return
        self.running = True
        self._start_listener()
        logger.info(
            f"Hotkey listener started (record={self.record_hotkey}, "
            f"switch={self.switch_hotkey}, mode={self.trigger_mode})"
        )

    def stop_listening(self) -> None:
        self.running = False
        self._stop_listener()
        logger.info("Hotkey listener stopped")

    def update_hotkeys(self, config_manager) -> None:
        self._stop_listener()
        self.trigger_mode = config_manager.get_value("trigger_mode", "hold")
        self.record_hotkey = config_manager.get_value("hotkey", "ctrl+shift+space")
        self.switch_hotkey = config_manager.get_value("mode_switch_hotkey", "")
        self.preset_list = config_manager.get_value("presets", [])
        if self.running:
            self._start_listener()
        logger.info(
            f"Hotkeys updated: record={self.record_hotkey}, "
            f"switch={self.switch_hotkey}, mode={self.trigger_mode}, "
            f"presets={len(self.preset_list)}"
        )

    def _start_listener(self) -> None:
        self._stop_listener()
        self._pressed_keys.clear()
        self._fired_tags.clear()
        self.record_key_held = False

        self._record_keys = _parse_hotkey_combo(self.record_hotkey)
        self._switch_keys = _parse_hotkey_combo(self.switch_hotkey) if self.switch_hotkey else frozenset()
        self._preset_keys = []
        for idx, preset in enumerate(self.preset_list):
            hk = preset.get("hotkey", "")
            if hk:
                self._preset_keys.append((_parse_hotkey_combo(hk), idx))

        from pynput.keyboard import Listener
        self._listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info("pynput listener started")

    def _stop_listener(self) -> None:
        if self._listener:
            try:
                self._listener.stop()
            except Exception as stop_error:
                logger.warning(f"Error stopping listener: {stop_error}")
            self._listener = None

    def _canonical(self, key):
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
            ch = getattr(key, 'char', None)
            if ch:
                if ch in _UNSHIFT:
                    return KeyCode.from_char(_UNSHIFT[ch])
                if ch.isalpha():
                    return KeyCode.from_char(ch.lower())
                if ch == ' ':
                    return Key.space
            vk = getattr(key, 'vk', None)
            if vk is not None and not ch:
                if 65 <= vk <= 90:
                    return KeyCode.from_char(chr(vk).lower())
                if 48 <= vk <= 57:
                    return KeyCode.from_char(chr(vk))
                _VK_TO_SPECIAL = {
                    0x20: Key.space, 0x0D: Key.enter, 0x09: Key.tab,
                    0x1B: Key.esc, 0x08: Key.backspace, 0x2E: Key.delete,
                }
                if vk in _VK_TO_SPECIAL:
                    return _VK_TO_SPECIAL[vk]
        except Exception:
            pass
        return key

    def _on_press(self, key) -> None:
        if not self.running:
            return
        key = self._canonical(key)
        self._pressed_keys.add(key)
        current = self._pressed_keys

        if self._switch_keys and self._switch_keys.issubset(current) and "switch" not in self._fired_tags:
            self._fired_tags.add("switch")
            threading.Thread(target=self._handle_switch_mode, daemon=True).start()

        for preset_keys, idx in self._preset_keys:
            tag = f"preset_{idx}"
            if preset_keys.issubset(current) and tag not in self._fired_tags:
                self._fired_tags.add(tag)
                threading.Thread(
                    target=self._handle_preset_activate, args=(idx,), daemon=True
                ).start()

        preset_taking_over = any(
            pk.issubset(current) for pk, _ in self._preset_keys
        )
        if self._record_keys.issubset(current) and not preset_taking_over:
            if self.trigger_mode == "hold":
                if not self.record_key_held:
                    self.record_key_held = True
                    threading.Thread(target=self._handle_hold_press, daemon=True).start()
                    if IS_WINDOWS:
                        threading.Thread(target=self._poll_hold_release, daemon=True).start()
            else:
                if "record" not in self._fired_tags:
                    self._fired_tags.add("record")
                    threading.Thread(target=self._handle_toggle_press, daemon=True).start()

    def _on_release(self, key) -> None:
        if not self.running:
            return
        key = self._canonical(key)

        if self.trigger_mode == "hold" and self.record_key_held and key in self._record_keys:
            self.record_key_held = False
            threading.Thread(target=self._handle_hold_stop, daemon=True).start()

        self._pressed_keys.discard(key)

        if "switch" in self._fired_tags and not self._switch_keys.issubset(self._pressed_keys):
            self._fired_tags.discard("switch")
        if "record" in self._fired_tags and not self._record_keys.issubset(self._pressed_keys):
            self._fired_tags.discard("record")
        for preset_keys, idx in self._preset_keys:
            tag = f"preset_{idx}"
            if tag in self._fired_tags and not preset_keys.issubset(self._pressed_keys):
                self._fired_tags.discard(tag)

    def _handle_hold_press(self) -> None:
        if not self.running:
            return
        logger.info("Record hotkey pressed (hold mode)")
        try:
            self.on_start_recording()
        except Exception as e:
            logger.error(f"Start recording callback failed: {e}")

    def _poll_hold_release(self) -> None:
        import ctypes
        get_async_key_state = ctypes.windll.user32.GetAsyncKeyState

        vk_groups = []
        for record_key in self._record_keys:
            vk_codes = _key_to_vk_codes(record_key)
            if vk_codes:
                vk_groups.append(vk_codes)

        if not vk_groups:
            return

        while self.record_key_held and self.running:
            time.sleep(0.05)
            for vk_codes in vk_groups:
                key_still_held = any(get_async_key_state(vk) & 0x8000 for vk in vk_codes)
                if not key_still_held:
                    if self.record_key_held:
                        self.record_key_held = False
                        logger.info("Hold release detected via polling")
                        self._handle_hold_stop()
                    return

    def _handle_hold_stop(self) -> None:
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
