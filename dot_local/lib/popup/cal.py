"""Shared calendar bits: the two Nextcloud calendars that vdirsyncer keeps in
~/.local/share/calendars (one folder per calendar, one .ics per event, plus
`displayname` and `color` files). Used by the calendar popup, the quick-add
popup and the reminder daemon.

    cal.calendars()              -> [Calendar], own calendar first
    cal.occurrences(a, b)        -> [Occurrence] overlapping [a, b) (datetimes)
    cal.day(d)                   -> [Occurrence] on date d, all-day first
    cal.add(cal_id, title, start, end, allday, location, alarm)
    cal.delete(occurrence)       -> removes the event (a series: all of it)
    cal.sync()                   -> vdirsyncer now, in the background

Small own iCalendar reader (no python-icalendar): unfolds lines, reads VEVENTs
with DTSTART/DTEND/DURATION (dates, UTC, TZID, floating), RRULE + EXDATE via
dateutil, RECURRENCE-ID overrides, VALARM triggers. Enough for what Nextcloud
and the iPhone write. New events are written in UTC, so no VTIMEZONE is needed.
"""
import datetime as dt
import os
import re
import subprocess
import uuid
from zoneinfo import ZoneInfo

from dateutil import rrule

ROOT = os.path.expanduser("~/.local/share/calendars")
OWN = "the-preu-plans-1"            # Flauschebär: the user's own calendar
# short names and glyphs per calendar (Nextcloud's names are long)
PEOPLE = {
    "the-preu-plans-1": ("Flauschebär", "\U000F18FB"),   # teddy bear
    "the-preu-plans": ("Pia", "\U000F02D1"),             # heart
}
DEFAULT_ALARM = dt.timedelta(minutes=-15)   # own timed events without a VALARM


def _local_zone():
    try:
        return ZoneInfo(os.path.realpath("/etc/localtime").split("zoneinfo/", 1)[1])
    except (IndexError, KeyError, ValueError):
        return dt.timezone.utc


TZ = _local_zone()


def now():
    return dt.datetime.now(TZ)


class Calendar:
    def __init__(self, cid):
        self.id = cid
        self.path = os.path.join(ROOT, cid)
        name = _read(os.path.join(self.path, "displayname")) or cid
        self.long_name = name
        self.name, self.glyph = PEOPLE.get(cid, (name.split(" - ")[-1], "\U000F00ED"))
        self.color = _read(os.path.join(self.path, "color")) or "#7aa2f7"
        self.color = self.color[:7]
        self.own = cid == OWN


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def calendars():
    try:
        ids = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
    except OSError:
        ids = []
    return sorted((Calendar(i) for i in ids), key=lambda c: (not c.own, c.name))


# ---------------------------------------------------------------- parsing
def _unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def _prop(line):
    """'DTSTART;TZID=Europe/Berlin:2026...' -> ('DTSTART', {'TZID': ...}, value)"""
    head, value, quoted = "", "", False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch == ":" and not quoted:
            head, value = line[:i], line[i + 1:]
            break
    else:
        return None, {}, ""
    name, *params = head.split(";")
    p = {}
    for item in params:
        k, _, v = item.partition("=")
        p[k.upper()] = v.strip('"')
    return name.upper(), p, value


def _text(v):
    return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) in "nN" else m.group(1), v)


def _when(value, params):
    """date for all-day values, else an aware datetime"""
    value = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        return dt.datetime.strptime(value[:8], "%Y%m%d").date()
    t = dt.datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    if value.endswith("Z"):
        return t.replace(tzinfo=dt.timezone.utc).astimezone(TZ)
    try:
        zone = ZoneInfo(params["TZID"]) if "TZID" in params else TZ
    except (KeyError, ValueError):
        zone = TZ
    return t.replace(tzinfo=zone).astimezone(TZ)


