#!/usr/bin/env python3
"""Generate tray icons for VoicePad."""

import os

from PIL import Image, ImageDraw

ICON_SIZE = 64
ICONS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "icons"
)


def generate_mic_icon(output_name: str, fill_color: tuple) -> None:
    icon_image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw_context = ImageDraw.Draw(icon_image)

    draw_context.ellipse(
        [ICON_SIZE // 4, ICON_SIZE // 8, 3 * ICON_SIZE // 4, 5 * ICON_SIZE // 8],
        fill=fill_color,
    )

    draw_context.rectangle(
        [
            ICON_SIZE // 4 + 4,
            ICON_SIZE // 2,
            3 * ICON_SIZE // 4 - 4,
            3 * ICON_SIZE // 4,
        ],
        fill=fill_color,
    )

    draw_context.arc(
        [ICON_SIZE // 6, ICON_SIZE // 4, 5 * ICON_SIZE // 6, 3 * ICON_SIZE // 4],
        start=0,
        end=180,
        fill=fill_color,
        width=2,
    )

    draw_context.line(
        [ICON_SIZE // 2, 3 * ICON_SIZE // 4, ICON_SIZE // 2, 7 * ICON_SIZE // 8],
        fill=fill_color,
        width=3,
    )

    draw_context.line(
        [
            ICON_SIZE // 3,
            7 * ICON_SIZE // 8,
            2 * ICON_SIZE // 3,
            7 * ICON_SIZE // 8,
        ],
        fill=fill_color,
        width=3,
    )

    output_path = os.path.join(ICONS_DIR, output_name)
    icon_image.save(output_path, "PNG")
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    os.makedirs(ICONS_DIR, exist_ok=True)
    generate_mic_icon("voicepad.png", (128, 128, 128))
    generate_mic_icon("voicepad_idle.png", (128, 128, 128))
    generate_mic_icon("voicepad_recording.png", (220, 50, 50))
    generate_mic_icon("voicepad_processing.png", (50, 120, 220))
    print("All icons generated successfully.")
