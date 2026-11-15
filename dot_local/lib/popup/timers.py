"""Kitchen timers shared by the timer popup (~/.local/bin/timer-popup, which
also rings them) and the bar countdown (~/.local/bin/timer-bar).

State: ~/.local/state/timer/timers.json
    {"timers":  [{"id", "label", "icon", "total", "end"} ...],   running
                 ... or "left" instead of "end" while paused
     "ringing": [{"id", "label", "icon", "total", "at"} ...]}    done, not yet seen

Times are epoch seconds. Written atomically; readers only look again when the
file's mtime changed.
"""
import json
import os
import re
import time
import uuid

STATE = os.path.expanduser("~/.local/state/timer/timers.json")

TIMER = "\U000F13AB"        # md-timer
SAND = ("\U000F078C", "\U000F051F", "\U000F06AD")   # full, running, empty
PAUSED = "\U000F19A0"       # md-timer_sand_paused
BELL = "\U000F009E"         # md-bell_ring

# label, minutes, icon, color name (palette) - the round preset buttons
PRESETS = [
    ("Ei", 7, "\U000F0AAF", "yellow"),
    ("Tee", 4, "\U000F0D9E", "green"),
    ("Nudeln", 9, "\U000F1160", "accent"),
    ("Pizza", 12, "\U000F0409", "red"),
    ("Pause", 5, "\U000F0176", "cyan"),
    ("Fokus", 25, "\U000F09D1", "magenta"),
]


def load():
    try:
        with open(STATE) as f:
            s = json.load(f)
    except (OSError, ValueError):
        s = {}
    s.setdefault("timers", [])
    s.setdefault("ringing", [])
    return s


def save(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(s, f)
    os.replace(tmp, STATE)


def mtime():
    try:
        return os.stat(STATE).st_mtime_ns
    except OSError:
        return 0


def left(t, now=None):
    """seconds left (float), paused ones keep theirs"""
    if "left" in t:
        return t["left"]
    return max(0.0, t["end"] - (now or time.time()))


def add(label, seconds, icon=None):
    s = load()
    t = {"id": uuid.uuid4().hex[:8], "label": label, "icon": icon or "",
         "total": seconds, "end": time.time() + seconds}
    s["timers"].append(t)
    save(s)
    return t


def change(tid, fn):
    """apply fn(timer) to one timer (returns False to drop it) and save"""
    s = load()
    keep = []
    for t in s["timers"]:
        if t["id"] != tid or fn(t) is not False:
            keep.append(t)
    s["timers"] = keep
    save(s)


def pause(t):
    if "left" in t:                      # resume
        t["end"] = time.time() + t.pop("left")
    else:
        t["left"] = left(t)
        t.pop("end", None)


def plus(t, seconds=60):
    if "left" in t:
        t["left"] += seconds
    else:
        t["end"] = max(t["end"], time.time()) + seconds
    t["total"] += seconds


def clock(sec):
    """4:05 / 1:02:03, rounded up: a timer shows 0:00 only when it rings"""
    sec = int(-(-sec // 1))
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def words(sec):
    """12 Min / 1 Std 30 Min / 45 Sek"""
    sec = int(round(sec))
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    out = []
    if h:
        out.append(f"{h} Std")
    if m:
        out.append(f"{m} Min")
    if s and not h:
        out.append(f"{s} Sek")
    return " ".join(out) or "0 Sek"


UNITS = {"h": 3600, "std": 3600, "stunde": 3600, "stunden": 3600,
         "m": 60, "min": 60, "mins": 60, "minute": 60, "minuten": 60,
         "s": 1, "sek": 1, "sec": 1, "sekunde": 1, "sekunden": 1}


def parse(text):
    """'Pizza 12' -> ('Pizza', 720); '1h 30' -> ('', 5400); '90s Tee' ->
    ('Tee', 90); '2:30' -> 150; 'halbe Stunde' -> 1800. A bare number is
    minutes; after hours it is minutes too. Returns (label, seconds or 0)."""
    t = " " + text + " "
    sec = 0

    def take(pattern, fn):
        nonlocal t, sec
        while True:
            m = re.search(pattern, t, re.I)
            if not m:
                return
            sec += fn(m)
            t = t[:m.start()] + " " + t[m.end():]

    take(r"(?<!\S)(\d{1,2}):(\d{2})(?!\S)", lambda m: int(m[1]) * 60 + int(m[2]))
    take(r"(?<!\S)(?:eine\s+)?halbe\s+stunde(?!\S)", lambda m: 1800)
    take(r"(?<!\S)(?:eine\s+)?viertel\s*stunde(?!\S)", lambda m: 900)
    take(r"(?<!\S)(\d+(?:[.,]\d+)?)\s*(" + "|".join(sorted(UNITS, key=len, reverse=True))
         + r")\.?(?!\S)", lambda m: round(float(m[1].replace(",", ".")) * UNITS[m[2].lower()]))
    take(r"(?<!\S)(\d+(?:[.,]\d+)?)(?!\S)", lambda m: round(float(m[1].replace(",", ".")) * 60))
    label = " ".join(w for w in t.split() if w.lower() not in ("für", "in", "und", "timer"))
    return label[:1].upper() + label[1:], sec
