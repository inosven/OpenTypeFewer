#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== VoicePad macOS Build ==="
echo

echo "Cleaning previous build..."
rm -rf dist/ build/output/

echo
echo "Building with PyInstaller..."
pyinstaller build/voicepad_mac.spec --clean --distpath dist --workpath build/output

echo
echo "Creating DMG..."
hdiutil create -volname "VoicePad" \
    -srcfolder "dist/VoicePad.app" \
    -ov -format UDZO \
    "dist/VoicePad-macos.dmg"

echo
echo "Build complete: dist/VoicePad-macos.dmg"
