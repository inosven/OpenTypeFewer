# VoicePad

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
  - Pull a model: `ollama pull qwen3.5:0.8b` (fast) or `ollama pull qwen3.5` (accurate)
- **Microphone** — System default mic is used
- **NVIDIA GPU** (optional) — Install `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` for GPU-accelerated speech recognition

## Quick Start

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

VoicePad starts in the system tray. The Whisper model downloads automatically on first use.

Use `Ctrl+Shift+Space` (default) to record.

## Usage

| Action | Default Hotkey |
|--------|---------------|
| Start/stop recording | `Ctrl+Shift+Space` |
| Cycle processing mode | `Ctrl+Shift+M` |
| Activate preset | User-defined (e.g. `Ctrl+Shift+1`) |

### Trigger Modes

- **Hold to record** — Hold the hotkey to record, release to stop.
- **Press to toggle** — Press once to start, press again to stop.

### Processing Styles

| Style | Description |
|-------|-------------|
| **Direct** | Raw transcription, no LLM processing |
| **Polish** | Clean up spoken language into fluent written form |
| **Custom** | Apply a user-defined prompt |

### Output Language

| Option | Description |
|--------|-------------|
| **Original** | Keep the spoken language as-is |
| **Chinese** | Translate/output in Chinese |
| **English** | Translate/output in English |

The only combination that skips the LLM entirely is **Direct + Original**. All other combinations call the LLM.

### Presets

Save different output configurations and bind them to hotkeys. Each preset stores:
- Processing style (Direct / Polish / Custom)
- Output language
- Custom prompt

Press a preset hotkey to instantly switch modes. Configure presets in Settings > Presets.

## Configuration

Config file: `~/.voicepad/config.yaml` (auto-generated on first run).

See [config.example.yaml](./config.example.yaml) for all options.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VOICEPAD_API_KEY` | API key for remote LLM (overrides config file) |

## CLI Options

```
python -m voicepad [OPTIONS]

Options:
  --config PATH         Config file path (default: ~/.voicepad/config.yaml)
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

### Windows

```batch
build\build_win.bat
```

Output: `dist\VoicePad\VoicePad.exe`

### macOS

```bash
chmod +x build/build_mac.sh
./build/build_mac.sh
```

Output: `dist/VoicePad-macos.dmg`

## Project Structure

```
src/voicepad/
├── app.py                     # Main controller
├── __main__.py                # CLI entry point
├── config/                    # Configuration management
├── subsystems/
│   ├── asr/                   # Speech recognition (faster-whisper)
│   ├── llm_engine/            # LLM polishing (Ollama / Remote API)
│   └── hotkey_listener/       # Global hotkey handling (keyboard)
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
