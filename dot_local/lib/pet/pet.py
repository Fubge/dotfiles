#!/usr/bin/env python3
"""The bar pet: a tiny pixel critter that lives in waybar (custom/claude) and
acts out what Claude is doing.

Two pets, picked in the claude-pad menu:
  mochi   peach fluffball with a little orange star (the Claude sparkle)
  kitty   round blue-grey kitten loaf

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
import os
import sys

W, H = 40, 20            # canvas in art pixels (60 x 30 logical = bar height)
SCALE = 3                # device pixels per art pixel in the @2 image
GROUND = H - 2           # feet stand on this row (one free row: the pill is rounded)
CX = 9                   # where the pet stands (center column)

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
}

PETS = {
    "mochi": dict(hi="#fff4e6", mid="#ffd8b5", shade="#f3b48a", line="#9c5a3c",
                  mouth="#7a3b2e", star="#ff7f00", star_hi="#ffdd99", star_off="#c98a63"),
    "kitty": dict(hi="#f3f5fa", mid="#d6dcea", shade="#adb6cd", line="#454b63",
                  mouth="#454b63", ear="#ffb3c2"),
}


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.px = {}

    def put(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[(x, y)] = c

    def grid(self, rows, x, y, colors=PROP_COLORS):
        """rows of characters; '.' = transparent, others looked up in colors."""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch != ".":
                    self.put(x + i, y + j, colors[ch])

    def merge(self, other):
        self.px.update(other.px)


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
               tail=0, props=())


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
        if kind == "kitty":           # little cat mouth
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
    "type":    lambda l, r, t, b: [(r + 1, b - 3), (r + 5, b - 2)],
    "type2":   lambda l, r, t, b: [(r + 1, b - 2), (r + 5, b - 3)],
    "gem":     lambda l, r, t, b: [(r + 1, t + 2)],
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
}


def draw_pet(kind, p):
    pal = PETS[kind]
    c = Canvas()
    spans = squashed(BODY[kind], p.squash)
    top = GROUND - len(spans) + p.y           # body ends one row above the feet
    cx = CX + p.x
    rows = spans_fill(c, spans, top, cx, pal)
    bot = top + len(rows) - 1
    l0, r0 = rows[0]
    if kind == "mochi":
        c.put(l0 - 1, top + 1, pal["mid"])     # soft tufts
        c.put(rows[3][1] + 1, top + 3, pal["mid"])
    else:
        for dx, dy in ((0, -2), (0, -1), (1, -1)):   # ears
            c.put(l0 + dx, top + dy, pal["mid"])
            c.put(r0 - dx, top + dy, pal["mid"])
        tail = [[(1, 0), (2, -1), (2, -2), (2, -3)],
                [(1, 0), (2, -1), (3, -2), (3, -3)]][p.tail]
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
    else:
        c.put(l0, top - 1, pal["ear"])
        c.put(r0, top - 1, pal["ear"])
    if p.y == 0:
        for fx in (cx - 3, cx - 2, cx + 2, cx + 3):
            c.put(fx, GROUND, pal["line"])
    face(c, kind, cx, top + 4 - (1 if p.squash > 0 else 0), p, pal)
    return c, box


# ---------------------------------------------------------------- props
PICK_UP = g("""
...kkkkk...
.kkmmmmmkk.
kmmMkwkMmmk
kMk.kwk.kMk
kk..kwk..kk
....kwk....
....kwk....
....kkk....
""")
PICK_HIT = rotate_cw(PICK_UP)
ROCK = g("""
...kkkkk...
.kkRRrrrkk.
kRRrrrrrrrk
krrrrRrrrdk
krrrrrrrddk
kkkkkkkkkkk
""")
SCREEN = [g("""
SSSs.
Ss.SS
SSSSs
"""), g("""
SSs.S
SSSSs
Ss...
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


