"""Shared bits of the notification daemon (~/.local/bin/notifications) and the
notification center (~/.local/bin/notification-center): app icons, glyphs,
text helpers, where the history lives and the daemon's own D-Bus interface.

Icons: apps get their real icon from the icon theme (Papirus-Dark, like the
launcher), found through the desktop entry the app names or its own name.
System messages (battery, Wi-Fi, volume...) and apps without an icon get a
Nerd Font glyph on a rounded square in a palette color instead.
"""
import html
import os
import re
import time

STATE = os.path.join(os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
                     "notifications")
HISTORY = os.path.join(STATE, "history.json")       # {"dnd", "read_at", "items": [...]}
IMAGES = os.path.join(STATE, "images")              # <id>.png: pictures for the center
BAR_STATUS = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "notifications.status")

NAME = "org.freedesktop.Notifications"
PATH = "/org/freedesktop/Notifications"
CENTER_IFACE = "dotfiles.Notifications.Center"
CENTER_XML = """<node><interface name="dotfiles.Notifications.Center">
  <method name="Get"><arg type="s" direction="out"/></method>
  <method name="Remove"><arg type="u" direction="in"/></method>
  <method name="Clear"/>
  <method name="SetDnd"><arg type="b" direction="in"/></method>
  <method name="ToggleDnd"/>
  <method name="MarkRead"/>
  <method name="Invoke"><arg type="u" direction="in"/></method>
  <signal name="Changed"/>
</interface></node>"""

# Nerd Font glyphs (Material Design), written as escapes: editors drop them
G = {
    "discord": "\U000F066F", "spotify": "\U000F04C7", "steam": "\U000F04D3",
    "gamepad": "\U000F0297", "robot": "\U000F06A9", "wifi": "\U000F05A9",
    "bluetooth": "\U000F00AF", "images": "\U000F02F9", "web": "\U000F059F",
    "youtube": "\U000F05C3", "volume": "\U000F057E", "brightness": "\U000F00DF",
    "battery": "\U000F0079", "mail": "\U000F01EE", "download": "\U000F01DA",
    "console": "\U000F018D", "package": "\U000F03D6", "message": "\U000F0369",
    "camera": "\U000F0100", "usb": "\U000F0553", "calendar": "\U000F00ED",
    "clock": "\U000F0954", "update": "\U000F06B0", "music": "\U000F075A",
    "lock": "\U000F033E", "keyboard": "\U000F030C", "cog": "\U000F0493",
    "bell": "\U000F009A", "bell-outline": "\U000F009C", "bell-off": "\U000F009B",
    "bell-sleep": "\U000F00A0", "bell-sleep-outline": "\U000F0A93",
    "bell-ring": "\U000F009E", "bell-badge": "\U000F116B", "alert": "\U000F0026", "close": "\U000F0156",
    "check": "\U000F05E0", "delete": "\U000F0A7A",
}
# (words in app name / desktop entry / icon name, glyph, palette color, system)
# first match wins; system = always the glyph (no app icon fits a battery
# warning), the others try the app's real icon first
APPS = [
    (("claude",), "robot", "accent", True),
    (("wi-fi", "wifi", "wireless", "network", "nm-applet"), "wifi", "blue", True),
    (("bluetooth", "blueman"), "bluetooth", "cyan", True),
    (("wallpaper",), "images", "yellow", True),
    (("volume", "audio", "sound", "pipewire", "pulse"), "volume", "accent", True),
    (("bright", "backlight"), "brightness", "yellow", True),
    (("battery", "upower", "power"), "battery", "green", True),
    (("gamemode",), "gamepad", "magenta", True),
    (("screenshot", "grim"), "camera", "cyan", True),
    (("usb", "udisk", "drive", "mount"), "usb", "cyan", True),
    (("timer", "clock", "alarm"), "clock", "yellow", True),
    (("lock",), "lock", "slate", True),
    (("update", "pacman", "package"), "package", "magenta", True),
    (("discord", "vesktop", "webcord"), "discord", "blue", False),
    (("spotify",), "spotify", "green", False),
    (("steam",), "steam", "cyan", False),
    (("game", "lutris", "heroic"), "gamepad", "magenta", False),
    (("youtube",), "youtube", "red", False),
    (("vivaldi", "firefox", "chrom", "browser", "web"), "web", "accent", False),
    (("mail", "thunderbird"), "mail", "blue", False),
    (("download", "transmission", "qbittorrent"), "download", "green", False),
    (("camera",), "camera", "cyan", False),
    (("calendar",), "calendar", "blue", False),
    (("music", "mpd", "player"), "music", "green", False),
    (("terminal", "kitty", "console", "shell"), "console", "slate", False),
    (("message", "chat", "telegram", "signal", "element"), "message", "blue", False),
    (("settings", "config"), "cog", "slate", False),
]
# icon names apps send that say nothing about the app
GENERIC_ICONS = ("dialog-", "utilities-", "notification", "emblem-", "user-", "mail-",
                 "appointment-", "audio-", "battery", "network-", "media-", "preferences-")


