#!/usr/bin/env python3
"""The bar pet: a tiny pixel critter that lives in waybar (custom/claude) and
acts out what Claude is doing.

Three pets, picked in the pet picker (claude-pad menu -> ~/.local/bin/pet-picker):
  mochi   peach fluffball with a little orange star (the Claude sparkle)
  kitty   round blue-grey kitten loaf
  bunny   lavender bunny with long ears, nibbles carrots

Everything is drawn here as code (round silhouettes from row spans, an outline
around them, then face and props on top). The pet is kept small and the props
big and outlined, so what it does reads at bar size. `build` renders every
frame of every animation to PNG and writes a CSS file with one class per
frame; the bar daemon (claude-pad watch) only switches classes.

    pet.py build DIR      frames to DIR/frames, DIR/pet.css, DIR/anims.json
    pet.py sheet FILE     contact sheet of all frames (for design work)

One art pixel = 3 device pixels = 1.5 logical pixels at scale 2. The @2 image
is used 1:1 (crisp), the plain one is only there for scale 1 setups.
"""
import hashlib
import json
import math
import os
import sys

W, H = 40, 20            # canvas in art pixels (60 x 30 logical = bar height)
SCALE = 3                # device pixels per art pixel in the @2 image
GROUND = 17              # feet row: shadow on row 18, one free row below; all the room
                         # above is for jumps, raised tools and rising Zs
TOP_SAFE = 1             # row 0 is the edge of the bar pill: nothing may be drawn there
CX = 9                   # where the pet stands (center column)
MIN_COLS = 18            # the module is as wide as each animation needs (columns
                         # it really uses, at least this), so the window title sits
                         # close to the pet and only moves over for props

# ---------------------------------------------------------------- colors
PROP = {
    "eye": "#2a2433", "shine": "#ffffff", "blush": "#ff9eb0", "tongue": "#e0607a",
    "z": "#a8e0ff", "think": "#f8f8f2",
    "confetti": ["#ff7f00", "#8fe3ff", "#ffdd99", "#c49bff", "#a6e3a1", "#ff9eb0"],
    "spark": "#ffdd66", "chip": "#c3c9d8",
}
# letters used in the prop grids below
PROP_COLORS = {
    "k": "#252a3d",                                  # prop outline
    "m": "#e4e8f2", "M": "#a9b1c6",                  # pick metal, shade
    "w": "#c08a58",                                  # wood
    "r": "#8a92a6", "R": "#b3bacb", "d": "#646b80",  # rock, light, dark
    "L": "#c3c9d8", "l": "#8a92a6", "S": "#8fe3ff",  # laptop, dark, screen glow
    "g": "#8fe3ff", "G": "#ffffff", "D": "#4fa6d6",  # gem
    "y": "#ffdd66", "Y": "#fff6cc", "s": "#8a92a6",  # bulb, socket
    "b": "#ff7f00",                                  # "!"
    "z": PROP["z"], "t": PROP["think"],
    "o": "#ff8a3d", "O": "#d9622b", "f": "#7bd88f",  # carrot, shade, leaves
    "B": "#ffb3dc", "p": "#ffe3f2", "q": "#6a3a66",  # butterfly wing, light, body
    "h": "#ff7aa8", "H": "#ffc2d8",                  # heart, shine
}
BALLS = [("#ff8a3d", "#ffd0a8"), ("#8fe3ff", "#e6f9ff"), ("#ff9eb0", "#ffe0e7")]   # color, shine
SOFT_LINE = {"butterfly": "#8a3f73", "heart": "#9c3557"}   # outlines not as hard as "k"

PETS = {
    "mochi": dict(hi="#fff4e6", mid="#ffd8b5", shade="#f3b48a", line="#9c5a3c",
                  mouth="#7a3b2e", star="#ff7f00", star_hi="#ffdd99", star_off="#c98a63"),
    "kitty": dict(hi="#f3f5fa", mid="#d6dcea", shade="#adb6cd", line="#454b63",
                  mouth="#454b63", ear="#ffb3c2"),
    "bunny": dict(hi="#faf6ff", mid="#ddd0f4", shade="#b7a2de", line="#5a4880",
                  mouth="#5a4880", ear="#ffb3c2", nose="#ff8fa8"),
}
NAMES = {"mochi": "Mochi", "kitty": "Kitty", "bunny": "Bunny"}


