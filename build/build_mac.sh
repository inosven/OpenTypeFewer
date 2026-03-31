#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== OpenTypeFewer macOS Build ==="
echo

# ── Convert PNG icon to ICNS ──────────────────────────────────────────────────
ICON_PNG="../logo-color.png"
ICON_ICNS="icons/opentypefewer.icns"

if [ ! -f "$ICON_ICNS" ]; then
    echo "Converting icon PNG → ICNS..."
    ICONSET_DIR="icons/voicepad.iconset"
    mkdir -p "$ICONSET_DIR"

    for SIZE in 16 32 64 128 256 512; do
        sips -z $SIZE $SIZE "$ICON_PNG" --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}.png" > /dev/null
        DOUBLE=$((SIZE * 2))
        sips -z $DOUBLE $DOUBLE "$ICON_PNG" --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}@2x.png" > /dev/null
    done

    iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS"
    rm -rf "$ICONSET_DIR"
    echo "Icon created: $ICON_ICNS"
fi

echo

# ── Clean previous build ──────────────────────────────────────────────────────
echo "Cleaning previous build..."
rm -rf dist/ build/output/

echo

# ── PyInstaller ───────────────────────────────────────────────────────────────
echo "Building with PyInstaller..."
pyinstaller build/voicepad_mac.spec \
    --clean \
    --distpath dist \
    --workpath build/output

echo

# ── Verify app bundle ─────────────────────────────────────────────────────────
if [ ! -d "dist/OpenTypeFewer.app" ]; then
    echo "ERROR: dist/OpenTypeFewer.app not found. Build failed."
    exit 1
fi

echo "App bundle created: dist/OpenTypeFewer.app"
echo

# ── Fix faster_whisper assets path ────────────────────────────────────────────
# PyInstaller puts datas in Contents/Resources but faster_whisper looks in
# Contents/Frameworks (where the frozen module lives). Copy to both places.
echo "Fixing faster_whisper assets..."
ONNX_SRC="dist/OpenTypeFewer.app/Contents/Resources/faster_whisper/assets/silero_vad_v6.onnx"
ONNX_DST="dist/OpenTypeFewer.app/Contents/Frameworks/faster_whisper/assets/silero_vad_v6.onnx"
if [ -f "$ONNX_SRC" ]; then
    mkdir -p "$(dirname "$ONNX_DST")"
    cp "$ONNX_SRC" "$ONNX_DST" || true
    echo "Copied silero_vad_v6.onnx to Frameworks"
else
    echo "WARNING: silero_vad_v6.onnx not found in Resources, skipping"
fi
echo

# ── Create DMG ────────────────────────────────────────────────────────────────
echo "Creating DMG..."
create-dmg \
    --volname "OpenTypeFewer" \
    --window-pos 200 120 \
    --window-size 540 380 \
    --icon-size 128 \
    --icon "OpenTypeFewer.app" 130 180 \
    --app-drop-link 400 180 \
    --background "icons/voicepad.png" \
    "dist/OpenTypeFewer-macos.dmg" \
    "dist/OpenTypeFewer.app"

echo
echo "✓ Build complete"
echo "  App:  dist/OpenTypeFewer.app"
echo "  DMG:  dist/OpenTypeFewer-macos.dmg"
echo
echo "NOTE: First launch requires granting Accessibility permission:"
echo "  System Settings > Privacy & Security > Accessibility → add OpenTypeFewer"