_DUR = re.compile(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?")


def _duration(v):
    m = _DUR.fullmatch(v.strip())
    if not m:
        return None
    sign, w, d, h, mi, s = m.groups()
    td = dt.timedelta(weeks=int(w or 0), days=int(d or 0), hours=int(h or 0),
                      minutes=int(mi or 0), seconds=int(s or 0))
    return -td if sign == "-" else td


class Event:
    def __init__(self, cal, path):
        self.cal = cal
        self.path = path
        self.uid = self.summary = self.location = self.description = ""
        self.start = self.end = None
        self.duration = None
        self.rrule = None
        self.exdates = set()
        self.recurrence_id = None
        self.alarms = []          # timedelta (relative to start) or datetime
        self.cancelled = False

    @property
    def allday(self):
        return not isinstance(self.start, dt.datetime)


def _parse_file(cal, path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = _unfold(f.read())
    except OSError:
        return []
    events, ev, depth_alarm, stack = [], None, False, []
    for line in lines:
        name, params, value = _prop(line)
        if name == "BEGIN":
            stack.append(value.upper())
            if value.upper() == "VEVENT":
                ev = Event(cal, path)
            elif value.upper() == "VALARM" and ev:
                depth_alarm = True
            continue
        if name == "END":
            if stack:
                stack.pop()
            if value.upper() == "VEVENT" and ev:
                if ev.start is not None:
                    events.append(ev)
                ev = None
            elif value.upper() == "VALARM":
                depth_alarm = False
            continue
        if not ev or not stack or stack[-1] not in ("VEVENT", "VALARM"):
            continue
        try:
            if depth_alarm:
                if name == "TRIGGER":
                    if params.get("VALUE") == "DATE-TIME":
                        ev.alarms.append(_when(value, params))
                    else:
                        td = _duration(value)
                        if td is not None:
                            ev.alarms.append(td)
                continue
            if name == "UID":
                ev.uid = value
            elif name == "SUMMARY":
                ev.summary = _text(value).strip()
            elif name == "LOCATION":
                ev.location = _text(value).strip()
            elif name == "DESCRIPTION":
                ev.description = _text(value).strip()
            elif name == "DTSTART":
                ev.start = _when(value, params)
            elif name == "DTEND":
                ev.end = _when(value, params)
            elif name == "DURATION":
                ev.duration = _duration(value)
            elif name == "RRULE":
                ev.rrule = value
            elif name == "EXDATE":
                for v in value.split(","):
                    ev.exdates.add(_key(_when(v, params)))
            elif name == "RECURRENCE-ID":
                ev.recurrence_id = _when(value, params)
            elif name == "STATUS":
                ev.cancelled = value.upper() == "CANCELLED"
        except ValueError:
            continue
    for e in events:
        if e.end is None:
            if e.duration is not None:
                e.end = e.start + e.duration
            elif e.allday:
                e.end = e.start + dt.timedelta(days=1)
            else:
                e.end = e.start
        if not e.summary:
            e.summary = "(ohne Titel)"
    return events


def _key(when):
    """comparable key for EXDATE / RECURRENCE-ID matching"""
    if isinstance(when, dt.datetime):
        return when.astimezone(dt.timezone.utc).replace(second=0, microsecond=0)
    return when


# ---------------------------------------------------------------- cache
_cache = {"sig": None, "events": []}


def _signature():
    sig = []
    for c in calendars():
        try:
            for e in os.scandir(c.path):
                if e.name.endswith(".ics"):
                    sig.append((e.path, e.stat().st_mtime_ns))
        except OSError:
            pass
    return tuple(sorted(sig))


def events():
    sig = _signature()
    if sig != _cache["sig"]:
        out = []
        for c in calendars():
            for path, _m in sig:
                if os.path.dirname(path) == c.path:
                    out.extend(_parse_file(c, path))
        _cache.update(sig=sig, events=out)
    return _cache["events"]


# ---------------------------------------------------------------- occurrences
class Occurrence:
    def __init__(self, event, start, end):
        self.event = event
        self.start = start
        self.end = end

    cal = property(lambda s: s.event.cal)
    summary = property(lambda s: s.event.summary)
    location = property(lambda s: s.event.location)
    allday = property(lambda s: s.event.allday)

    def bounds(self):
        """aware datetimes, all-day events from local midnight to midnight"""
        if self.allday:
            return (dt.datetime.combine(self.start, dt.time(), TZ),
                    dt.datetime.combine(self.end, dt.time(), TZ))
        return self.start, max(self.end, self.start)

    def alarm_times(self):
        out = []
        alarms = self.event.alarms
        if not alarms and self.cal.own and not self.allday:
            alarms = [DEFAULT_ALARM]
        base = self.bounds()[0]
        for a in alarms:
            out.append(a + base if isinstance(a, dt.timedelta) else a)
        return out

    def time_text(self):
        if self.allday:
            days = (self.end - self.start).days
            return "ganztägig" if days <= 1 else f"{days} Tage"
        if self.end <= self.start:
            return self.start.strftime("%H:%M")
        return f"{self.start:%H:%M} – {self.end:%H:%M}"


def _rule_text(rule, start):
    """dateutil wants UNTIL in UTC for aware starts and naive for naive ones"""
    if isinstance(start, dt.datetime):
        return re.sub(r"UNTIL=(\d{8})(?=;|$)", r"UNTIL=\1T235959Z", rule)
    return re.sub(r"UNTIL=(\d{8})T\d{6}Z?", r"UNTIL=\1", rule)


def occurrences(a, b):
    """all occurrences overlapping [a, b) (aware datetimes), sorted"""
    out = []
    evs = events()
    overrides = {}
    for e in evs:
        if e.recurrence_id is not None:
            overrides.setdefault(e.uid, {})[_key(e.recurrence_id)] = e
    for e in evs:
        if e.recurrence_id is not None:
            continue
        length = e.end - e.start
        if e.rrule:
            naive = e.allday
            first = dt.datetime.combine(e.start, dt.time()) if naive else e.start
            try:
                rule = rrule.rrulestr(_rule_text(e.rrule, e.start), dtstart=first)
            except (ValueError, TypeError):
                rule = None
            if rule is None:
                continue
            lo = (a - length) if not naive else (a - length).replace(tzinfo=None)
            hi = b if not naive else b.replace(tzinfo=None)
            try:
                starts = rule.between(lo - dt.timedelta(days=1), hi, inc=True)
            except (ValueError, TypeError):
                continue
            own = overrides.get(e.uid, {})
            for s in starts:
                s = s.date() if naive else s
                k = _key(s)
                if k in e.exdates or k in own:
                    continue
                out.append(Occurrence(e, s, s + length))
        else:
            out.append(Occurrence(e, e.start, e.end))
    for ovs in overrides.values():
        for e in ovs.values():
            out.append(Occurrence(e, e.start, e.end))
    result = []
    for o in out:
        if o.event.cancelled:
            continue
        s, en = o.bounds()
        if s < b and (en > a or (en == s and a <= s < b)):
            result.append(o)
    result.sort(key=lambda o: (o.bounds()[0], not o.allday, o.summary.lower()))
    return result


def day(d):
    a = dt.datetime.combine(d, dt.time(), TZ)
    occ = occurrences(a, a + dt.timedelta(days=1))
    occ.sort(key=lambda o: (not o.allday, o.bounds()[0], o.summary.lower()))
    return occ


# ---------------------------------------------------------------- writing
def _esc(text):
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\n", "\\n"))


def _fold(line):
    out, raw = [], line.encode()
    while len(raw) > 74:
        cut = 74
        while cut and (raw[cut] & 0xC0) == 0x80:   # do not split a UTF-8 character
            cut -= 1
        out.append(raw[:cut].decode())
        raw = b" " + raw[cut:]
    out.append(raw.decode())
    return "\r\n".join(out)


def _utc(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def add(cal_id, title, start, end, allday=False, location="", alarm=None):
    """Write a new event and kick off a sync. start/end: dates (all-day, end
    exclusive) or aware datetimes. alarm: timedelta before/after start or None."""
    uid = str(uuid.uuid4()).upper()
    stamp = _utc(now())
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//dotfiles//calendar//DE",
             "CALSCALE:GREGORIAN", "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}",
             f"CREATED:{stamp}", f"LAST-MODIFIED:{stamp}"]
    if allday:
        lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{end:%Y%m%d}",
                  "TRANSP:TRANSPARENT"]
    else:
        lines += [f"DTSTART:{_utc(start)}", f"DTEND:{_utc(end)}", "TRANSP:OPAQUE"]
    lines.append("SUMMARY:" + _esc(title))
    if location:
        lines.append("LOCATION:" + _esc(location))
    if alarm is not None:
        secs = int(alarm.total_seconds())
        sign, secs = ("-" if secs < 0 else ""), abs(secs)
        d, rest = divmod(secs, 86400)
        h, rest = divmod(rest, 3600)
        m = rest // 60
        trig = f"{sign}P" + (f"{d}D" if d else "") + (
            "T" + (f"{h}H" if h else "") + (f"{m}M" if m else "") if (h or m) else "")
        if trig.endswith("P"):
            trig += "T0S"
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Reminder",
                  f"TRIGGER:{trig}", "END:VALARM"]
    lines += ["END:VEVENT", "END:VCALENDAR"]
    path = os.path.join(ROOT, cal_id, uid + ".ics")
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as f:
        f.write("\r\n".join(_fold(l) for l in lines) + "\r\n")
    os.replace(tmp, path)
    sync()
    return path


