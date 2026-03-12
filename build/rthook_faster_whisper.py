"""Runtime hook: fix faster_whisper assets path inside a macOS .app bundle.

In a PyInstaller BUNDLE, Python modules land in Contents/Frameworks/ but
collect_data_files puts assets in Contents/Resources/.
faster_whisper.utils.get_assets_path() uses __file__ and finds the wrong dir.
"""
import os
import sys

if getattr(sys, "frozen", False):
    import faster_whisper.utils as _fw_utils

    def _get_assets_path():
        # sys.executable = .../VoicePad.app/Contents/MacOS/VoicePad
        # assets land at  .../VoicePad.app/Contents/Resources/faster_whisper/assets
        candidates = [
            os.path.join(os.path.dirname(sys.executable),
                         "..", "Resources", "faster_whisper", "assets"),
            os.path.join(os.path.dirname(sys.executable),
                         "faster_whisper", "assets"),
        ]
        for path in candidates:
            path = os.path.normpath(path)
            if os.path.isdir(path):
                return path
        # fallback to original logic
        return os.path.join(os.path.dirname(os.path.abspath(_fw_utils.__file__)), "assets")

    _fw_utils.get_assets_path = _get_assets_path