def pick(app, entry="", icon=""):
    """Glyph, palette color and system flag for an app."""
    text = " ".join(n.lower() for n in (app, entry, icon) if n and not n.startswith("/"))
    for words, glyph, color, system in APPS:
        if any(w in text for w in words):
            return G[glyph], color, system
    return G["bell"], "accent", False


_icon_cache = {}


def app_gicon(app, entry="", icon=""):
    """The app's real icon (a Gio.Icon the icon theme has), or None."""
    key = (app, entry, icon)
    if key in _icon_cache:
        return _icon_cache[key]
    from gi.repository import Gdk, Gio, Gtk

    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

    def usable(gicon):
        if gicon is None:
            return None
        if isinstance(gicon, Gio.ThemedIcon):
            return gicon if any(theme.has_icon(n) for n in gicon.get_names()) else None
        if isinstance(gicon, Gio.FileIcon):
            return gicon if gicon.get_file().query_exists() else None
        return None

    def desktop(name):
        for n in (name, name.lower(), name.lower().replace(" ", "-")):
            try:
                info = Gio.DesktopAppInfo.new(n + ".desktop")
            except TypeError:
                info = None
            if info:
                found = usable(info.get_icon())
                if found:
                    return found
        return None

    found = None
    names = [n for n in (entry, app) if n]
    for n in names:
        found = desktop(n)
        if found:
            break
    if not found:
        for n in names:
            for cand in (n.lower(), n.lower().replace(" ", "-")):
                if theme.has_icon(cand):
                    found = Gio.ThemedIcon.new(cand)
                    break
            if found:
                break
    if not found and icon and not icon.startswith(("/", "file://")) \
            and not icon.startswith(GENERIC_ICONS) and theme.has_icon(icon):
        found = Gio.ThemedIcon.new(icon)
    if not found and len(app) >= 3:
        # "Spotify" -> spotify-launcher.desktop: only when the app's name is in it
        for group in Gio.DesktopAppInfo.search(app):
            for desktop_id in group[:1]:
                info = Gio.DesktopAppInfo.new(desktop_id)
                if info and app.lower() in (info.get_name() or "").lower():
                    found = usable(info.get_icon())
            if found or group:
                break
    _icon_cache[key] = found
    return found


def icon_widget(app, entry="", icon="", urgency=1, size=24, css="notif-icon"):
    """Real app icon, or the glyph on a rounded square. Returns the widget."""
    from gi.repository import Gtk

    glyph, color, system = pick(app, entry, icon)
    if urgency >= 2:
        color = "red"
        if glyph == G["bell"]:
            glyph = G["alert"]
    gicon = None if system or urgency >= 2 else app_gicon(app, entry, icon)
    if gicon:
        img = Gtk.Image(gicon=gicon, pixel_size=size, css_classes=[css, "app"],
                        valign=Gtk.Align.CENTER)
        return img
    return Gtk.Label(label=glyph, css_classes=[css, "tint-" + color], valign=Gtk.Align.CENTER)


def body_markup(text):
    """The spec's small markup subset for Pango: keep <b> <i> <u>, links
    become their text, other tags go, everything else is escaped."""
    out = []
    for part in re.split(r"(<[^>]*>)", text):
        if re.fullmatch(r"</?[biu]>", part):
            out.append(part)
        elif not (part.startswith("<") and part.endswith(">")):
            out.append(html.escape(html.unescape(part), quote=False))
    return "".join(out).strip()


def plain(text):
    """Body without markup (for one-line previews)."""
    return html.unescape(re.sub(r"<[^>]*>", "", text)).strip()


def age_text(when, now=None):
    seconds = (now or time.time()) - when
    m = int(seconds // 60)
    if m < 1:
        return "now"
    if m < 60:
        return f"{m} min"
    if m < 24 * 60:
        return f"{m // 60} h"
    return time.strftime("%d.%m.", time.localtime(when))


def day_label(when, now=None):
    """Section of the center: Today, Yesterday, Earlier."""
    now = now or time.time()
    today = time.localtime(now)
    midnight = time.mktime((today.tm_year, today.tm_mon, today.tm_mday, 0, 0, 0, 0, 0, -1))
    if when >= midnight:
        return "Today"
    if when >= midnight - 86400:
        return "Yesterday"
    return "Earlier"
