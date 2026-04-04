# OpenTypeFewer

Local, open-source voice-to-clipboard tool. Speak, and paste.

[中文文档](./README_ZH.md)

## Features

- **Voice to clipboard + auto-paste** — Press a hotkey, speak, release. Result is copied to clipboard and pasted at cursor position automatically.
- **Offline speech recognition** — Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2-based Whisper). No internet required. NVIDIA GPU accelerated when available.
- **Chinese, English, and mixed language** — Auto-detects spoken language or force a specific one.
- **Two-dimensional output mode** — Independently control _processing style_ (Direct / Polish / Custom) and _output language_ (Original / Chinese / English / custom).
- **Presets** — Save multiple output configurations (processing + language + custom prompt) with dedicated hotkeys. Switch instantly between presets like "Business Email", "Chinese Polish", etc.
- **LLM polishing** — Optionally clean up transcriptions with a local LLM via [Ollama](https://ollama.com/) or a remote API (Anthropic / OpenAI / OpenAI-compatible). Supports extended thinking for supported models.
- **Mini floating panel** — A compact always-on-top status panel showing recording state, current mode, and volume bars. Hide to tray and restore with a double-click on the tray icon.
- **System tray app** — Lives in your tray. Double-click to show panel (Windows).
- **Settings GUI** — Full-featured settings window. Configure ASR model/device, microphone, LLM providers, hotkeys, presets, and appearance.
- **Dark / Light / System theme** — Follows your OS theme or set it manually.
- **Cross-platform** — macOS and Windows.

## Prerequisites

- **Python 3.10+** (for running from source)
- **Ollama** (optional, for local LLM polishing) — [Install Ollama](https://ollama.com/download)
  - Pull a model: `ollama pull qwen3.5:0.8b` (fast) or `ollama pull qwen3.5:8b` (accurate)
- **Microphone** — Configurable in Settings (default: system default mic)
- **NVIDIA GPU** (optional, Windows) — Install `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` for GPU-accelerated speech recognition. Auto-detected at startup.

## Quick Start

### Download

[Latest Release](https://github.com/inosven/OpenTypeFewer/releases/latest) — Windows (CUDA / CPU) and macOS builds available.

### Install from Source

```bash
git clone https://github.com/inosven/OpenTypeFewer.git
cd OpenTypeFewer
pip install -e .
```

### Run

```bash
opentypefewer
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

| Action                | Default Hotkey                   |
| --------------------- | -------------------------------- |
| Start/stop recording  | `Ctrl+Shift+Space`               |
| Cycle processing mode | `Ctrl+Shift+M`                   |
| Activate preset       | User-defined (e.g. `Ctrl+Alt+1`) |

### Trigger Modes

- **Hold to record** — Hold the hotkey to record, release to stop.
- **Press to toggle** — Press once to start, press again to stop.

### Processing Styles

| Style      | Description                                       |
| ---------- | ------------------------------------------------- |
| **Direct** | Raw transcription, no LLM processing              |
| **Polish** | Clean up spoken language into fluent written form |
| **Custom** | User-defined prompt as a style modifier           |

### Output Language

| Option       | Description                    |
| ------------ | ------------------------------ |
| **Original** | Keep the spoken language as-is |
| **Chinese**  | Translate/output in Chinese    |
| **English**  | Translate/output in English    |

**Direct** mode always skips the LLM entirely, regardless of output language. **Polish** and **Custom** modes call the LLM.

In **Custom** mode, the custom prompt acts as a _style modifier_ combined with the output language. For example, setting language to English and custom prompt to "keep it casual" will translate to informal English — the language instruction and the style hint both apply.

### Mini Panel

The mini panel opens automatically on startup (Windows) or via **Show Panel** in the tray menu. Double-click the tray icon to restore it (Windows). It shows:

- Settings and minimize-to-tray buttons at the top
- Current state (Ready / Recording / Processing) with animated orb
- Active preset name, mode, and hotkey
- Live volume bars during recording

### LLM Providers

| Provider       | Description                                                         |
| -------------- | ------------------------------------------------------------------- |
| **Ollama**     | Local inference. Model dropdown auto-populated from running Ollama. |
| **Anthropic**  | Claude API.                                                         |
| **OpenAI**     | OpenAI API.                                                         |
| **Compatible** | Any OpenAI-compatible endpoint (LM Studio, vLLM, Groq, etc.).       |

**Enable Thinking** toggle is available for each provider. Maps to extended reasoning where supported (Qwen3 thinking, Claude extended thinking, OpenAI `reasoning_effort=high`).

### Presets

Save different output configurations and bind them to hotkeys. Each preset stores:

- Processing style (Direct / Polish / Custom)
- Output language
- Custom prompt

Press a preset hotkey to instantly switch modes. Configure presets in Settings > Presets.

> **Tip:** Preset hotkeys must not be a prefix of your record hotkey (or vice versa). For example, if your record hotkey is `Ctrl+Shift`, don't use `Ctrl+Shift+1` as a preset — use `Ctrl+Alt+1` instead.

## Configuration

Config file: `~/.opentypefewer/config.yaml` (auto-generated on first run).

See [config.example.yaml](./config.example.yaml) for all options.

### Environment Variables

| Variable           | Description                                    |
| ------------------ | ---------------------------------------------- |
| `VOICEPAD_API_KEY` | API key for remote LLM (overrides config file) |

## CLI Options

```
opentypefewer [OPTIONS]

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

Output: `dist\OpenTypeFewer\OpenTypeFewer.exe` (CUDA and CPU versions)

## Project Structure

```
src/voicepad/
├── app.py                     # Main controller
├── __main__.py                # CLI entry point
├── asr_subprocess.py          # ASR child process (isolated model loading)
├── panel_subprocess.py        # Mini panel child process (pywebview)
├── settings_subprocess.py     # Settings window child process (pywebview)
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
    └── main_window/           # PyWebView UI — mini panel + settings window
        └── frontend/          # HTML / CSS / JS
```

## License

[MIT](./LICENSE)
