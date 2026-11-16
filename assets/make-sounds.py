#!/usr/bin/env python3
"""Renders the system's own sounds into dot_local/share/sounds/slate/
(needs ffmpeg). Run it from the repo root after changing a sound:
    python3 assets/make-sounds.py

timer.oga  the kitchen timer's alarm (~/.local/bin/timer-popup): a soft,
           warm three-note chime instead of a beeping alarm clock
tick.oga   volume feedback (~/.local/bin/sound-popup, ~/.local/bin/osd):
           a short wooden tick, played at the new volume
"""
import math
import os
import struct
import subprocess
import tempfile
import wave

RATE = 48000
OUT = os.path.join(os.path.dirname(__file__), "..", "dot_local", "share", "sounds", "slate")


def note(freq, length, partials, decay, attack=0.004):
    """one struck note: a few sine partials (multiple, level), each dying
    away faster the higher it is"""
    out = []
    for i in range(int(RATE * length)):
        t = i / RATE
        v = sum(level * math.sin(2 * math.pi * freq * mult * t) * math.exp(-t * decay * mult)
                for mult, level in partials)
        out.append(v * min(1.0, t / attack))
    return out


def mix(parts, length):
    """parts: (start in s, samples)"""
    buf = [0.0] * int(RATE * length)
    for start, samples in parts:
        at = int(start * RATE)
        for i, v in enumerate(samples):
            if at + i < len(buf):
                buf[at + i] += v
    return buf


def write(name, buf, peak):
    top = max(abs(v) for v in buf) or 1
    fade = int(RATE * 0.02)                 # no click at the end
    for i in range(fade):
        buf[-1 - i] *= i / fade
    data = b"".join(struct.pack("<h", int(v / top * peak * 32767)) for v in buf)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(data)
        os.makedirs(OUT, exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp.name,
                        "-c:a", "libvorbis", "-q:a", "4", os.path.join(OUT, name)], check=True)


# marimba-like: strong fundamental, a little 4th partial, quick warm decay
BAR = ((1, 1.0), (2, 0.18), (4, 0.10))
G4, C5, E5, G5 = 392.00, 523.25, 659.25, 783.99
write("timer.oga", mix([(0.00, note(C5, 1.4, BAR, 3.2)),
                        (0.22, note(E5, 1.4, BAR, 3.2)),
                        (0.44, note(G5, 1.8, BAR, 2.6)),
                        (0.44, note(G4, 1.8, BAR, 2.6))], 2.3), peak=0.5)
write("tick.oga", note(880, 0.09, ((1, 1.0), (2.7, 0.25)), 45, attack=0.002), peak=0.6)
