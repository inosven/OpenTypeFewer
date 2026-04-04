# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import site
from pathlib import Path

block_cipher = None

project_root = os.path.abspath(os.path.join(SPECPATH, ".."))

all_site_dirs = site.getsitepackages() + [site.getusersitepackages()]

nvidia_binaries = []
for sp in all_site_dirs:
    nvidia_dir = Path(sp) / "nvidia"
    if nvidia_dir.exists():
        for dll_file in nvidia_dir.rglob("*.dll"):
            nvidia_binaries.append(
                (str(dll_file), str(dll_file.parent.relative_to(sp)))
            )

ctranslate2_binaries = []
for sp in all_site_dirs:
    ct2_dir = Path(sp) / "ctranslate2"
    if ct2_dir.exists():
        for dll_file in ct2_dir.rglob("*.dll"):
            ctranslate2_binaries.append(
                (str(dll_file), str(dll_file.parent.relative_to(sp)))
            )

webview_path = None
for sp in all_site_dirs:
    candidate = os.path.join(sp, "webview")
    if os.path.isdir(candidate):
        webview_path = candidate
        break

sounddevice_data_path = None
faster_whisper_assets_path = None
for sp in all_site_dirs:
    candidate = os.path.join(sp, "_sounddevice_data")
    if os.path.isdir(candidate) and not sounddevice_data_path:
        sounddevice_data_path = candidate
    candidate = os.path.join(sp, "faster_whisper", "assets")
    if os.path.isdir(candidate) and not faster_whisper_assets_path:
        faster_whisper_assets_path = candidate

frontend_dir = os.path.join(
    project_root, "src", "voicepad", "modules", "main_window", "frontend"
)

datas = [
    (os.path.join(project_root, "sounds"), "sounds"),
    (os.path.join(project_root, "icons"), "icons"),
    (os.path.join(project_root, "config.example.yaml"), "."),
    (frontend_dir, os.path.join("voicepad", "modules", "main_window", "frontend")),
]
if webview_path:
    datas.append((webview_path, "webview"))
if sounddevice_data_path:
    datas.append((sounddevice_data_path, "_sounddevice_data"))
if faster_whisper_assets_path:
    datas.append((faster_whisper_assets_path, os.path.join("faster_whisper", "assets")))

a = Analysis(
    [os.path.join(project_root, "src", "voicepad", "__main__.py")],
    pathex=[os.path.join(project_root, "src")],
    binaries=nvidia_binaries + ctranslate2_binaries,
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
        "webview.platforms.edgechromium",
        "clr",
        "pythonnet",
        "clr_loader",
        "pystray",
        "pystray._win32",
        "pystray._base",
        "pystray._util",
        "pystray._util.win32",
        "PIL",
        "PIL.Image",
        "PIL.IcoImagePlugin",
        "PIL.PngImagePlugin",
        "PIL.BmpImagePlugin",
        "six",
        "six.moves",
        "keyboard",
        "keyboard._winkeyboard",
        "plyer.platforms.win",
        "plyer.platforms.win.notification",
        "scipy.io",
        "scipy.io.wavfile",
        "ctranslate2",
        "faster_whisper",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
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
    icon=os.path.join(project_root, "icons", "opentypefewer_tray.png"),
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
