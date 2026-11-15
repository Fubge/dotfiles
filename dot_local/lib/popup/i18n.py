"""Visible texts in the language picked at `chezmoi init` (machine.lang).

All of them live in the repo's .chezmoidata/locale.toml (de + en side by
side); chezmoi renders the chosen language into ~/.config/popups/strings.json,
flat "area.key": "text".

    T("common.connecting")               -> "Verbinde …"
    T("wifi.password_for", ssid=name)    -> str.format placeholders
    Tn("cal.events", 3)                  -> picks cal.events_one / _other, {n} filled
    T("cal.weekdays")                    -> lists come back as lists

A missing key shows up as the key itself, so a typo is visible, not a crash.
"""
import json
import os

PATH = os.path.expanduser("~/.config/popups/strings.json")

try:
    with open(PATH) as f:
        _S = json.load(f)
except (OSError, ValueError):
    _S = {}

LANG = _S.get("meta.lang", "en")


def T(key, /, **kw):
    s = _S.get(key, key)
    return s.format(**kw) if kw and isinstance(s, str) else s


def Tn(key, n, /, **kw):
    return T(f"{key}_{'one' if n == 1 else 'other'}", n=n, **kw)


def greeting(name=True):
    """Time of day greeting, the same words on the lock screen, in the bar and
    the session menu: "Guten Abend, Raphael"."""
    import time
    h = time.localtime().tm_hour
    hello = T("greet.night" if h < 5 or h >= 22 else "greet.morning" if h < 11 else
              "greet.day" if h < 18 else "greet.evening")
    return T("greet.with_name", hello=hello,
             name=os.environ.get("USER", "").capitalize()) if name else hello


def dec(text):
    """Decimal comma in German: dec(f"{x:.1f} h")."""
    return text.replace(".", ",") if LANG == "de" else text
