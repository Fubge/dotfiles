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
side never imports GTK, so it starts fast. Still, a Python client costs ~80 ms
per press (interpreter, imports, compiling the whole script: executables without
.py get no bytecode cache). Key binds and bar clicks therefore go through the
bash client ~/.local/bin/popup-cmd (~5 ms), which writes the command into the
FIFO $XDG_RUNTIME_DIR/popup-cmd/<script>.fifo (next to <script>.pid) and only
runs the script itself when no server is running.

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

Every show is a little entrance, the same in all popups (style: popups/style.css):
the title (class menu-title) types itself with an orange caret, like the lock
screen greeting, and the rows slide in one after the other. animate_in() numbers
the row-like widgets in order (classes in-0..in-11) and sets class "enter" on
the window for ENTER_MS; rows built later while it is open do not animate.
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
ENTER_MS = 700      # how long the entrance animations may run
TYPE_MS = 45        # title typing speed per character
BLINK_MS = 530      # caret blink, as the lock screen
BLINKS = 3          # caret blinks after typing, then it goes away
# widgets that slide in on their own (their children move with them)
ROW_CLASSES = ("sound-row", "slider-row", "item-card", "section", "note", "app-name",
               "segment", "battery", "more", "pet-card", "sound-sep", "menu-search",
               "menu-info", "card")


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


def animate_in(win):
    """Entrance: number the rows (staggered slide-in), type the title."""
    from gi.repository import GLib, Gtk

    count = 0

    def walk(w):
        nonlocal count
        while w is not None:
            for c in w.get_css_classes():
                if c.startswith("in-"):
                    w.remove_css_class(c)
            if w.get_visible() and (isinstance(w, Gtk.ListBoxRow)
                                    or any(w.has_css_class(c) for c in ROW_CLASSES)):
                w.add_css_class(f"in-{min(count, 11)}")
                count += 1
            elif w.has_css_class("menu-title") and isinstance(w, Gtk.Label):
                type_title(w)
            else:
                walk(w.get_first_child())
            w = w.get_next_sibling()

    walk(win.get_child())
    if getattr(win, "enter_timer", None):
        GLib.source_remove(win.enter_timer)

    def start():
        win.add_css_class("enter")
        win.enter_timer = GLib.timeout_add(ENTER_MS, stop)
        return False

    def stop():
        win.remove_css_class("enter")
        win.enter_timer = None
        return False

    if not win.has_css_class("enter"):
        # usual case (shown from hidden): start before the first frame, so the
        # rows never flash in their end position
        start()
    else:
        # still running (shown again quickly): restart it after one frame
        win.remove_css_class("enter")
        GLib.timeout_add(16, start)


def type_title(label, caret_color=None, step_ms=TYPE_MS):
    """Type the label's text with a caret (in its own color unless given),
    blink, done. Notifications pass the accent caret and a faster pace."""
    from gi.repository import GLib

    if getattr(label, "type_timer", None):
        GLib.source_remove(label.type_timer)
    text = label.get_text()
    if "\u258d" in text:         # still our markup (maybe cut short): the stored title
        text = label.full_text
    label.full_text = text
    if caret_color is None:
        color = label.get_color()
        caret_color = "#%02x%02x%02x" % tuple(round(c * 255) for c in
                                              (color.red, color.green, color.blue))
    start = GLib.get_monotonic_time()
    esc = GLib.markup_escape_text

    def tick():
        ms = (GLib.get_monotonic_time() - start) // 1000
        typed = min(len(text), ms // step_ms)
        after = ms - len(text) * step_ms
        done = after > BLINKS * 2 * BLINK_MS
        on = not done and (after < 0 or (after // BLINK_MS) % 2 == 0)
        # the untyped rest is drawn invisibly: the centered title does not move
        label.set_markup(esc(text[:typed])
                         + f'<span foreground="{caret_color}" alpha="{100 if on else 1}%">\u258d</span>'
                         + f'<span alpha="1%">{esc(text[typed:])}</span>')
        if done:              # the caret stays, invisible: the title does not shift
            label.type_timer = None
        return not done
    tick()
    label.type_timer = GLib.timeout_add(30, tick)


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
    from gi.repository import GLib, Gtk

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
        animate_in(win)
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

    def handle(line):
        cmd, *opts = line.split() or [""]
        center = "--center" in opts
        if cmd == "show":
            show_up(center)
        elif cmd == "toggle":
            win.close() if win.get_visible() else show_up(center)
        elif cmd == "quit":
            loop.quit()

    def on_cmd(*_a):
        handle(sock.recv(64).decode())
        return True
    GLib.io_add_watch(sock.fileno(), GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN, on_cmd)

    # FIFO for ~/.local/bin/popup-cmd. Opened read-write: a writer always
    # exists, so it never reports EOF, and nothing blocks while we run
    fifo_dir = os.path.join(RUN, "popup-cmd")
    os.makedirs(fifo_dir, exist_ok=True)
    base = os.path.join(fifo_dir, os.path.basename(sys.argv[0]))
    try:
        os.unlink(base + ".fifo")
    except OSError:
        pass
    os.mkfifo(base + ".fifo", 0o600)
    fifo = os.open(base + ".fifo", os.O_RDWR | os.O_NONBLOCK)
    with open(base + ".pid", "w") as f:
        f.write(str(os.getpid()))
    pending = [b""]

    def on_fifo(*_a):
        try:
            pending[0] += os.read(fifo, 4096)
        except BlockingIOError:
            return True
        *lines, pending[0] = pending[0].split(b"\n")
        for line in lines:
            handle(line.decode(errors="replace"))
        return True
    GLib.io_add_watch(fifo, GLib.PRIORITY_DEFAULT, GLib.IOCondition.IN, on_fifo)

    if show:
        show_up()
    else:
        # warm up while hidden: CSS, layout and fonts of the first show would
        # otherwise cost ~80 ms on the first press after login
        def warm_up():
            if not win.get_visible():
                win.realize()
                child = win.get_child()
                if child:
                    child.measure(Gtk.Orientation.VERTICAL, getattr(win, "popup_width", -1))
            return False
        GLib.idle_add(warm_up)
    loop.run()
    for p in (path, base + ".fifo", base + ".pid"):
        try:
            os.unlink(p)
        except OSError:
            pass


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
