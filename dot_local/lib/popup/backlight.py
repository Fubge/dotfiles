"""Screen brightness as perceived percent, shared by the brightness popup
and the control center. Square-root curve like the brightness keys
(brightnessctl -e2), spread over the hardware range: 1% = darkest step
(raw 1; 0 is panel off), 100% = full. ~/.local/bin/brightness shows the same
numbers in the bar."""
import subprocess
from pathlib import Path

# first backlight device (intel_backlight, amdgpu_bl0, ...)
DEVICE = next(Path("/sys/class/backlight").iterdir(), Path("/sys/class/backlight/none"))
EXPONENT = 2
ICONS = ["\U000F0594", "\U000F0595", "\U000F05A8"]  # moon / cloud / sun, as in the bar


def to_percent(raw):
    top = int((DEVICE / "max_brightness").read_text())
    return int((max(0, raw - 1) / (top - 1)) ** (1 / EXPONENT) * 99 + 1.5)


def read_percent():
    return to_percent(int((DEVICE / "brightness").read_text()))


def to_raw(percent):
    top = int((DEVICE / "max_brightness").read_text())
    return 1 + round((top - 1) * ((percent - 1) / 99) ** EXPONENT)


def write_percent(percent):
    subprocess.run(["brightnessctl", "-q", "set", str(to_raw(percent))], check=False)


def icon(percent):
    return ICONS[0 if percent <= 33 else 1 if percent <= 66 else 2]
