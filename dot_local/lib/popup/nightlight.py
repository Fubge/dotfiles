"""Night light logic, shared by ~/.local/bin/nightlight (the daemon that
drives hyprsunset) and the system menu (SUPER+ALT+Space -> night light).

Settings (settings.json, section "nightlight"):
    mode   off | sunset | schedule | always
    temp   color temperature at night in Kelvin (warmer = lower)
    start, end   "HH:MM" for mode schedule

"sunset" needs no location setup: the coordinates of the time zone's main
city (/usr/share/zoneinfo/zone1970.tab, e.g. Berlin for Europe/Berlin) are
close enough for sunrise and sunset. The change is a slow fade over FADE_MIN
minutes, from the start of the night and towards its end.
"""
import math
import os
import time

import settings
from i18n import T

DAY_K = 6500               # neutral (hyprsunset identity)
DEFAULTS = {"mode": "off", "temp": 4000, "start": "21:00", "end": "07:00"}
FADE_MIN = 45
TEMP_RANGE = (2500, 6000)


def config():
    c = dict(DEFAULTS)
    c.update(settings.get("nightlight"))
    return c


def zone():
    """(zone name, latitude, longitude) of the local time zone, or None."""
    try:
        name = os.path.realpath("/etc/localtime").split("/zoneinfo/", 1)[1]
    except IndexError:
        return None
    try:
        for line in open("/usr/share/zoneinfo/zone1970.tab"):
            parts = line.split("\t")
            if len(parts) >= 3 and parts[2].strip() == name:
                return name, *_coords(parts[1])
    except OSError:
        pass
    return None


def _coords(iso):
    """'+5230+01322' -> (52.5, 13.37)"""
    split = max(iso.rfind("+"), iso.rfind("-"))
    lat, lon = iso[:split], iso[split:]

    def deg(s, width):
        sign = -1 if s[0] == "-" else 1
        s = s[1:]
        d, m, sec = int(s[:width]), int(s[width:width + 2]), int(s[width + 2:] or 0)
        return sign * (d + m / 60 + sec / 3600)
    return deg(lat, 2), deg(lon, 3)


def sun_times(day=None):
    """Sunrise and sunset today as minutes after local midnight (NOAA
    approximation, ~1 min). None near the poles or without a known zone."""
    z = zone()
    if not z:
        return None
    _name, lat, lon = z
    t = time.localtime(day or time.time())
    g = 2 * math.pi / 365 * (t.tm_yday - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    x = (math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(decl))
         - math.tan(la) * math.tan(decl))
    if not -1 <= x <= 1:
        return None
    ha = math.degrees(math.acos(x))
    offset = t.tm_gmtoff / 60
    rise = 720 - 4 * (lon + ha) - eqtime + offset
    sset = 720 - 4 * (lon - ha) - eqtime + offset
    return rise % 1440, sset % 1440


def hhmm(minutes):
    minutes = int(round(minutes)) % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse(s):
    try:
        h, m = s.split(":")
        return (int(h) * 60 + int(m)) % 1440
    except (ValueError, AttributeError):
        return 0


def night(c=None):
    """(start, end) of the night in minutes after midnight, or None (off / always)."""
    c = c or config()
    if c["mode"] == "schedule":
        return parse(c["start"]), parse(c["end"])
    if c["mode"] == "sunset":
        sun = sun_times()
        if sun:
            return sun[1], sun[0]
        return parse(DEFAULTS["start"]), parse(DEFAULTS["end"])
    return None


def target(c=None, now=None):
    """Temperature wanted right now (DAY_K = off)."""
    c = c or config()
    temp = max(TEMP_RANGE[0], min(TEMP_RANGE[1], int(c["temp"])))
    if c["mode"] == "always":
        return temp
    span = night(c)
    if not span:
        return DAY_K
    start, end = span
    t = time.localtime(now or time.time())
    m = t.tm_hour * 60 + t.tm_min + t.tm_sec / 60
    since = (m - start) % 1440          # minutes into the night
    length = (end - start) % 1440 or 1440
    if since >= length:
        return DAY_K
    until = length - since
    k = max(0.0, min(1.0, since / FADE_MIN, until / FADE_MIN))
    return int(round(DAY_K - (DAY_K - temp) * k))


def status(c=None):
    """Short line for the menu tile."""
    c = c or config()
    mode = c["mode"]
    if mode == "off":
        return T("nightlight.off")
    if mode == "always":
        return T("nightlight.always", temp=c['temp'])
    span = night(c)
    if not span:
        return T("nightlight.off")
    now = target(c)
    if now < DAY_K:
        return T("nightlight.on_until", time=hhmm(span[1]))
    return T("nightlight.from", time=hhmm(span[0]))