def props(c, items, box):
    l, r, top, bot = box
    for item in items:
        name, *args = item if isinstance(item, tuple) else (item,)
        if name == "rock":
            c.grid(ROCK, r + 9, GROUND - 5)
        elif name == "pick_up":       # raised over the shoulder, handle in the paw
            c.grid(PICK_UP, r - 4, top - 6)
        elif name == "pick_hit":      # swung down onto the rock
            c.grid(PICK_HIT, r + 2, top + 1)
        elif name == "sparks":
            for dx, dy, col in ((9, -4, "spark"), (12, -6, "spark"), (16, -5, "chip"),
                                (19, -3, "spark"), (14, -8, "chip"), (8, -1, "chip")):
                c.put(r + dx, GROUND - 5 + dy, PROP[col])
        elif name == "computer":      # monitor with code lines + keyboard
            c.grid(MONITOR, r + 9, GROUND - 10)
            c.grid(SCREEN[args[0]], r + 12, GROUND - 7, {"S": PROP_COLORS["S"], "s": "#ffffff"})
            c.grid(KEYBOARD, r, GROUND - 2)
        elif name == "dots":
            for i in range(args[0]):
                c.grid(DOT, r + 2 + i * 3, top - 3 - i)
        elif name == "bulb":
            c.grid(BULB, r + 2, top - 7)
        elif name == "gem":
            c.grid(GEM, r - 1, top - 5 + (args[0] if args else 0))
        elif name == "bang":
            c.grid(BANG, r + 4, top - 3 + (args[0] if args else 0))
        elif name == "Z":
            c.grid(Z, r + args[0], args[1])
        elif name == "confetti":
            seed = args[0]
            pts = [(l - 5, 4), (l - 3, 10), (r + 4, 2), (r + 7, 9), (l + 2, 0), (r + 1, 6),
                   (r + 10, 4), (l - 6, 13), (r + 13, 11), (l + 6, 3)]
            for i, (x, y) in enumerate(pts):
                c.put(x + (seed % 2), (y + seed * 2) % (H - 3), PROP["confetti"][(i + seed) % 6])


BACK = ("rock", "computer")


def render(kind, pose):
    p = Pose(pose)
    body, box = draw_pet(kind, p)
    c = Canvas()
    names = [x if isinstance(x, str) else x[0] for x in p.props]
    props(c, [x for x, n in zip(p.props, names) if n in BACK], box)
    c.merge(body)
    props(c, [x for x, n in zip(p.props, names) if n not in BACK], box)
    return c


# ---------------------------------------------------------------- animations
def F(ms, **pose):
    return (pose, ms)


def rep(seq, n):
    return seq * n


