# OpenTypeFewer

本地开源语音输入剪贴板工具。说完就贴。

[English](./README.md)

## 功能特点

- **语音转剪贴板 + 自动粘贴** — 按快捷键，说话，松开。结果自动复制到剪贴板并粘贴到光标位置。
- **离线语音识别** — 基于 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2 版 Whisper），无需联网。支持 NVIDIA GPU 加速。
- **中英文及混合语言** — 自动检测语种，也可强制指定。
- **二维输出模式** — 独立控制 _处理方式_（直出 / 润色 / 自定义）和 _输出语言_（原文 / 中文 / 英文 / 自定义）。
- **预设** — 保存多组输出配置（处理方式 + 输出语言 + 自定义 Prompt），绑定专属快捷键。一键切换「商务邮件」「中文润色」等不同模式。
- **LLM 润色** — 可选使用本地 LLM（[Ollama](https://ollama.com/)）或远程 API（Anthropic / OpenAI / OpenAI 兼容接口）润色转写结果。支持扩展思考（Extended Thinking）。
- **迷你悬浮面板** — 小巧的置顶状态面板，实时显示录音状态、当前模式和音量波形。可隐藏到托盘，双击托盘图标恢复（Windows）。
- **系统托盘应用** — 常驻托盘，双击图标显示面板（Windows）。
- **设置界面** — 完整的设置窗口，可配置 ASR 模型/设备、麦克风、LLM 提供商、快捷键、预设和外观。
- **深色 / 浅色 / 跟随系统主题** — 自动跟随系统，或手动设置。
- **跨平台** — 支持 macOS 和 Windows。

## 前置要求

- **Python 3.10+**（从源码运行时需要）
- **Ollama**（可选，本地 LLM 润色）— [下载 Ollama](https://ollama.com/download)
  - 拉取模型：`ollama pull qwen3.5:0.8b`（快速）或 `ollama pull qwen3.5:8b`（精确）
- **麦克风** — 可在设置中选择（默认：系统默认麦克风）
- **NVIDIA GPU**（可选，Windows）— 安装 `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` 以启用 GPU 加速语音识别，启动时自动检测

## 快速开始

### 下载安装

[最新版本下载](https://github.com/inosven/OpenTypeFewer/releases/latest) — 提供 Windows（CUDA / CPU）和 macOS 版本。

### 从源码安装

```bash
git clone https://github.com/inosven/OpenTypeFewer.git
cd OpenTypeFewer
pip install -e .
```

### 运行

```bash
python -m voicepad
```

OpenTypeFewer 启动后常驻系统托盘。Whisper 模型会在首次使用时自动下载。

默认快捷键：`Ctrl+Shift+Space`

### macOS — 首次启动权限

macOS 首次启动时需要授予两个权限：

1. **辅助功能（Accessibility）** — 全局快捷键必需
   `系统设置 > 隐私与安全性 > 辅助功能` → 添加 OpenTypeFewer

2. **麦克风** — 录音必需
   `系统设置 > 隐私与安全性 > 麦克风` → 允许 OpenTypeFewer

## 使用方法

| 操作          | 默认快捷键                    |
| ------------- | ----------------------------- |
| 开始/停止录音 | `Ctrl+Shift+Space`            |
| 切换处理方式  | `Ctrl+Shift+M`                |
| 激活预设      | 用户自定义（如 `Ctrl+Alt+1`） |

### 触发模式

- **长按录音** — 按住快捷键录音，松开停止。
- **按键切换** — 按一次开始，再按一次停止。

### 处理方式

| 方式       | 说明                           |
| ---------- | ------------------------------ |
| **直出**   | 原始转写结果，不经过 LLM       |
| **润色**   | 将口语转为流畅的书面语         |
| **自定义** | 使用自定义 Prompt 作为风格修饰 |

### 输出语言

| 选项         | 说明             |
| ------------ | ---------------- |
| **原文语言** | 保持说话时的语言 |
| **中文**     | 翻译/输出为中文  |
| **英文**     | 翻译/输出为英文  |

**直出**模式始终跳过 LLM，无论输出语言如何设置。**润色**和**自定义**模式会调用 LLM。

**自定义**模式下，自定义 Prompt 作为*风格修饰语*与输出语言叠加生效。例如将语言设为英文、Prompt 设为"语气轻松随意"，则会以口语化英文输出——语言指令和风格提示同时有效。

### 迷你悬浮面板

启动后自动打开（Windows），也可在托盘菜单中点击 **Show Panel** 打开，或双击托盘图标恢复（Windows）。显示：

- 顶部设置和最小化到托盘按钮
- 当前状态（就绪 / 录音中 / 处理中）及动画指示球
- 当前预设名称、模式和快捷键
- 录音时的实时音量波形

### LLM 提供商

| 提供商                 | 说明                                               |
| ---------------------- | -------------------------------------------------- |
| **Ollama**             | 本地推理，模型列表从运行中的 Ollama 自动获取。     |
| **Anthropic**          | Claude API。                                       |
| **OpenAI**             | OpenAI API。                                       |
| **Compatible（兼容）** | 任意 OpenAI 兼容接口（LM Studio、vLLM、Groq 等）。 |

每个提供商均提供 **启用思考（Enable Thinking）** 开关，对应各自的扩展推理能力（Qwen3 思考模式、Claude Extended Thinking、OpenAI `reasoning_effort=high`）。

### 预设

保存不同的输出配置并绑定快捷键。每个预设包含：

- 处理方式（直出 / 润色 / 自定义）
- 输出语言
- 自定义 Prompt

按下预设快捷键即可一键切换模式。在 设置 > 预设 中配置。

> **提示：** 预设快捷键不能是录音快捷键的前缀（反之亦然）。例如录音快捷键为 `Ctrl+Shift`，则不要用 `Ctrl+Shift+1` 作为预设——改用 `Ctrl+Alt+1`。

## 配置

配置文件：`~/.opentypefewer/config.yaml`（首次运行自动生成）。

完整选项参见 [config.example.yaml](./config.example.yaml)。

### 环境变量

| 变量               | 说明                                   |
| ------------------ | -------------------------------------- |
| `VOICEPAD_API_KEY` | 远程 LLM 的 API 密钥（优先于配置文件） |

## 命令行选项

```
python -m voicepad [选项]

选项:
  --config PATH         配置文件路径（默认：~/.opentypefewer/config.yaml）
  --processing MODE     设置处理方式（direct/polish/custom）
  --language LANG       设置输出语言（source/zh/en）
  --ui-language LANG    设置界面语言（en/zh）
  --list-devices        列出音频输入设备
  --test-mic            测试麦克风（录音 3 秒）
  --test-asr            测试语音识别（录音 5 秒）
  --test-llm            测试 LLM 连接
  --download-model SIZE 下载 faster-whisper 模型
  --version             显示版本
  --verbose             详细日志
```

## 构建

### macOS

```bash
chmod +x build/build_mac.sh
./build/build_mac.sh
```

输出：`dist/OpenTypeFewer.app` 和 `dist/OpenTypeFewer-macos.dmg`

安装 DMG 后，首次启动需授予辅助功能和麦克风权限（见上文）。

### Windows

```batch
build\build_win.bat
```

输出：`dist\OpenTypeFewer\OpenTypeFewer.exe`（CUDA 和 CPU 两个版本）

## 项目结构

```
src/voicepad/
├── app.py                     # 主控制器
├── __main__.py                # CLI 入口
├── asr_subprocess.py          # ASR 子进程（隔离模型加载）
├── panel_subprocess.py        # 迷你面板子进程（pywebview）
├── settings_subprocess.py     # 设置窗口子进程（pywebview）
├── config/                    # 配置管理
├── subsystems/
│   ├── asr/                   # 语音识别（faster-whisper）
│   ├── llm_engine/            # LLM 润色（Ollama / 远程 API）
│   └── hotkey_listener/       # 全局快捷键（macOS 用 pynput，Windows 用 keyboard）
└── modules/
    ├── recorder/              # 音频录制（sounddevice）
    ├── clipboard/             # 剪贴板操作（pyperclip）
    ├── notify/                # 通知和提示音
    ├── i18n/                  # 国际化（中/英）
    ├── tray/                  # 系统托盘（pystray）
    └── main_window/           # PyWebView UI — 迷你面板 + 设置窗口
        └── frontend/          # HTML / CSS / JS
```

## 许可证

[MIT](./LICENSE)
