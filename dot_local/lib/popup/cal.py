"""Shared calendar bits: the two Nextcloud calendars that vdirsyncer keeps in
~/.local/share/calendars (one folder per calendar, one .ics per event, plus
`displayname` and `color` files). Used by the calendar popup, the quick-add
popup and the reminder daemon.

    cal.calendars()              -> [Calendar], own calendar first
    cal.occurrences(a, b)        -> [Occurrence] overlapping [a, b) (datetimes)
    cal.day(d)                   -> [Occurrence] on date d, all-day first
    cal.add(cal_id, title, start, end, allday, location, alarm)
    cal.delete(occurrence)       -> removes the event (a series: all of it)
    cal.update(occurrence, ...)  -> change title / times / place / alarm / calendar
    cal.shift(occurrence, days)  -> move it (drag and drop)
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

from i18n import T, Tn

ROOT = os.path.expanduser("~/.local/share/calendars")
OWN = "the-preu-plans-1"            # Flauschebär: the user's own calendar
# short names, glyphs and colors per calendar (Nextcloud's names are long).
# Color None: the one set in Nextcloud. Flauschebär's Nextcloud blue melted into
# the dark blue-grey desktop, so here it is lavender (Nextcloud keeps its blue).
PEOPLE = {
    "the-preu-plans-1": ("Flauschebär", "\U000F18FB", "#c3a6ff"),   # teddy bear
    "the-preu-plans": ("Pia", "\U000F02D1", None),                  # heart
}


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
        self.name, self.glyph, color = PEOPLE.get(cid, (name.split(" - ")[-1], "\U000F00ED", None))
        self.color = (color or _read(os.path.join(self.path, "color")) or "#7aa2f7")[:7]
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
            e.summary = T("cal.untitled")
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
        base = self.bounds()[0]
        for a in self.event.alarms:     # no VALARM, no reminder
            out.append(a + base if isinstance(a, dt.timedelta) else a)
        return out

    def time_text(self):
        if self.allday:
            days = (self.end - self.start).days
            return T("cal.allday") if days <= 1 else Tn("cal.days", days)
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
        lines += _alarm_lines(alarm)
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


def find(uid, start_iso):
    """the occurrence of event uid starting at start_iso (from an --edit option)"""
    try:
        when = dt.datetime.fromisoformat(start_iso)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=TZ)
    for o in occurrences(when - dt.timedelta(days=1), when + dt.timedelta(days=2)):
        if o.event.uid == uid and o.bounds()[0] == when:
            return o
    return None


def _when_lines(name, t, allday, tzid):
    if allday:
        return [f"{name};VALUE=DATE:{t:%Y%m%d}"]
    if tzid:
        return [f"{name};TZID={tzid}:{t.astimezone(ZoneInfo(tzid)):%Y%m%dT%H%M%S}"]
    return [f"{name}:{_utc(t)}"]


def _alarm_lines(alarm):
    secs = int(alarm.total_seconds())
    sign, secs = ("-" if secs < 0 else ""), abs(secs)
    d, rest = divmod(secs, 86400)
    h, rest = divmod(rest, 3600)
    m = rest // 60
    trig = f"{sign}P" + (f"{d}D" if d else "") + (
        "T" + (f"{h}H" if h else "") + (f"{m}M" if m else "") if (h or m) else "")
    if trig.endswith("P"):
        trig += "T0S"
    return ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Reminder", f"TRIGGER:{trig}",
            "END:VALARM"]


def update(occ, title=None, start=None, end=None, allday=None, location=None,
           alarm=..., cal_id=None):
    """Change an event in place, keeping everything else in its file (UID,
    Apple fields, other overrides). start/end are the new times of THIS
    occurrence; a series moves along by the same amount (like "all events" in
    Google). alarm=... keeps the alarms, None removes them. cal_id moves the
    file to the other calendar. Writes, then syncs."""
    ev = occ.event
    try:
        with open(ev.path, encoding="utf-8") as f:
            lines = _unfold(f.read())
    except OSError:
        return False
    if start is None:
        start, end = occ.start, occ.end
    if allday is None:
        allday = not isinstance(start, dt.datetime)
    delta_start = None
    if not ev.rrule:
        new_start, new_end = start, end
    else:
        # the series' first start moves by as much as this occurrence did
        o0 = occ.bounds()[0]
        n0 = start if not allday else dt.datetime.combine(start, dt.time(), TZ)
        delta_start = n0 - o0
        m0 = ev.start if isinstance(ev.start, dt.datetime) else dt.datetime.combine(ev.start, dt.time(), TZ)
        m0 = m0 + delta_start
        new_start = m0.date() if allday else m0
        new_end = new_start + (end - start)
    out, i, in_master, in_alarm, done = [], 0, False, False, False
    stamp = _utc(now())
    for line in lines:
        name, params, value = _prop(line)
        if name == "BEGIN" and value.upper() == "VEVENT":
            in_master = True
            master_lines = []
            out.append(line)
            continue
        if not in_master:
            out.append(line)
            continue
        if name == "BEGIN" and value.upper() == "VALARM":
            in_alarm = True
        if in_alarm:
            if name == "END" and value.upper() == "VALARM":
                in_alarm = False
            if alarm is ...:
                master_lines.append(line)
            continue
        if name == "END" and value.upper() == "VEVENT":
            # an override (RECURRENCE-ID) stays untouched
            if any(_prop(l)[0] == "RECURRENCE-ID" for l in master_lines):
                out.extend(master_lines + [line])
                in_master = False
                continue
            tzid = next((_prop(l)[1].get("TZID") for l in master_lines
                         if _prop(l)[0] == "DTSTART"), None)
            if tzid and not any(l.startswith("TZID:" + tzid) for l in lines):
                tzid = None          # no VTIMEZONE for it in the file: write UTC
            keep = []
            seq = 1      # no SEQUENCE yet: this is the first change
            for l in master_lines:
                n = _prop(l)[0]
                if n in ("DTSTART", "DTEND", "DURATION", "DTSTAMP", "LAST-MODIFIED"):
                    continue
                if n == "SEQUENCE":
                    try:
                        seq = int(_prop(l)[2]) + 1
                    except ValueError:
                        seq = 1
                    continue
                if n == "SUMMARY" and title is not None:
                    continue
                if n == "LOCATION" and location is not None:
                    continue
                if n == "TRANSP":
                    continue
                if n == "RRULE" and allday != ev.allday:
                    # UNTIL must match the new value type
                    l = "RRULE:" + _rule_text(_prop(l)[2], new_start)
                keep.append(l)
            new = [f"DTSTAMP:{stamp}", f"LAST-MODIFIED:{stamp}", f"SEQUENCE:{seq}"]
            new += _when_lines("DTSTART", new_start, allday, tzid)
            new += _when_lines("DTEND", new_end, allday, tzid)
            new.append("TRANSP:" + ("TRANSPARENT" if allday else "OPAQUE"))
            if title is not None:
                new.append("SUMMARY:" + _esc(title))
            if location:
                new.append("LOCATION:" + _esc(location))
            alarms = []
            if alarm is not ... and alarm is not None:
                alarms = _alarm_lines(alarm)
            # alarms kept (alarm=...) are still in keep, in their place
            out.extend(new + keep + alarms + [line])
            in_master = False
            done = True
            continue
        master_lines.append(line)
    if not done:
        return False
    target = ev.path
    if cal_id and cal_id != ev.cal.id:
        target = os.path.join(ROOT, cal_id, os.path.basename(ev.path))
    tmp = target + ".tmp"
    with open(tmp, "w", newline="") as f:
        f.write("\r\n".join(_fold(l) for l in out) + "\r\n")
    os.replace(tmp, target)
    if target != ev.path:
        try:
            os.unlink(ev.path)
        except OSError:
            pass
    sync()
    return True


def shift(occ, days):
    """Move an event by whole days (drag and drop in the month), same times."""
    d = dt.timedelta(days=days)
    return update(occ, start=occ.start + d, end=occ.end + d)


def sync():
    subprocess.Popen(["systemctl", "--user", "start", "--no-block", "vdirsyncer.service"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------- words
DAYS = T("cal.weekdays")
DAYS_SHORT = T("cal.weekdays_short")
MONTHS = T("cal.months")
MONTHS_SHORT = T("cal.months_short")


def day_name(d, today=None):
    today = today or now().date()
    delta = (d - today).days
    names = {0: T("cal.today"), 1: T("cal.tomorrow"), 2: T("cal.day_after"), -1: T("cal.yesterday")}
    if delta in names:
        return names[delta]
    return DAYS[d.weekday()]


def date_text(d, year=False):
    s = T("cal.date", wd=DAYS_SHORT[d.weekday()], d=d.day, mon=MONTHS_SHORT[d.month - 1])
    return s + (f" {d.year}" if year else "")


def until_text(t, ref=None):
    """'in 5 Min', 'in 2 Std', 'in 3 Tagen', 'jetzt'"""
    ref = ref or now()
    mins = round((t - ref).total_seconds() / 60)
    if mins <= 0:
        return T("cal.now")
    if mins < 60:
        return T("cal.in_min", n=mins)
    if mins < 60 * 24:
        h, m = divmod(mins, 60)
        if h < 3 and m >= 10:
            return T("cal.in_hm", h=h, m=f"{m:02d}")
        return T("cal.in_h", n=round(mins / 60))
    days = (t.date() - ref.date()).days
    return T("cal.tomorrow_lc") if days == 1 else T("cal.in_days", n=days)


def left_text(t, ref=None):
    """'noch 40 Min' for a running event"""
    ref = ref or now()
    mins = max(1, round((t - ref).total_seconds() / 60))
    if mins < 60:
        return T("cal.left_min", n=mins)
    h, m = divmod(mins, 60)
    return T("cal.left_hm", h=h, m=f"{m:02d}")