# ---------------------------------------------------------------- canvas
def blend(under, over):
    a = int(over[7:9], 16) / 255
    mix = [round(int(under[i:i + 2], 16) * (1 - a) + int(over[i:i + 2], 16) * a) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(mix)


CLIPPED = set()          # pixels drawn outside the canvas (build reports them)


class Canvas:
    def __init__(self):
        self.px = {}

    def put(self, x, y, c):
        if not (0 <= x < W and TOP_SAFE <= y < H):
            CLIPPED.add((x, y))
        if 0 <= x < W and 0 <= y < H:
            under = self.px.get((x, y))
            if len(c) == 9 and under and len(under) == 7:   # translucent over opaque
                c = blend(under, c)
            self.px[(x, y)] = c

    def grid(self, rows, x, y, colors=PROP_COLORS):
        """rows of characters; '.' = transparent, others looked up in colors."""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch != ".":
                    self.put(x + i, y + j, colors[ch])

    def merge(self, other):
        for (x, y), col in other.px.items():
            self.put(x, y, col)


def outline(c, color):
    add = {}
    for (x, y) in c.px:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (x + dx, y + dy)
            if p not in c.px:
                add[p] = color
    for (x, y), col in add.items():
        c.put(x, y, col)


def spans_fill(c, spans, top, cx, col):
    """Round body from half widths per row, lit from the top left.
    Returns (left, right) per row."""
    n = len(spans)
    rows = []
    for i, hw in enumerate(spans):
        y = top + i
        left, right = int(cx - hw + 0.5), int(cx + hw - 0.5)
        rows.append((left, right))
        for x in range(left, right + 1):
            t = i / max(1, n - 1)
            color = col["mid"]
            if t > 0.75 or (t > 0.55 and (x == left or x == right)):
                color = col["shade"]
            if 0 < i <= n * 0.3 and left + 1 <= x <= cx - 2:
                color = col["hi"]
            c.put(x, y, color)
    return rows


def squashed(spans, squash):
    """squash 1: one row lower and a bit wider (breathing, landing)."""
    if squash > 0:
        return [s + 0.5 if 0 < i < len(spans) - 1 else s for i, s in enumerate(spans[1:])]
    return list(spans)


def g(s):
    return s.strip("\n").split("\n")


def rotate_cw(rows):
    w = max(len(r) for r in rows)
    rows = [r.ljust(w, ".") for r in rows]
    return ["".join(rows[len(rows) - 1 - j][i] for j in range(len(rows))) for i in range(w)]


# ---------------------------------------------------------------- pose
class Pose(dict):
    """eyes, mouth, squash, x, y, paws, star, tail, props; missing = default."""
    def __getattr__(self, k):
        return self.get(k, DEFAULT.get(k))


DEFAULT = dict(eyes="open", mouth="dot", squash=0, x=0, y=0, paws=None, star="on",
               tail=0, ear=0, puff=0, props=())
SHADOW, SHADOW_EDGE = "#1c202950", "#1c202928"


def face(c, kind, cx, ey, p, pal):
    """Eyes (2x2) at cx-3 and cx+2 on row ey, blush and mouth one row below."""
    e, s = PROP["eye"], PROP["shine"]
    lx, rx = cx - 3, cx + 2
    my = ey + 2
    for x in (lx, rx):
        eyes = p.eyes
        if eyes in ("open", "left", "right", "up", "wide"):
            dx = {"left": -1, "right": 1}.get(eyes, 0)
            top = ey - (1 if eyes in ("up", "wide") else 0)
            h = 3 if eyes == "wide" else 2
            for i in range(2):
                for j in range(h):
                    c.put(x + dx + i, top + j, e)
            c.put(x + dx + (1 if eyes == "right" else 0), top, s)
        elif eyes == "blink":
            c.put(x, ey + 1, e)
            c.put(x + 1, ey + 1, e)
        elif eyes == "half":
            c.put(x, ey + 1, e)
            c.put(x + 1, ey + 1, e)
            c.put(x + 1, ey, e)
        elif eyes == "happy":       # ^ ^
            c.put(x, ey, e)
            c.put(x + 1, ey, e)
            c.put(x - 1, ey + 1, e)
            c.put(x + 2, ey + 1, e)
        elif eyes == "sleep":       # closed, relaxed
            c.put(x - 1, ey, e)
            c.put(x, ey + 1, e)
            c.put(x + 1, ey + 1, e)
            c.put(x + 2, ey, e)
        elif eyes == "focus":       # > <
            a, b = (x, x + 1) if x == lx else (x + 1, x)
            c.put(a, ey - 1, e)
            c.put(b, ey, e)
            c.put(a, ey + 1, e)
    c.put(lx - 2, my, PROP["blush"])
    c.put(lx - 1, my, PROP["blush"])
    c.put(rx + 2, my, PROP["blush"])
    c.put(rx + 3, my, PROP["blush"])
    m = pal["mouth"]
    if p.mouth == "dot":
        if kind == "bunny":
            c.put(cx, my - 1, pal["nose"])
        if kind in ("kitty", "bunny"):   # little cat mouth
            c.put(cx - 1, my, m)
            c.put(cx + 1, my, m)
            c.put(cx, my + 1, m)
        else:
            c.put(cx, my, m)
    elif p.mouth == "smile":
        c.put(cx - 1, my, m)
        c.put(cx, my + 1, m)
        c.put(cx + 1, my, m)
    elif p.mouth in ("open", "o"):
        c.put(cx, my, m)
        c.put(cx, my + 1, PROP["tongue"] if p.mouth == "open" else m)
        if p.mouth == "open":
            c.put(cx - 1, my, m)
            c.put(cx + 1, my, m)


# paw spots relative to the body box (l, r, top, bottom)
PAWS = {
    "hold":    lambda l, r, t, b: [(r + 1, t + 5)],
    "hold_up": lambda l, r, t, b: [(r + 1, t + 1)],
    "up":      lambda l, r, t, b: [(l - 2, t + 1), (r + 1, t + 1)],
    "up2":     lambda l, r, t, b: [(l - 2, t), (r + 1, t)],
    "wave":    lambda l, r, t, b: [(r + 1, t + 3)],
    "wave2":   lambda l, r, t, b: [(r + 2, t + 1)],
    "wave_mid": lambda l, r, t, b: [(r + 2, t + 2)],
    "type":    lambda l, r, t, b: [(r + 1, b - 3), (r + 5, b - 2)],
    "type2":   lambda l, r, t, b: [(r + 1, b - 2), (r + 5, b - 3)],
    "gem":     lambda l, r, t, b: [(r + 1, t + 2)],
    "juggle":  lambda l, r, t, b: [(l - 2, t + 4), (r + 1, t + 4)],
    "juggle_l": lambda l, r, t, b: [(l - 2, t + 3), (r + 1, t + 4)],
    "juggle_r": lambda l, r, t, b: [(l - 2, t + 4), (r + 1, t + 3)],
}


def paws(which, box, col):
    pc = Canvas()
    for x, y in PAWS[which](*box):
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            pc.put(x + dx, y + dy, col["mid"])
        pc.put(x, y, col["hi"])
    return pc


BODY = {
    "mochi": [2.5, 4, 4.5, 5, 5.5, 5.5, 5.5, 5.5, 5, 4],
    "kitty": [3.5, 4.5, 5, 5.5, 5.5, 5.5, 5.5, 5.5, 5, 4.5],
    "bunny": [3, 4, 4.5, 5, 5.5, 5.5, 5.5, 5.5, 5, 4.5],
}


def bunny_ears(cx, top, ear):
    """Long ears as (x, y, inner) pixels; ear=1: the right one flops over."""
    px = []
    for dy in range(1, 4):
        px += [(cx - 2, top - dy, False), (cx - 1, top - dy, dy < 3)]
    if ear:
        px += [(cx + 1, top - 1, True), (cx + 2, top - 1, False), (cx + 2, top - 2, False),
               (cx + 3, top - 2, True), (cx + 4, top - 2, False), (cx + 3, top - 1, False),
               (cx + 4, top - 1, False), (cx + 5, top - 1, False)]
    else:
        for dy in range(1, 4):
            px += [(cx + 1, top - dy, dy < 3), (cx + 2, top - dy, False)]
    return px


def draw_pet(kind, p):
    pal = PETS[kind]
    c = Canvas()
    spans = squashed(BODY[kind], p.squash)
    if p.puff:      # all fluffed up after a shake
        spans = [sp + 0.5 * p.puff if 0 < i < len(spans) - 1 else sp for i, sp in enumerate(spans)]
    top = GROUND - len(spans) + p.y           # body ends one row above the feet
    cx = CX + p.x
    rows = spans_fill(c, spans, top, cx, pal)
    bot = top + len(rows) - 1
    l0, r0 = rows[0]
    if kind == "mochi":
        c.put(l0 - 1, top + 1, pal["mid"])     # soft tufts
        c.put(rows[3][1] + 1, top + 3, pal["mid"])
    elif kind == "bunny":
        for x, y, _ in bunny_ears(cx, top, p.ear):
            c.put(x, y, pal["mid"])
        ty = bot - 2 - (1 if p.tail else 0)          # puffy tail
        for dx, dy in ((1, 0), (2, 0), (1, 1), (2, 1)):
            c.put(rows[-3][1] + dx, ty + dy, pal["hi"])
    else:
        for dx, dy in ((0, -2), (0, -1), (1, -1)):   # ears (ear=1: left one twitches)
            c.put(l0 + dx - (1 if p.ear and dy == -2 else 0), top + dy, pal["mid"])
            c.put(r0 - dx, top + dy, pal["mid"])
        tail = [[(1, 0), (2, -1), (2, -2), (2, -3)],
                [(1, 0), (2, -1), (3, -2), (3, -3)],
                [(1, 0), (2, -1), (3, -2), (4, -3)]][p.tail]
        for dx, dy in tail:
            c.put(rows[-1][1] + dx, bot + dy, pal["shade"])
    box = (min(r[0] for r in rows), max(r[1] for r in rows), top, bot)
    if p.paws:
        c.merge(paws(p.paws, box, pal))
    outline(c, pal["line"])
    if kind == "mochi":
        sx, sy = cx, top - 3
        star, hi = (pal["star"], pal["star_hi"]) if p.star != "off" else (pal["star_off"],) * 2
        for dx, dy in ((0, 0), (-1, 1), (1, 1), (0, 1)):
            c.put(sx + dx, sy + dy, star)
        c.put(sx, sy + 1, hi)
        if p.star == "glow":
            for dx, dy in ((0, -1), (-2, 1), (2, 1)):
                c.put(sx + dx, sy + dy, pal["star_hi"])
    elif kind == "bunny":
        for x, y, inner in bunny_ears(cx, top, p.ear):
            if inner:
                c.put(x, y, pal["ear"])
    else:
        c.put(l0, top - 1, pal["ear"])
        c.put(r0, top - 1, pal["ear"])
    if p.y == 0:
        for fx in (cx - 3, cx - 2, cx + 2, cx + 3):
            c.put(fx, GROUND, pal["line"])
    # soft shadow on the "floor", smaller while in the air
    half = 4 + (p.squash > 0) + p.y
    shadow = Canvas()
    for x in range(cx - half, cx + half + 1):
        edge = abs(x - cx) == half
        shadow.put(x, GROUND + 1, SHADOW_EDGE if edge else SHADOW)
    shadow.merge(c)
    c = shadow
    face(c, kind, cx, top + 4 - (1 if p.squash > 0 else 0), p, pal)
    return c, box


# ---------------------------------------------------------------- props
PICK_LEN, PICK_HEAD = 5, 3.5     # handle length, half width of the head


def pick(c, gx, gy, angle):
    """Pickaxe held at (gx, gy), rotated clockwise from straight up (degrees).
    Drawn from a few lines and sampled finely, so every swing angle works."""
    core = Canvas()
    a = math.radians(angle)

    def put(lx, ly, col):
        x = gx + lx * math.cos(a) - ly * math.sin(a)
        y = gy + lx * math.sin(a) + ly * math.cos(a)
        core.put(math.floor(x + 0.5), math.floor(y + 0.5), col)

    t = 0.0
    while t <= PICK_LEN:
        put(0, -t, PROP_COLORS["w"])
        t += 0.2
    s = -PICK_HEAD
    while s <= PICK_HEAD:   # arched head, tips bent back towards the grip
        put(s, -PICK_LEN - 1 + 0.17 * s * s, PROP_COLORS["m" if abs(s) < 2.6 else "M"])
        s += 0.2
    outline(core, PROP_COLORS["k"])
    c.merge(core)


ROCK = g("""
...kkkkk...
.kkRRrrrkk.
kRRrrrrrrrk
krrrrRrrrdk
krrrrrrrddk
kkkkkkkkkkk
""")
CODE = ["SSs..", "SS.Ss", ".SSs.", "SSSs.", "Ss...", ".SS.S", "SSSSs", "Ss.SS"]


def screen(k):
    """Three lines of 'code', scrolling up one line per step."""
    return [CODE[(k + i) % len(CODE)] for i in range(3)]


POOF = [g("""
..tt...
.tttt..
..tt...
"""), g("""
.tt.tt.
ttttttt
.ttttt.
..t.t..
"""), g("""
t.....t
...t...
t.....t
""")]
MONITOR = g("""
.kkkkkkkkk.
kLLLLLLLLLk
kLkkkkkkkLk
kLk.....kLk
kLk.....kLk
kLk.....kLk
kLkkkkkkkLk
kLLLLLLLLLk
.kkkklkkkk.
...kllllk..
...kkkkkk..
""")
KEYBOARD = g("""
.kkkkkkkk.
kLlLlLlLlk
.kkkkkkkk.
""")
GEM = g("""
.kkkkk.
kGgggGk
kgggggk
.kgDgk.
..kDk..
...k...
""")
BULB = g("""
.kkkkk.
kYyyyyk
kyYyyyk
kyyyyyk
.kyyyk.
..kss..
..kss..
...kk..
""")
BANG = g("""
kkkk
kbbk
kbbk
kbbk
kkkk
kbbk
kkkk
""")
Z = g("""
zzzzz
...z.
..z..
.z...
zzzzz
""")
DOT = g("""
tt
tt
""")
z = g("""
zzz
.z.
zzz
""")


def fade(color, alpha):
    return color + "%02x" % int(255 * alpha)


def carrot(c, x0, y, length):
    """Carrot lying sideways, tip at x0 (the mouth), leaves on the right end."""
    core = Canvas()
    for i in range(length):
        x = x0 + i
        core.put(x, y, PROP_COLORS["o"])
        if i >= 2:
            core.put(x, y - 1, PROP_COLORS["o"])
            core.put(x, y + 1, PROP_COLORS["O"])
    e = x0 + length
    for dx, dy in ((0, 0), (1, -1), (1, 0), (1, 1), (2, -2), (2, 0), (2, 2)):
        core.put(e + dx, y + dy, PROP_COLORS["f"])
    outline(core, PROP_COLORS["k"])
    c.merge(core)


BUTTERFLY = [g("""
p...p
BpqpB
.BqB.
"""), g("""
..p..
.BqB.
..q..
""")]
HEART = g("""
h.h
hhh
.h.
""")


def soft_sprite(c, rows, x, y, line, alpha=1.0):
    """Small sprite with its own soft outline, optionally faded as a whole."""
    core = Canvas()
    core.grid(rows, x, y)
    outline(core, line)
    for (px, py), col in core.px.items():
        c.put(px, py, col if alpha >= 1 else fade(col, alpha))


def props(c, items, box, pal=None):
    l, r, top, bot = box
    for item in items:
        name, *args = item if isinstance(item, tuple) else (item,)
        if name == "rock":
            c.grid(ROCK, r + 7, GROUND - 5)
        elif name == "pick":          # (pick, angle): grip in the "hold" paw
            pick(c, r + 2, top + 5, args[0])
        elif name == "sparks":        # (sparks, step): fly out from the hit
            k = args[0]
            for dx, dy, col in ((1, -1, "spark"), (2, -2, "chip"), (-1, -2, "spark"),
                                (3, 0, "spark"), (0, -3, "chip")):
                x, y = r + 9 + dx * (k + 1), GROUND - 5 + dy * (k + 1) * 2 // 3 - k // 2
                c.put(x, y, fade(PROP[col], 1 - k * 0.3))
        elif name == "computer":      # monitor with code lines + keyboard
            c.grid(MONITOR, r + 9, GROUND - 10)
            c.grid(screen(args[0]), r + 12, GROUND - 7, {"S": PROP_COLORS["S"], "s": "#ffffff"})
            c.grid(KEYBOARD, r, GROUND - 2)
        elif name == "dots":
            for i in range(args[0]):
                c.grid(DOT, r + 2 + i * 3, top - 1 - i)
        elif name == "bulb":
            c.grid(BULB, r + 3, top - 4)
        elif name == "gem":           # (gem, bob, sparkle)
            gy = top - 3 + args[0]
            c.grid(GEM, r - 1, gy)
            if len(args) > 1 and args[1]:
                sx, sy = r + 5, gy - 1
                for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                    c.put(sx + dx, sy + dy, "#ffffff" if (dx, dy) == (0, 0) else fade("#ffffff", 0.6))
        elif name == "poof":          # (poof, step, dx, dy): little cloud where a prop appears
            k, dx, dy = args
            c.grid(POOF[k], r + dx, GROUND + dy, {"t": fade(PROP["think"], (1, 0.85, 0.55)[k])})
        elif name == "carrot":        # (carrot, length): gets shorter bite by bite
            carrot(c, (l + r) // 2 + 2, top + 6, args[0])
        elif name == "bang":
            c.grid(BANG, r + 4, top - 1 + (args[0] if args else 0))
        elif name == "Z":             # (Z, step 0..7): rises and fades out
            k = args[0]
            alpha = 1 if k < 5 else 1 - (k - 4) * 0.25
            shape = z if k < 3 else Z
            c.grid(shape, r - 1 + k // 3, GROUND - 7 - k, {"z": fade(PROP["z"], alpha)})
        elif name == "butterfly":     # (butterfly, x, y, wings 0 open / 1 folded[, alpha]): absolute spot
            x, y, wing, *alpha = args      # optional alpha: fades out flying away
            a = alpha[0] if alpha else 1
            bc = Canvas()
            soft_sprite(bc, BUTTERFLY[wing], x - 2, y, SOFT_LINE["butterfly"])
            if not wing:              # little feelers
                bc.put(x - 1, y - 1, PROP_COLORS["q"])
                bc.put(x + 1, y - 1, PROP_COLORS["q"])
            for (px, py), col in bc.px.items():
                c.put(px, py, col if a >= 1 else fade(col, a))
        elif name == "heart":         # (heart, x, y, alpha): absolute spot
            x, y, alpha = args
            hc = Canvas()
            soft_sprite(hc, HEART, x - 1, y, SOFT_LINE["heart"])
            hc.put(x - 1, y, PROP_COLORS["H"])
            for (px, py), col in hc.px.items():
                c.put(px, py, col if alpha >= 1 else fade(col, alpha))
        elif name == "fluff":         # (fluff, step): tufts of fur fly off and drift down
            k = args[0]
            cx, cy = (l + r) // 2, (top + bot) // 2
            alpha = (1, 0.9, 0.7, 0.45, 0.25)[k]
            for i, (dx, dy) in enumerate(((-0.6, -1), (1, -1.2), (-0.7, -0.3), (1.3, -0.2),
                                          (0.1, -1.4), (-0.4, -1.3), (0.7, -1.3))):
                dist = 5 + k * 1.1
                x = round(cx + dx * dist)
                y = round(cy + dy * dist * 0.55 + k * k * 0.3)
                col = pal["hi"] if i % 2 else pal["mid"]
                c.put(x, y, fade(col, alpha))
                c.put(x + (1 if dx >= 0 else -1), y, fade(pal["shade"], alpha * 0.8))
                if k < 2:
                    c.put(x, y - 1, fade(col, alpha * 0.6))
        elif name == "ball":          # (ball, x, y, color): 2x2 juggling ball, top left at x, y
            x, y, i = args
            col, shine = BALLS[i]
            bc = Canvas()
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                bc.put(x + dx, y + dy, col)
            outline(bc, PROP_COLORS["k"])
            bc.put(x, y, shine)
            c.merge(bc)
        elif name == "dizzy":         # (dizzy, step): little stars circling the head after a bonk
            k = args[0]
            cx = (l + r) // 2
            for i in range(3):
                a = (k * 0.9 + i * 2.1)
                x = round(cx + 6 * math.cos(a))
                y = round(top - 1 + 1.5 * math.sin(a))
                c.put(x, y, PROP["spark"])
                if (k + i) % 2:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        c.put(x + dx, y + dy, fade(PROP["spark"], 0.55))
        elif name == "confetti":      # (confetti, step): pieces drift down
            k = args[0]
            pts = [(l - 3, 2), (l - 2, 6), (r + 4, 1), (r + 7, 5), (l + 2, 1), (r + 1, 3),
                   (r + 10, 2), (l - 3, 8), (r + 13, 6), (l + 6, 1)]
            for i, (x, y) in enumerate(pts):
                yy = y + k
                wob = (1 if (k + i) % 4 < 2 else 0)
                if TOP_SAFE <= yy < GROUND + 2:
                    c.put(x + wob, yy, PROP["confetti"][i % 6])


BACK = ("rock", "computer")


def render(kind, pose):
    p = Pose(pose)
    body, box = draw_pet(kind, p)
    c = Canvas()
    # rock and computer stand behind the pet, so does a pickaxe swung back
    back = [x for x in p.props if (x if isinstance(x, str) else x[0]) in BACK
            or (isinstance(x, tuple) and x[0] == "pick" and x[1] < 0)]
    props(c, back, box, PETS[kind])
    c.merge(body)
    props(c, [x for x in p.props if x not in back], box, PETS[kind])
    return c


# ---------------------------------------------------------------- animations
def F(ms, **pose):
    return (pose, ms)


def rep(seq, n):
    return seq * n


def swing():
    """One pickaxe blow: wind up, swing (several angles), hit, sparks, back."""
    hold = dict(paws="hold", eyes="right", props=["rock"])

    def at(ms, angle, **kw):
        pose = dict(hold, **kw)
        pose["props"] = pose["props"] + [("pick", angle)]
        return F(ms, **pose)
    return [at(160, 0), at(120, -15), at(260, -30), at(60, 0), at(50, 35),
            at(50, 70), at(90, 100, eyes="focus", squash=1),
            at(80, 100, eyes="focus", squash=1, props=["rock", ("sparks", 0)]),
            at(80, 95, eyes="focus", props=["rock", ("sparks", 1)]),
            at(90, 85, props=["rock", ("sparks", 2)]),
            at(90, 60), at(110, 30)]


def jump(ms=70, height=2, **pose):
    """Crouch, rise, hang, fall, land: a little arc instead of a teleport."""
    ys = list(range(-1, -height - 1, -1))
    up = [F(ms, y=y, **pose) for y in ys]
    return ([F(110, squash=1, **pose)] + up + [F(ms * 2, y=-height, **pose)] +
            up[::-1][1:] + [F(ms, **pose), F(130, squash=1, **pose), F(ms, **pose)])


def with_props(frames, fn):
    """Give each frame props from fn(index), e.g. confetti that keeps falling."""
    return [(dict(pose, props=list(pose.get("props", [])) + fn(i)), ms)
            for i, (pose, ms) in enumerate(frames)]


def appear(poof, props, pose):
    """A prop pops in: puff of cloud first, the prop shows up inside it."""
    name, dx, dy = poof
    return [F(90, props=[(name, 0, dx, dy)], **pose),
            F(90, props=props + [(name, 1, dx - 1, dy)], **pose),
            F(110, props=props + [(name, 2, dx - 1, dy)], **pose)]


def butterfly():
    """A butterfly flutters down out of the sky, the pet watches it come,
    it lands on its head, the pet melts into a smile (heart), then it lifts
    off and the pet hops up trying to catch it. Happy little heart at the end."""
    out = []
    # approach in a wobbly curve from the top right
    path = []
    for i in range(16):
        t = i / 15
        x = 24 - 12 * t + 1.2 * math.sin(t * 9)
        y = 4 - 0.5 * t + 1.8 * math.sin(t * 12)
        path.append((round(x), round(y)))
    for i, (x, y) in enumerate(path):
        eyes = "up" if x < 15 else "right"
        if i < 3:
            eyes = "open" if i == 0 else "right"
        out.append(F(100, eyes=eyes, props=[("butterfly", x, y, i % 2)]))
    land = ("butterfly", 12, 3)          # on the right shoulder of the head
    # sitting: slow wing beats, the pet looks up, then melts
    out += [F(500, eyes="up", props=[land + (0,)]),
            F(260, eyes="up", props=[land + (1,)]),
            F(500, eyes="up", props=[land + (0,)]),
            F(160, eyes="wide", props=[land + (0,)])]
    for k in range(6):   # a heart rises and fades while the pet grins
        out.append(F(200, squash=1 if k in (1, 2) else 0, **SMILE,
                     props=[land + (k % 3 == 2,), ("heart", 3, 5 - k // 2, 1 - k * 0.15)]))
    out.append(F(300, eyes="up", props=[land + (1,)]))
    # takeoff: it lifts up and away, the pet reaches up after it
    flight = [(13, 2), (15, 2), (17, 3), (19, 2), (21, 3), (23, 2), (25, 3)]
    jumps = jump(70, 2, eyes="up", mouth="o", paws="up")
    out += with_props(jumps, lambda i: [("butterfly", *flight[min(i, len(flight) - 1)], i % 2,
                                         1 - max(0, i - 3) * 0.22)] if i < len(flight) else [])
    out += [F(400, eyes="right"), F(150, eyes="blink"), F(120, eyes="right")]
    for k in range(5):
        out.append(F(170, **SMILE, props=[("heart", 15 + (k % 2), 5 - k // 2, 1 - k * 0.18)]))
    out.append(F(700, **SMILE))
    return out


def juggle():
    """Juggles three balls (Claude orange, blue, pink) in a shower pattern:
    up from the right paw, over the head, down into the left paw. Then
    catches two, the third bonks it on the head and bounces away, dizzy
    stars, and the pet laughs it off."""
    top = GROUND - 10                    # body top while standing
    hy = top + 3                         # ball row at the paws
    lx, rx = CX - 8, CX + 6              # ball x in the left / right paw
    cx, rxx, ry = (lx + rx) / 2, (rx - lx) / 2, hy - 2   # arc: apex on row 2

    def at(p):
        """Ball position for phase p in 0..1."""
        if p < 0.8:                      # in the air, right to left
            a = math.pi * p / 0.8
            return round(cx + rxx * math.cos(a)), round(hy - ry * math.sin(a))
        return (lx, hy) if p < 0.9 else (rx, hy)   # quick pass in the paws

    out = []
    steps = 12
    for k in range(steps * 3):
        t = k / steps
        balls = [("ball", *at((t + i / 3) % 1), i) for i in range(3)]
        throw = (k % 4) in (0, 1)
        eyes = "focus" if k % 12 in (5, 6) else "up"
        out.append(F(95, paws="juggle_r" if throw else "juggle_l", eyes=eyes, props=balls))
    # catch two, the third (blue) comes straight down on the head
    held = [("ball", lx, hy, 0), ("ball", rx, hy, 2)]
    for y in (2, 3, top - 3):
        out.append(F(90, paws="juggle", eyes="up", props=held + [("ball", CX - 1, y, 1)]))
    out.append(F(110, paws="juggle", eyes="blink", squash=1, mouth="o",
                 props=held + [("ball", CX - 1, top - 2, 1)]))
    # it bounces off to the right and rolls away; the pet is dizzy
    bounce = [(CX + 2, top - 4), (CX + 5, top - 4), (CX + 7, top - 2), (CX + 9, top + 2),
              (CX + 10, GROUND - 2), (CX + 11, GROUND - 3), (CX + 12, GROUND - 2),
              (CX + 13, GROUND - 2), (CX + 14, GROUND - 2)]
    for k, (x, y) in enumerate(bounce):
        out.append(F(100, paws="juggle", eyes="sleep" if k < 6 else "half",
                     props=held + [("ball", x, y, 1), ("dizzy", k)]))
    rest = held + [("ball", CX + 14, GROUND - 2, 1)]
    out += [F(160, paws="juggle", eyes="blink", props=rest), F(140, paws="juggle", props=rest),
            F(140, paws="juggle", eyes="right", props=rest)]
    for k in range(4):                   # giggle
        out.append(F(140, paws="juggle", eyes="happy", mouth="open" if k % 2 == 0 else "smile",
                     squash=k % 2, props=rest))
    out.append(F(500, paws="juggle", **SMILE, props=rest))
    return out


def fluff():
    """Shakes like a wet puppy: squeezed eyes, wobble, poofs up twice its
    fluff with tufts flying off, then settles down proud."""
    shake = rep([F(55, x=-1, eyes="focus"), F(55, x=1, eyes="focus")], 5)
    return ([F(300, eyes="half"), F(160, squash=1, eyes="focus")] + shake +
            [F(110, puff=1, eyes="wide", mouth="o", props=[("fluff", 0)]),
             F(120, puff=2, eyes="wide", mouth="o", props=[("fluff", 1)]),
             F(140, puff=2, **SMILE, props=[("fluff", 2)]),
             F(180, puff=1, **SMILE, props=[("fluff", 3)]),
             F(220, puff=1, **SMILE, props=[("fluff", 4)]),
             F(160, squash=1, **SMILE), F(900, **SMILE)])


SMILE = dict(eyes="happy", mouth="smile")
ANIMS = {
    # ---- idle (day)
    "rest":    [F(1800)],
    "breathe": rep([F(800, squash=1), F(1000)], 2),
    "blink":   [F(90, eyes="half"), F(110, eyes="blink"), F(90, eyes="half"), F(700),
                F(90, eyes="half"), F(110, eyes="blink"), F(90, eyes="half"), F(500)],
    "look":    [F(900, eyes="left"), F(300), F(900, eyes="right"), F(400)],
    "wave":    [F(120, paws="wave", **SMILE)] +
               rep([F(110, paws="wave_mid", **SMILE), F(160, paws="wave2", **SMILE),
                    F(110, paws="wave_mid", **SMILE), F(160, paws="wave", **SMILE)], 3) + [F(300, **SMILE)],
    "hop":     jump() + [F(300)],
    "wiggle":  rep([F(160, x=-1), F(160), F(160, x=1), F(160)], 2),
    "yawn":    [F(200, eyes="half"), F(150, eyes="half", mouth="o"), F(900, eyes="happy", mouth="open"),
                F(200, eyes="half", mouth="o"), F(400, eyes="half"), F(120, eyes="blink"), F(300)],
    "happy":   [F(1400, **SMILE)],
    "butterfly": butterfly(),
    "fluff":   fluff(),
    # mochi only
    "twinkle": [F(160, star="glow"), F(160), F(160, star="glow"), F(160), F(700, eyes="up")],
    # kitty only
    "swish":   rep([F(140, tail=1), F(200, tail=2), F(140, tail=1), F(200, tail=0)], 3),
    "twitch":  [F(120, ear=1), F(160), F(120, ear=1), F(900)],
    # bunny only
    "nibble":  appear(("poof", 2, -9), [("carrot", 6)], dict(eyes="right")) +
               [F(150, eyes="happy" if i % 2 else "open", mouth="o" if i % 2 else "dot",
                  props=[("carrot", 6 - i // 3)]) for i in range(12)] +
               [F(200, mouth="o"), F(1000, **SMILE)],
    "flop":    [F(700, ear=1, eyes="up"), F(200, ear=1, eyes="blink"), F(500, ear=1),
                F(150, squash=1), F(600, **SMILE)],
    "thump":   rep([F(120, tail=1, squash=1), F(160)], 3) + [F(500)],
    # ---- night / off
    "sleep":   [F(260, eyes="sleep", star="off", squash=1 if i % 4 < 2 else 0, props=[("Z", i)])
                for i in range(8)] + [F(600, eyes="sleep", star="off")],
    "doze":    [F(1200, eyes="half"), F(150, eyes="blink"), F(1500, eyes="sleep"), F(200, eyes="blink"),
                F(250, eyes="half"), F(800)],
    # ---- starting
    "wake":    [F(700, eyes="sleep", star="off"), F(300, eyes="blink"), F(300, eyes="half"), F(150, eyes="blink"),
                F(300), F(120, eyes="blink"), F(200, star="glow"), F(900, **SMILE)],
    # ---- busy
    "mine":    appear(("poof", 9, -4), ["rock"], dict(paws="hold", eyes="right")) + rep(swing(), 4),
    "type":    appear(("poof", 11, -7), [("computer", 0)], dict(eyes="right")) +
               [F(130, paws="type" if i % 2 else "type2", eyes="right", props=[("computer", i // 2)])
                for i in range(20)],
    "juggle":  juggle(),
    "think":   [F(500, eyes="up", props=[("dots", 1)]), F(500, eyes="up", props=[("dots", 2)]),
                F(500, eyes="up", props=[("dots", 3)]), F(400, eyes="left", props=[("dots", 3)]),
                F(120, eyes="wide", props=[("dots", 3)]),
                F(900, eyes="happy", mouth="o", star="glow", props=["bulb"])],
    # ---- waiting
    "alert":   with_props(jump(60, 2, eyes="wide", paws="wave"), lambda i: [("bang", 0)]) +
               [F(110, eyes="wide", paws="wave_mid", props=[("bang", 0)]),
                F(160, eyes="wide", paws="wave2", props=[("bang", 0)]),
                F(110, eyes="wide", paws="wave_mid", props=[("bang", 0)]),
                F(400, eyes="wide", paws="wave", props=[("bang", 0)]), F(400, eyes="wide", mouth="o")],
    # ---- done
    "cheer":   with_props(jump(70, 2, eyes="happy", mouth="open", paws="up") +
                          jump(70, 2, eyes="happy", mouth="open", paws="up2") +
                          [F(200, eyes="happy", mouth="smile", paws="up")] * 3,
                          lambda i: [("confetti", i)]),
    "gem":     rep([F(450, paws="gem", props=[("gem", 0, 0)], **SMILE),
                    F(150, paws="gem", props=[("gem", 1, 1)], **SMILE),
                    F(300, paws="gem", props=[("gem", 1, 0)], **SMILE)], 3),
    # ---- clicked
    "poke":    [F(90, eyes="wide", mouth="o")] + jump(60, 2, eyes="happy", mouth="open") +
               [F(700, **SMILE)],
}
ONLY = {"twinkle": ("mochi",), "swish": ("kitty",), "twitch": ("kitty",),
        "nibble": ("bunny",), "flop": ("bunny",), "thump": ("bunny",)}


def anims_for(kind):
    return [n for n in ANIMS if kind in ONLY.get(n, (kind,))]


# ---------------------------------------------------------------- build
def image(canvas, scale):
    from PIL import Image
    im = Image.new("RGBA", (W * scale, H * scale), (0, 0, 0, 0))
    for (x, y), col in canvas.px.items():
        im.paste(col, (x * scale, y * scale, (x + 1) * scale, (y + 1) * scale))
    return im


def build(out):
    frames_dir = os.path.join(out, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir):
        os.unlink(os.path.join(frames_dir, f))
    ids, anims, css, widths, bad = {}, {}, [], set(), set()
    for kind in PETS:
        anims[kind] = {}
        for name in anims_for(kind):
            seq = ANIMS[name]
            steps, right = [], 0
            for pose, ms in seq:
                CLIPPED.clear()
                canvas = render(kind, pose)
                if CLIPPED:
                    bad.add(f"{kind}/{name}")
                key = hashlib.sha1(repr(sorted(canvas.px.items())).encode()).hexdigest()
                if key not in ids:
                    n = ids[key] = len(ids)
                    image(canvas, SCALE).save(os.path.join(frames_dir, f"f{n}@2.png"))
                    image(canvas, 2).save(os.path.join(frames_dir, f"f{n}.png"))
                    css.append(f'#custom-claude.f{n} {{ background-image: -gtk-scaled('
                               f'url("frames/f{n}.png"), url("frames/f{n}@2.png")); }}')
                steps.append([f"f{ids[key]}", ms])
                right = max([right] + [x for (x, y) in canvas.px])
            cols = min(W, max(MIN_COLS, right + 2))
            cols += cols % 2                   # whole logical pixels
            widths.add(cols)
            anims[kind][name] = [st + [f"w{cols}"] for st in steps]
    w, h = W * SCALE // 2, H * SCALE // 2
    with open(os.path.join(out, "pet.css"), "w") as f:
        f.write("/* Generated by ~/.local/lib/pet/pet.py build: one class per pet frame */\n")
        f.write(f"#custom-claude {{ min-width: {MIN_COLS * SCALE // 2}px; min-height: {h}px; "
                f"background-size: {w}px {h}px; }}\n")
        for cols in sorted(widths):
            f.write(f"#custom-claude.w{cols} {{ min-width: {cols * SCALE // 2}px; }}\n")
        f.write("\n".join(css) + "\n")
    with open(os.path.join(out, "anims.json"), "w") as f:
        json.dump({"anims": anims, "names": NAMES}, f)
    print(f"{len(ids)} frames -> {out}")
    if bad:
        print("WARNING: leaves the bar (clipped):", ", ".join(sorted(bad)), file=sys.stderr)


def sheet(path, bg="#7583a8", scale=4):
    from PIL import Image
    tiles = []
    for kind in PETS:
        for name in anims_for(kind):
            for pose, _ in ANIMS[name][:3]:
                tiles.append(image(render(kind, pose), scale))
    cols, pad = 5, 6
    tw, th = W * scale, H * scale
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGBA", (cols * (tw + pad) + pad, rows * (th + pad) + pad), "#161a21")
    for i, t in enumerate(tiles):
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + pad)
        out.paste(Image.new("RGBA", (tw, th), bg), (x, y))
        out.paste(t, (x, y), t)
    out.save(path)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "build":
        build(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "sheet":
        sheet(sys.argv[2])
    else:
        sys.exit(__doc__)
