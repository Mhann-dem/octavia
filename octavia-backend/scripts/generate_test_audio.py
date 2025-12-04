"""Generate a short test WAV file (mono, 16kHz) for integration tests.
Usage: python scripts/generate_test_audio.py [output_path]
"""
import sys
import wave
import math
import struct

def generate_wav(path, duration=2.0, freq=440.0, sr=16000):
    n_samples = int(sr * duration)
    amplitude = 0.5 * 32767
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        for i in range(n_samples):
            t = i / sr
            val = int(amplitude * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack('<h', val))

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'test_audio.wav'
    print(f"Generating {out} ...")
    generate_wav(out)
    print("Done")