ANIMS = {
    # ---- idle (day)
    "rest":    [F(1800)],
    "breathe": rep([F(700, squash=1), F(900)], 2),
    "blink":   [F(130, eyes="blink"), F(400), F(130, eyes="blink"), F(600)],
    "look":    [F(900, eyes="left"), F(250), F(900, eyes="right"), F(400)],
    "wave":    [F(200, paws="wave", mouth="smile")] + rep([F(220, paws="wave2", eyes="happy", mouth="smile"),
                                                          F(220, paws="wave", eyes="happy", mouth="smile")], 3),
    "hop":     [F(150, squash=1), F(140, y=-1), F(200, y=-2), F(140, y=-1), F(160, squash=1), F(300)],
    "wiggle":  rep([F(180, x=-1, squash=1), F(180), F(180, x=1, squash=1), F(180)], 2),
    "yawn":    [F(300, eyes="half"), F(900, eyes="happy", mouth="open"), F(400, eyes="half"), F(400, eyes="blink"), F(300)],
    "happy":   [F(1400, eyes="happy", mouth="smile")],
    # mochi only
    "twinkle": [F(220, star="glow"), F(220), F(220, star="glow"), F(600, eyes="up")],
    # kitty only
    "swish":   rep([F(260, tail=1), F(260, tail=0)], 3),
    # ---- night / off
    "sleep":   rep([F(900, eyes="sleep", star="off", props=[("Z", 3, 7)]),
                    F(900, eyes="sleep", star="off", squash=1, props=[("Z", 5, 2)])], 2),
    "doze":    [F(1200, eyes="half"), F(300, eyes="blink"), F(1500, eyes="sleep"), F(300, eyes="half"),
                F(200, eyes="open"), F(800)],
    # ---- starting
    "wake":    [F(700, eyes="sleep", star="off"), F(300, eyes="half"), F(150, eyes="blink"), F(300),
                F(150, eyes="blink"), F(200, star="glow"), F(900, eyes="happy", mouth="smile")],
    # ---- busy
    "mine":    rep([F(380, paws="hold_up", eyes="right", props=["rock", "pick_up"]),
                    F(110, paws="hold", eyes="focus", squash=1, props=["rock", "pick_hit"]),
                    F(260, paws="hold", eyes="focus", squash=1, props=["rock", "pick_hit", "sparks"])], 4),
    "type":    rep([F(150, paws="type", eyes="right", props=[("computer", 0)]),
                    F(150, paws="type2", eyes="right", props=[("computer", 1)])], 8),
    "think":   [F(500, eyes="up", props=[("dots", 1)]), F(500, eyes="up", props=[("dots", 2)]),
                F(500, eyes="up", props=[("dots", 3)]), F(400, eyes="left", props=[("dots", 3)]),
                F(900, eyes="happy", mouth="o", star="glow", props=["bulb"])],
    # ---- waiting
    "alert":   [F(160, squash=1, props=[("bang", 0)]), F(220, y=-2, eyes="wide", paws="wave", props=[("bang", -1)]),
                F(160, eyes="wide", paws="wave2", props=[("bang", 0)]), F(500, eyes="wide", paws="wave", props=[("bang", 0)]),
                F(400, eyes="wide", mouth="o")],
    # ---- done
    "cheer":   [F(150, squash=1, eyes="happy", mouth="open")] +
               rep([F(200, y=-2, eyes="happy", mouth="open", paws="up", props=[("confetti", 0)]),
                    F(200, y=-1, eyes="happy", mouth="open", paws="up2", props=[("confetti", 1)]),
                    F(160, squash=1, eyes="happy", mouth="smile", paws="up", props=[("confetti", 2)])], 3),
    "gem":     rep([F(400, eyes="happy", mouth="smile", paws="gem", props=[("gem", 0)]),
                    F(400, eyes="happy", mouth="smile", paws="gem", squash=1, props=[("gem", 1)])], 3),
}
ONLY = {"twinkle": "mochi", "swish": "kitty"}


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
    ids, anims, css = {}, {}, []
    for kind in PETS:
        anims[kind] = {}
        for name, seq in ANIMS.items():
            if ONLY.get(name, kind) != kind:
                continue
            steps = []
            for pose, ms in seq:
                canvas = render(kind, pose)
                key = hashlib.sha1(repr(sorted(canvas.px.items())).encode()).hexdigest()
                if key not in ids:
                    n = ids[key] = len(ids)
                    image(canvas, SCALE).save(os.path.join(frames_dir, f"f{n}@2.png"))
                    image(canvas, 2).save(os.path.join(frames_dir, f"f{n}.png"))
                    css.append(f'#custom-claude.f{n} {{ background-image: -gtk-scaled('
                               f'url("frames/f{n}.png"), url("frames/f{n}@2.png")); }}')
                steps.append([f"f{ids[key]}", ms])
            anims[kind][name] = steps
    w, h = W * SCALE // 2, H * SCALE // 2
    with open(os.path.join(out, "pet.css"), "w") as f:
        f.write("/* Generated by ~/.local/lib/pet/pet.py build: one class per pet frame */\n")
        f.write(f"#custom-claude {{ min-width: {w}px; min-height: {h}px; background-size: {w}px {h}px; }}\n")
        f.write("\n".join(css) + "\n")
    with open(os.path.join(out, "anims.json"), "w") as f:
        json.dump({"anims": anims}, f)
    print(f"{len(ids)} frames -> {out}")


def sheet(path, bg="#7583a8", scale=4):
    from PIL import Image
    tiles = []
    for kind in PETS:
        for name, seq in ANIMS.items():
            if ONLY.get(name, kind) != kind:
                continue
            for pose, _ in seq[:3]:
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
