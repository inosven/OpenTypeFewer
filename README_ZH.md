# VoicePad

本地开源语音输入剪贴板工具。说完就贴。

[English](./README.md)

## 功能特点

- **语音转剪贴板 + 自动粘贴** — 按快捷键，说话，松开。结果自动复制到剪贴板并粘贴到光标位置。
- **离线语音识别** — 基于 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2 版 Whisper），无需联网。支持 NVIDIA GPU 加速。
- **中英文及混合语言** — 自动检测语种，也可强制指定。
- **二维输出模式** — 独立控制 *处理方式*（直出 / 润色 / 自定义）和 *输出语言*（原文 / 中文 / 英文 / 自定义）。
- **预设** — 保存多组输出配置（处理方式 + 输出语言 + 自定义 Prompt），绑定专属快捷键。一键切换「商务邮件」「中文润色」等不同模式。
- **LLM 润色** — 可选使用本地 LLM（[Ollama](https://ollama.com/)）或远程 API（Anthropic / OpenAI）润色转写结果。
- **系统托盘应用** — 常驻托盘，不抢焦点。
- **设置界面** — 可视化配置所有选项。快捷键输入框支持按键检测。
- **跨平台** — 支持 macOS 和 Windows。

## 前置要求

- **Python 3.10+**（从源码运行时需要）
- **Ollama**（可选，本地 LLM 润色）— [下载 Ollama](https://ollama.com/download)
  - 拉取模型：`ollama pull qwen3.5:0.8b`（快速）或 `ollama pull qwen3.5`（精确）
- **麦克风** — 使用系统默认麦克风
- **NVIDIA GPU**（可选）— 安装 `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` 以启用 GPU 加速语音识别

## 快速开始

### 从源码安装

```bash
git clone https://github.com/nicekid1/VoicePad.git
cd VoicePad
pip install -e .
```

### 运行

```bash
python -m voicepad
```

VoicePad 启动后常驻系统托盘。Whisper 模型会在首次使用时自动下载。

默认使用 `Ctrl+Shift+Space` 录音。

## 使用方法

| 操作 | 默认快捷键 |
|------|-----------|
| 开始/停止录音 | `Ctrl+Shift+Space` |
| 切换处理方式 | `Ctrl+Shift+M` |
| 激活预设 | 用户自定义（如 `Ctrl+Shift+1`） |

### 触发模式

- **长按录音** — 按住快捷键录音，松开停止。
- **按键切换** — 按一次开始，再按一次停止。

### 处理方式

| 方式 | 说明 |
|------|------|
| **直出** | 原始转写结果，不经过 LLM |
| **润色** | 将口语转为流畅的书面语 |
| **自定义** | 使用自定义 Prompt 处理 |

### 输出语言

| 选项 | 说明 |
|------|------|
| **原文语言** | 保持说话时的语言 |
| **中文** | 翻译/输出为中文 |
| **英文** | 翻译/输出为英文 |

唯一不调用 LLM 的组合是 **直出 + 原文语言**，其他所有组合都会调用 LLM。

### 预设

保存不同的输出配置并绑定快捷键。每个预设包含：
- 处理方式（直出 / 润色 / 自定义）
- 输出语言
- 自定义 Prompt

按下预设快捷键即可一键切换模式。在 设置 > 预设 中配置。

## 配置

配置文件：`~/.voicepad/config.yaml`（首次运行自动生成）。

完整选项参见 [config.example.yaml](./config.example.yaml)。

### 环境变量

| 变量 | 说明 |
|------|------|
| `VOICEPAD_API_KEY` | 远程 LLM 的 API 密钥（优先于配置文件） |

## 命令行选项

```
python -m voicepad [选项]

选项:
  --config PATH         配置文件路径（默认：~/.voicepad/config.yaml）
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

### Windows

```batch
build\build_win.bat
```

输出：`dist\VoicePad\VoicePad.exe`

### macOS

```bash
chmod +x build/build_mac.sh
./build/build_mac.sh
```

输出：`dist/VoicePad-macos.dmg`

## 项目结构

```
src/voicepad/
├── app.py                     # 主控制器
├── __main__.py                # CLI 入口
├── config/                    # 配置管理
├── subsystems/
│   ├── asr/                   # 语音识别（faster-whisper）
│   ├── llm_engine/            # LLM 润色（Ollama / 远程 API）
│   └── hotkey_listener/       # 全局快捷键（keyboard）
└── modules/
    ├── recorder/              # 音频录制（sounddevice）
    ├── clipboard/             # 剪贴板操作（pyperclip）
    ├── notify/                # 通知和提示音
    ├── i18n/                  # 国际化（中/英）
    ├── tray/                  # 系统托盘（pystray）
    └── settings_window/       # 设置界面（customtkinter）
```

## 开发

### 运行测试

```bash
# 全部测试
python -m pytest tests/ -v

# 跳过硬件相关测试
python -m pytest tests/ -v -m "not hardware"

# 按 ID 运行单个测试
python -m pytest tests/*/U001/ -v
```

## 许可证

[MIT](./LICENSE)
