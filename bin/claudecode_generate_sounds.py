#!/usr/bin/env python3
"""Generate default chime WAV files for VoicePad."""

import os
import sys
import struct
import wave
import math


SAMPLE_RATE = 44100
SOUNDS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "sounds"
)


def generate_tone(frequency_hz: float, duration_seconds: float, volume: float = 0.5) -> list:
    sample_count = int(SAMPLE_RATE * duration_seconds)
    audio_samples = []
    for sample_index in range(sample_count):
        time_value = sample_index / SAMPLE_RATE
        envelope = 1.0
        fade_samples = int(SAMPLE_RATE * 0.01)
        if sample_index < fade_samples:
            envelope = sample_index / fade_samples
        elif sample_index > sample_count - fade_samples:
            envelope = (sample_count - sample_index) / fade_samples
        sample_value = volume * envelope * math.sin(2 * math.pi * frequency_hz * time_value)
        audio_samples.append(int(sample_value * 32767))
    return audio_samples


def write_wav_file(file_path: str, audio_samples: list) -> None:
    with wave.open(file_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        packed_data = struct.pack(f"<{len(audio_samples)}h", *audio_samples)
        wav_file.writeframes(packed_data)


def generate_start_sound() -> None:
    tone_high = generate_tone(880, 0.15, 0.4)
    output_path = os.path.join(SOUNDS_DIR, "start.wav")
    write_wav_file(output_path, tone_high)
    print(f"Generated: {output_path}")


def generate_stop_sound() -> None:
    tone_low = generate_tone(440, 0.15, 0.4)
    output_path = os.path.join(SOUNDS_DIR, "stop.wav")
    write_wav_file(output_path, tone_low)
    print(f"Generated: {output_path}")


def generate_done_sound() -> None:
    tone_a = generate_tone(523, 0.1, 0.3)
    tone_b = generate_tone(659, 0.1, 0.3)
    tone_c = generate_tone(784, 0.15, 0.3)
    combined_samples = tone_a + tone_b + tone_c
    output_path = os.path.join(SOUNDS_DIR, "done.wav")
    write_wav_file(output_path, combined_samples)
    print(f"Generated: {output_path}")


def generate_error_sound() -> None:
    tone_low = generate_tone(220, 0.3, 0.4)
    output_path = os.path.join(SOUNDS_DIR, "error.wav")
    write_wav_file(output_path, tone_low)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    generate_start_sound()
    generate_stop_sound()
    generate_done_sound()
    generate_error_sound()
    print("All sounds generated successfully.")