def delete(occ):
    try:
        os.unlink(occ.event.path)
    except OSError:
        return False
    sync()
    return True


def sync():
    subprocess.Popen(["systemctl", "--user", "start", "--no-block", "vdirsyncer.service"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------- words
DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
DAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]
MONTHS_SHORT = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt",
                "Nov", "Dez"]


def day_name(d, today=None):
    today = today or now().date()
    delta = (d - today).days
    names = {0: "Heute", 1: "Morgen", 2: "Übermorgen", -1: "Gestern"}
    if delta in names:
        return names[delta]
    return DAYS[d.weekday()]


def date_text(d, year=False):
    s = f"{DAYS_SHORT[d.weekday()]} {d.day}. {MONTHS_SHORT[d.month - 1]}"
    return s + (f" {d.year}" if year else "")


def until_text(t, ref=None):
    """'in 5 Min', 'in 2 Std', 'in 3 Tagen', 'jetzt'"""
    ref = ref or now()
    mins = round((t - ref).total_seconds() / 60)
    if mins <= 0:
        return "jetzt"
    if mins < 60:
        return f"in {mins} Min"
    if mins < 60 * 24:
        h, m = divmod(mins, 60)
        if h < 3 and m >= 10:
            return f"in {h}:{m:02d} Std"
        return f"in {round(mins / 60)} Std"
    days = (t.date() - ref.date()).days
    return "morgen" if days == 1 else f"in {days} Tagen"


def left_text(t, ref=None):
    """'noch 40 Min' for a running event"""
    ref = ref or now()
    mins = max(1, round((t - ref).total_seconds() / 60))
    if mins < 60:
        return f"noch {mins} Min"
    h, m = divmod(mins, 60)
    return f"noch {h}:{m:02d} Std"
