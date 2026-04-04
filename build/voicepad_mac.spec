# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import site
from pathlib import Path

block_cipher = None

project_root = os.path.abspath(os.path.join(SPECPATH, ".."))

site_packages = site.getsitepackages()[0]

webview_path = os.path.join(site_packages, "webview")

faster_whisper_assets_path = None
for sp in site.getsitepackages():
    candidate = os.path.join(sp, "faster_whisper", "assets")
    if os.path.isdir(candidate):
        faster_whisper_assets_path = candidate
        break

frontend_dir = os.path.join(
    project_root, "src", "voicepad", "modules", "main_window", "frontend"
)

datas = [
    (os.path.join(project_root, "sounds"), "sounds"),
    (os.path.join(project_root, "icons"), "icons"),
    (os.path.join(project_root, "config.example.yaml"), "."),
    (frontend_dir, os.path.join("voicepad", "modules", "main_window", "frontend")),
]
if os.path.isdir(webview_path):
    datas.append((webview_path, "webview"))
if faster_whisper_assets_path:
    datas.append((faster_whisper_assets_path, os.path.join("faster_whisper", "assets")))

a = Analysis(
    [os.path.join(project_root, "src", "voicepad", "__main__.py")],
    pathex=[os.path.join(project_root, "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "voicepad",
        "voicepad.app",
        "voicepad.config.config_manager",
        "voicepad.modules.i18n.i18n_manager",
        "voicepad.modules.i18n.locales.en",
        "voicepad.modules.i18n.locales.zh",
        "voicepad.modules.clipboard.clipboard_writer",
        "voicepad.modules.notify.notifier",
        "voicepad.modules.recorder.audio_recorder",
        "voicepad.modules.tray.tray_app",
        "voicepad.modules.main_window.window_api",
        "voicepad.asr_subprocess",
        "voicepad.panel_subprocess",
        "voicepad.settings_subprocess",
        "voicepad.subsystems.asr.asr_engine",
        "voicepad.subsystems.llm_engine.llm_router",
        "voicepad.subsystems.llm_engine.ollama_backend",
        "voicepad.subsystems.llm_engine.remote_backend",
        "voicepad.subsystems.hotkey_listener.hotkey_manager",
        "webview",
        "pystray",
        "pystray._darwin",
        "pystray._base",
        "pystray._util",
        "six",
        "six.moves",
        "keyboard",
        "plyer.platforms.macosx",
        "plyer.platforms.macosx.notification",
        "scipy.io",
        "scipy.io.wavfile",
        "ctranslate2",
        "faster_whisper",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpenTypeFewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join(project_root, "icons", "opentypefewer.icns"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OpenTypeFewer",
)

app = BUNDLE(
    coll,
    name="OpenTypeFewer.app",
    icon=os.path.join(project_root, "icons", "opentypefewer.icns"),
    bundle_identifier="com.opentypefewer.app",
    info_plist={
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": "OpenTypeFewer needs microphone access to record speech for transcription.",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleName": "OpenTypeFewer",
    },
)
