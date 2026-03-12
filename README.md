# OpenTypeFewer

Local, open-source voice-to-clipboard tool. Speak, and paste.

[中文文档](./README_ZH.md)

## Features

- **Voice to clipboard + auto-paste** — Press a hotkey, speak, release. Result is copied to clipboard and pasted at cursor position automatically.
- **Offline speech recognition** — Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2-based Whisper). No internet required. NVIDIA GPU accelerated when available.
- **Chinese, English, and mixed language** — Auto-detects spoken language or force a specific one.
- **Two-dimensional output mode** — Independently control *processing style* (Direct / Polish / Custom) and *output language* (Original / Chinese / English / custom).
- **Presets** — Save multiple output configurations (processing + language + custom prompt) with dedicated hotkeys. Switch instantly between presets like "Business Email", "Chinese Polish", etc.
- **LLM polishing** — Optionally clean up transcriptions with a local LLM via [Ollama](https://ollama.com/) or a remote API (Anthropic / OpenAI).
- **System tray app** — Lives in your tray. Never steals focus.
- **Settings GUI** — Configure everything from a tabbed settings window. Hotkey fields auto-detect key presses.
- **Cross-platform** — macOS and Windows.

## Prerequisites

- **Python 3.10+** (for running from source)
- **Ollama** (optional, for local LLM polishing) — [Install Ollama](https://ollama.com/download)
  - Pull a model: `ollama pull qwen3:1.7b` (fast) or `ollama pull qwen3:8b` (accurate)
- **Microphone** — System default mic is used
- **NVIDIA GPU** (optional, Windows/Linux) — Install `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` for GPU-accelerated speech recognition

## Quick Start

### Download realease, install and ready to go
[Windows](https://github.com/inosven/OpenTypeFewer/releases/tag/v0.1.0)
[MacOS](https://github.com/inosven/OpenTypeFewer/releases/tag/MacOS)

### Install from Source

```bash
git clone https://github.com/inosven/OpenTypeFewer.git
cd OpenTypeFewer
pip install -e .
```

### Run

```bash
python -m voicepad
```

OpenTypeFewer starts in the system tray. The Whisper model downloads automatically on first use.

Default hotkey: `Ctrl+Shift+Space`

### macOS — First Launch Permissions

macOS requires two permissions on first launch:

1. **Accessibility** — required for global hotkeys
   `System Settings > Privacy & Security > Accessibility` → add OpenTypeFewer

2. **Microphone** — required for audio recording
   `System Settings > Privacy & Security > Microphone` → allow OpenTypeFewer

## Usage

| Action | Default Hotkey |
|--------|---------------|
| Start/stop recording | `Ctrl+Shift+Space` |
| Cycle processing mode | `Ctrl+Shift+M` |
| Activate preset | User-defined (e.g. `Ctrl+Alt+1`) |

### Trigger Modes

- **Hold to record** — Hold the hotkey to record, release to stop.
- **Press to toggle** — Press once to start, press again to stop.

### Processing Styles

| Style | Description |
|-------|-------------|
| **Direct** | Raw transcription, no LLM processing |
| **Polish** | Clean up spoken language into fluent written form |
| **Custom** | User-defined prompt as a style modifier |

### Output Language

| Option | Description |
|--------|-------------|
| **Original** | Keep the spoken language as-is |
| **Chinese** | Translate/output in Chinese |
| **English** | Translate/output in English |

The only combination that skips the LLM entirely is **Direct + Original**. All other combinations call the LLM.

In **Custom** mode, the custom prompt acts as a *style modifier* combined with the output language. For example, setting language to English and custom prompt to "keep it casual" will translate to informal English — the language instruction and the style hint both apply.

### Presets

Save different output configurations and bind them to hotkeys. Each preset stores:
- Processing style (Direct / Polish / Custom)
- Output language
- Custom prompt

Press a preset hotkey to instantly switch modes. The tray icon tooltip briefly shows the active preset name as confirmation. Configure presets in Settings > Presets.

> **Tip:** Preset hotkeys must not be a prefix of your record hotkey (or vice versa). For example, if your record hotkey is `Ctrl+Shift`, don't use `Ctrl+Shift+1` as a preset — use `Ctrl+Alt+1` instead.

## Configuration

Config file: `~/.opentypefewer/config.yaml` (auto-generated on first run).

See [config.example.yaml](./config.example.yaml) for all options.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VOICEPAD_API_KEY` | API key for remote LLM (overrides config file) |

## CLI Options

```
python -m voicepad [OPTIONS]

Options:
  --config PATH         Config file path (default: ~/.opentypefewer/config.yaml)
  --processing MODE     Set processing style (direct/polish/custom)
  --language LANG       Set output language (source/zh/en)
  --ui-language LANG    Set interface language (en/zh)
  --list-devices        List audio input devices
  --test-mic            Test microphone (3 second recording)
  --test-asr            Test ASR (5 second recording)
  --test-llm            Test LLM connection
  --download-model SIZE Download faster-whisper model
  --version             Show version
  --verbose             Verbose logging
```

## Building

### macOS

```bash
chmod +x build/build_mac.sh
./build/build_mac.sh
```

Output: `dist/OpenTypeFewer.app` and `dist/OpenTypeFewer-macos.dmg`

After installing the DMG, grant Accessibility and Microphone permissions on first launch (see above).

### Windows

```batch
build\build_win.bat
```

Output: `dist\VoicePad\VoicePad.exe`

## Project Structure

```
src/voicepad/
├── app.py                     # Main controller
├── __main__.py                # CLI entry point
├── config/                    # Configuration management
├── subsystems/
│   ├── asr/                   # Speech recognition (faster-whisper)
│   ├── llm_engine/            # LLM polishing (Ollama / Remote API)
│   └── hotkey_listener/       # Global hotkeys (pynput on macOS, keyboard on Windows)
└── modules/
    ├── recorder/              # Audio recording (sounddevice)
    ├── clipboard/             # Clipboard operations (pyperclip)
    ├── notify/                # Notifications and sounds
    ├── i18n/                  # Internationalization (en/zh)
    ├── tray/                  # System tray (pystray)
    └── settings_window/       # Settings GUI (customtkinter)
```

## Development

### Run Tests

```bash
# All tests
python -m pytest tests/ -v

# Skip hardware-dependent tests
python -m pytest tests/ -v -m "not hardware"

# Single test by ID
python -m pytest tests/*/U001/ -v
```

## License

[MIT](./LICENSE)
