"""Resident GTK popups: start once, then only hide and show the window.

Starting Python + GTK costs ~0.5 s per click; showing a hidden window is
instant. A popup script calls main() with its window class and a build()
function; the same script then works as server and as client:

    SCRIPT                  run and show the window (or show the running one)
    SCRIPT --hidden         run in the background (login autostart, hypr/vars.lua)
    SCRIPT show [--center]  show the running popup (starts one if there is none)
    SCRIPT toggle [--center]  show it, or hide it when it is open (bar icon clicks)
    SCRIPT quit             stop the running popup (e.g. after its code changed)

Commands go over a datagram socket $XDG_RUNTIME_DIR/<class>.sock. The client
side never imports GTK, so it starts fast.

build() runs in the server after GTK is loaded and returns a Gtk.Window with a
show_up() method (refresh its content, then present()). Closing only hides the
window (Hyprland closes bar popups when focus leaves), so it can come back.
While it is shown, waybar tooltips are off (~/.local/bin/bar-tooltips) and an
open rofi menu is closed: only one menu at a time, like ~/.local/bin/popup.
Plain Gtk.Window, no Gtk.Application: registering that on D-Bus costs ~0.6 s.

Position: a window with a `popup_width` attribute is placed by place() on
every show: centered under the mouse just below the bar (--center: in the
middle of the screen). When its content grows or shrinks while it is open,
keep_top() keeps it below the bar. Others keep their static rule (hypr/rules.lua).
The server sets win.bring_up(center=False) for windows that show themselves
(the list menu shows up on a request, not on a command).
"""
import json
import os
import signal
import socket
import subprocess
import sys

RUN = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
BAR_TOOLTIPS = os.path.expanduser("~/.local/bin/bar-tooltips")
HYPR_SOCK = os.path.join(RUN, "hypr", os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", ""),
                         ".socket.sock")
POPUP_TOP = 46      # just below the bar, as hypr/vars.lua M.popup.top
EDGE = 16           # min distance to the screen edges


def sock_path(app_id):
    return os.path.join(RUN, app_id + ".sock")


def send(app_id, cmd):
    """Send a command to the running popup; False if none is running."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.sendto(cmd.encode(), sock_path(app_id))
        return True
    except OSError:
        return False


def hypr(request):
    """One request to Hyprland's IPC socket ("j/cursorpos", "eval ..."): what
    hyprctl does, without starting a process (~0.3 ms instead of ~15 ms)."""
    try:
        with socket.socket(socket.AF_UNIX) as s:
            s.connect(HYPR_SOCK)
            s.sendall(request.encode())
            data = b""
            while chunk := s.recv(65536):
                data += chunk
        return data.decode()
    except OSError:
        return ""


def place(app_id, width, center=False, x=None, at=None):
    """Set where the window shows up next, through a named window rule
    "<app_id>-at" (a re-shown window gets its rules again). Bar popups sit just
    below the bar, centered under the mouse (or under x, or `at` px right of
    the screen's middle) and EDGE px away from the screen sides; center=True
    puts it in the middle of the screen. Returns the left edge (for x=)."""
    try:
        mon = next(m for m in json.loads(hypr("j/monitors")) if m["focused"])
        mw = int(mon["width"] / mon["scale"])
        cx = json.loads(hypr("j/cursorpos"))["x"] - mon["x"]
    except (ValueError, StopIteration, KeyError):
        return None
    if center or at is not None:
        cx = mw // 2 + (at or 0)
    left = x if x is not None else max(EDGE, min(cx - width // 2, mw - width - EDGE))
    top = "monitor_h*0.5-window_h*0.5" if center else str(POPUP_TOP)
    cls = "^" + app_id.replace(".", "\\\\.") + "$"
    hypr("eval hl.window_rule({ name = '%s-at', match = { class = '%s' }, "
         "float = true, pin = true, move = { '%d', '%s' } })" % (app_id, cls, left, top))
    PLACED[app_id] = None if center else (mon["x"] + left, mon["y"] + POPUP_TOP)
    return left


PLACED = {}     # app_id -> global (x, y) of a bar popup's top left corner


def keep_top(app_id):
    """Hyprland grows and shrinks a floating window around its middle, so a bar
    popup whose content grows would slide up behind the bar: put it back."""
    at = PLACED.get(app_id)
    if at:
        hypr('dispatch hl.dsp.window.move({ window = "class:%s", x = %d, y = %d })'
             % (app_id, *at))


def close_rofi():
    """Close an open rofi (launcher, clipboard...). Its pid file, not pkill:
    pgrep/pkill scan all of /proc (~50 ms)."""
    try:
        pid = int(open(os.path.join(RUN, "rofi.pid")).read())
        if open(f"/proc/{pid}/comm").read().strip() == "rofi":
            os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError):
        pass


def serve(app_id, build, show):
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib

    GLib.set_prgname(app_id)       # Wayland app id = window class for Hyprland
    win = build()
    win.set_hide_on_close(True)
    tag = str(os.getpid())

    def visible_changed(*_a):
        if not win.get_visible():
            subprocess.Popen([BAR_TOOLTIPS, "on", tag])
    win.connect("notify::visible", visible_changed)

    def show_up(center=False):
        subprocess.Popen([BAR_TOOLTIPS, "off", tag])
        close_rofi()
        if hasattr(win, "popup_width"):
            place(app_id, win.popup_width, center=center)
        win.show_up()
        surface = win.get_surface()
        if surface and not getattr(win, "keeps_top", False):
            win.keeps_top = True
            last = [None]

            def on_layout(_s, _w, height):
                if height != last[0]:
                    if last[0] is not None and win.get_visible():
                        # after Hyprland got the new size (it re-centers then)
                        GLib.timeout_add(40, lambda: keep_top(app_id) and False)
                    last[0] = height
            surface.connect("layout", on_layout)
    win.bring_up = show_up

    loop = GLib.MainLoop()
    path = sock_path(app_id)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        os.unlink(path)
    except OSError:
        pass
    sock.bind(path)

    def on_cmd(*_a):
        cmd, *opts = sock.recv(64).decode().split() or [""]
        center = "--center" in opts
        if cmd == "show":
            show_up(center)
        elif cmd == "toggle":
            win.close() if win.get_visible() else show_up(center)
        elif cmd == "quit":
            loop.quit()
        return True
    GLib.io_add_watch(sock.fileno(), GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN, on_cmd)
    if show:
        show_up()
    loop.run()
    os.unlink(path)


def main(app_id, build, usage):
    args = sys.argv[1:]
    if args[:1] in (["show"], ["toggle"]) and args[1:] in ([], ["--center"]):
        if not send(app_id, " ".join(args)):
            serve(app_id, build, show=True)
    elif args == ["quit"]:
        send(app_id, "quit")
    elif args in ([], ["--hidden"]):
        if send(app_id, "ping"):          # already running
            if not args:
                send(app_id, "show")
            return
        serve(app_id, build, show=not args)
    else:
        sys.exit(usage)
