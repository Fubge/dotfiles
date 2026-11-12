"""Resident GTK popups: start once, then only hide and show the window.

Starting Python + GTK costs ~0.5 s per click; showing a hidden window is
instant. A popup script calls main() with its window class and a build()
function; the same script then works as server and as client:

    SCRIPT            run and show the window (or show the running one)
    SCRIPT --hidden   run in the background (login autostart, hypr/vars.lua)
    SCRIPT show       show the running popup (starts one if there is none)
    SCRIPT toggle     show it, or hide it when it is open (bar icon clicks)
    SCRIPT quit       stop the running popup (e.g. after its code changed)

Commands go over a datagram socket $XDG_RUNTIME_DIR/<class>.sock. The client
side never imports GTK, so it starts fast.

build() runs in the server after GTK is loaded and returns a Gtk.Window with a
show_up() method (refresh its content, then present()). Closing only hides the
window (Hyprland closes bar popups when focus leaves), so it can come back.
While it is shown, waybar tooltips are off (~/.local/bin/bar-tooltips) and an
open rofi menu is closed: only one menu at a time, like ~/.local/bin/popup.
Plain Gtk.Window, no Gtk.Application: registering that on D-Bus costs ~0.6 s.
"""
import os
import socket
import subprocess
import sys

RUN = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
BAR_TOOLTIPS = os.path.expanduser("~/.local/bin/bar-tooltips")


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

    def show_up():
        subprocess.Popen([BAR_TOOLTIPS, "off", tag])
        subprocess.run(["pkill", "-x", "rofi"])
        win.show_up()

    loop = GLib.MainLoop()
    path = sock_path(app_id)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        os.unlink(path)
    except OSError:
        pass
    sock.bind(path)

    def on_cmd(*_a):
        cmd = sock.recv(64).decode().strip()
        if cmd == "show":
            show_up()
        elif cmd == "toggle":
            win.close() if win.get_visible() else show_up()
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
    if args in (["show"], ["toggle"]):
        if not send(app_id, args[0]):
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
