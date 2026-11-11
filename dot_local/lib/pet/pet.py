#!/usr/bin/env python3
"""The bar pet: a tiny pixel critter that lives in waybar (custom/claude) and
acts out what Claude is doing.

Two pets, picked in the claude-pad menu:
  mochi   peach fluffball with a little orange star (the Claude sparkle)
  kitty   round blue-grey kitten loaf

Everything is drawn here as code (round silhouettes from row spans, an outline
around them, then face and props on top). `build` renders every frame of every
animation to PNG and writes a CSS file with one class per frame; the bar daemon
(claude-pad watch) only switches classes.

    pet.py build DIR      frames to DIR/frames, DIR/pet.css, DIR/anims.json
    pet.py sheet FILE     contact sheet of all frames (for design work)

One art pixel = 3 device pixels = 1.5 logical pixels at scale 2. The @2 image
is used 1:1 (crisp), the plain one is only there for scale 1 setups.
"""
import hashlib
import json
import os
import sys

W, H = 36, 20            # canvas in art pixels (54 x 30 logical = bar height)
SCALE = 3                # device pixels per art pixel in the @2 image
GROUND = H - 1           # feet stand on this row

# ---------------------------------------------------------------- colors
PROP = {
    "pick_metal": "#d4d9e6", "pick_wood": "#b08257", "outline": "#2b3047",
    "rock": "#7d8599", "rock_hi": "#a3abbf", "spark": "#ffdd99",
    "z": "#a8e0ff", "bang": "#ff7f00", "think": "#f8f8f2", "bulb": "#ffdd66",
    "laptop": "#9aa3b8", "laptop_dark": "#4a5068", "screen": "#8fe3ff",
    "gem": "#8fe3ff", "gem_hi": "#ffffff", "gem_dark": "#4fa6d6",
    "confetti": ["#ff7f00", "#8fe3ff", "#ffdd99", "#c49bff", "#a6e3a1", "#ff9eb0"],
    "eye": "#2a2433", "shine": "#ffffff", "blush": "#ff9eb0",
}

PETS = {
    "mochi": dict(hi="#fff4e6", mid="#ffd8b5", shade="#f3b48a", line="#9c5a3c",
                  mouth="#7a3b2e", star="#ff7f00", star_hi="#ffdd99", star_off="#c98a63"),
    "kitty": dict(hi="#eef1f8", mid="#cdd4e6", shade="#a7b0c9", line="#4a5068",
                  mouth="#4a5068", ear="#ffb3c2"),
}


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.px = {}

    def put(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[(x, y)] = c

    def get(self, x, y):
        return self.px.get((x, y))

    def grid(self, rows, x, y, colors):
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
        if 0 <= x < W and 0 <= y < H:
            c.px[(x, y)] = col


def spans_fill(c, spans, top, cx, col):
    """Round body from half widths per row, lit from the top left."""
    n = len(spans)
    for i, hw in enumerate(spans):
        y = top + i
        left, right = int(cx - hw + 0.5), int(cx + hw - 0.5)
        for x in range(left, right + 1):
            t = i / max(1, n - 1)
            color = col["mid"]
            if t > 0.72 or (t > 0.55 and (x - left < 1 or right - x < 1)):
                color = col["shade"]
            if t < 0.3 and left + 2 <= x <= cx - 1 and i >= 1:
                color = col["hi"]
            c.put(x, y, color)
    return [(int(cx - hw + 0.5), int(cx + hw - 0.5)) for hw in spans]


def squashed(spans, squash):
    """squash 1: one row lower and a bit wider; -1: stretched (jump)."""
    if squash > 0:
        return [s + 0.5 if 0 < i < len(spans) - 1 else s for i, s in enumerate(spans[1:])]
    return list(spans)


# ---------------------------------------------------------------- pose
class Pose(dict):
    """eyes, mouth, squash, x, y, paws, extra flags; missing keys = defaults."""
    def __getattr__(self, k):
        return self.get(k, DEFAULT.get(k))


DEFAULT = dict(eyes="open", mouth="dot", squash=0, x=0, y=0, paws=None, star="on",
               tail=0, blush=True, props=())


def face(c, kind, lx, rx, ey, mx, my, p, pal):
    """Eyes at (lx, ey) and (rx, ey), 2 wide; mouth centered at mx, my."""
    e, s = PROP["eye"], PROP["shine"]
    tall = 3 if kind == "mochi" else 2
    eyes = p.eyes
    for x in (lx, rx):
        if eyes in ("open", "left", "right", "up", "wide"):
            dx = {"left": -1, "right": 1}.get(eyes, 0)
            dy = -1 if eyes == "up" else 0
            h = tall + (1 if eyes == "wide" else 0)
            top = ey + dy - (1 if eyes == "wide" else 0)
            for i in range(2):
                for j in range(h):
                    c.put(x + dx + i, top + j, e)
            c.put(x + dx + (1 if eyes == "right" else 0), top, s)
        elif eyes == "blink":
            c.put(x, ey + tall - 1, e)
            c.put(x + 1, ey + tall - 1, e)
        elif eyes == "half":
            c.put(x, ey + tall - 1, e)
            c.put(x + 1, ey + tall - 1, e)
            c.put(x, ey + tall - 2, e)
            c.put(x + 1, ey + tall - 2, e)
        elif eyes == "happy":       # ^ ^
            c.put(x, ey, e)
            c.put(x + 1, ey, e)
            c.put(x - 1, ey + 1, e)
            c.put(x + 2, ey + 1, e)
        elif eyes == "sleep":       # u u (closed, relaxed)
            c.put(x - 1, ey + tall - 2, e)
            c.put(x, ey + tall - 1, e)
            c.put(x + 1, ey + tall - 1, e)
            c.put(x + 2, ey + tall - 2, e)
        elif eyes == "focus":       # > <
            inner = 1 if x == lx else -1
            c.put(x + (0 if inner > 0 else 1), ey, e)
            c.put(x + (1 if inner > 0 else 0), ey + 1, e)
            c.put(x + (0 if inner > 0 else 1), ey + 2 if tall == 3 else ey + 1, e) if tall == 3 else None
    if p.blush:
        for bx in (lx - 2, rx + 2):
            c.put(bx, my, PROP["blush"])
            c.put(bx + 1, my, PROP["blush"])
    m = pal["mouth"]
    if p.mouth == "dot":
        if kind == "kitty":
            c.put(mx - 1, my, m)
            c.put(mx + 1, my, m)
            c.put(mx, my + 1, m)
        else:
            c.put(mx, my, m)
    elif p.mouth == "smile":
        c.put(mx - 1, my, m)
        c.put(mx, my + 1, m)
        c.put(mx + 1, my, m)
    elif p.mouth == "open":
        c.put(mx, my, m)
        c.put(mx, my + 1, m)
        c.put(mx + 1, my, m)
        c.put(mx + 1, my + 1, m)
        c.put(mx + 1 if False else mx, my + 1, "#e0607a")
        c.put(mx + 1, my + 1, "#e0607a")
    elif p.mouth == "o":
        c.put(mx, my, m)
        c.put(mx, my + 1, m)


def paws(c, which, box, col):
    """Little round paws, only when the pose needs them. box = (l, r, top, bottom)."""
    l, r, top, bot = box
    mid = (top + bot) // 2 + 1
    spots = []
    if which in ("hold", "hold_up"):
        spots = [(r + 1, mid)] if which == "hold" else [(r + 1, mid - 2)]
    elif which == "up":
        spots = [(l - 2, top + 3), (r + 1, top + 3)]
    elif which == "up2":
        spots = [(l - 2, top + 2), (r + 1, top + 2)]
    elif which == "wave":
        spots = [(r + 1, mid - 3)]
    elif which == "wave2":
        spots = [(r + 2, mid - 4)]
    elif which in ("type", "type2"):
        a, b = (0, -1) if which == "type" else (-1, 0)
        spots = [(r + 1, bot - 2 + a), (r + 4, bot - 2 + b)]
    elif which == "gem":
        spots = [(r + 1, mid - 3)]
    pc = Canvas()
    for x, y in spots:
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            pc.put(x + dx, y + dy, col["mid"])
        pc.put(x, y, col["hi"])
    return pc


def draw_pet(kind, p):
    pal = PETS[kind]
    c = Canvas()
    if kind == "mochi":
        base = [3, 5, 6, 7, 7.5, 8, 8, 8, 8, 7.5, 7, 6]
        spans = squashed(base, p.squash)
        top = GROUND - len(spans) + p.y   # feet row = GROUND (feet are 1 px)
        top -= 1
        cx = 11 + p.x
        rows = spans_fill(c, spans, top, cx, pal)
        # soft tufts
        c.put(rows[0][0] - 1, top, pal["mid"])
        c.put(rows[0][1] + 1, top, pal["mid"])
        c.put(rows[4][0] - 1, top + 4, pal["mid"])
        c.put(rows[-3][1] + 1, top + len(rows) - 3, pal["shade"])
        box = (min(r[0] for r in rows), max(r[1] for r in rows), top, top + len(rows) - 1)
        if p.paws:
            c.merge(paws(c, p.paws, box, pal))
        outline(c, pal["line"])
        # star on top
        sx, sy = cx, top - 3
        star, hi = (pal["star"], pal["star_hi"]) if p.star != "off" else (pal["star_off"], pal["star_off"])
        for dx, dy in ((0, 0), (-1, 1), (1, 1), (0, 2), (0, 1)):
            c.put(sx + dx, sy + dy, star)
        c.put(sx, sy + 1, hi)
        if p.star == "glow":
            for dx, dy in ((0, -1), (-2, 1), (2, 1)):
                c.put(sx + dx, sy + dy, pal["star_hi"])
        # feet
        if p.y == 0:
            for fx in (cx - 4, cx - 3, cx + 2, cx + 3):
                c.put(fx, GROUND, pal["line"])
        sq = len(base) - len(spans)
        face(c, kind, cx - 4, cx + 2, top + 5 - sq // 2 + (1 if p.squash > 0 else 0) - (1 if p.squash > 0 else 0),
             cx, top + 8 - sq, p, pal)
        return c, box
    # kitty
    base = [5.5, 6.5, 7, 7.5, 8, 8, 8, 8, 8, 7.5, 7, 6]
    spans = squashed(base, p.squash)
    top = GROUND - len(spans) + p.y
    cx = 11.5 + p.x
    rows = spans_fill(c, spans, top, cx, pal)
    l0, r0 = rows[0]
    ears = [(0, -3), (0, -2), (1, -2), (0, -1), (1, -1), (2, -1)]
    for dx, dy in ears:
        c.put(l0 + dx, top + dy, pal["mid"])
        c.put(r0 - dx, top + dy, pal["mid"])
    # tail on the right, two positions
    r_last = rows[-1][1]
    tail = [[(1, -1), (2, -2), (2, -3), (2, -4), (1, -5)],
            [(1, -1), (2, -2), (3, -3), (3, -4), (4, -5)]][p.tail]
    by = top + len(rows) - 1
    for dx, dy in tail:
        c.put(r_last + dx, by + dy, pal["shade"])
    box = (min(r[0] for r in rows), max(r[1] for r in rows), top, by)
    if p.paws:
        c.merge(paws(c, p.paws, box, pal))
    outline(c, pal["line"])
    for dx, dy in ((0, -1), (1, -1), (0, -2)):
        c.put(l0 + dx, top + dy, pal["ear"])
        c.put(r0 - dx, top + dy, pal["ear"])
    if p.y == 0:
        for fx in (int(cx) - 4, int(cx) - 3, int(cx) + 2, int(cx) + 3):
            c.put(fx, GROUND, pal["line"])
    face(c, kind, int(cx) - 4, int(cx) + 3 - (1 if False else 0), top + 5, int(cx), top + 7, p, pal)
    return c, box


# ---------------------------------------------------------------- props
def g(s):
    return s.strip("\n").split("\n")


PICK_UP = g("""
.mmmm.
m..w.m
...w..
..w...
.w....
w.....
""")
PICK_HIT = g("""
....m.
.....m
wwwwwm
.....m
....m.
""")
ROCK = g("""
..kkkk..
.kHrrrk.
krHrrrrk
kkkkkkkk
""")
Z = g("""
zzzzz
...z.
..z..
.z...
zzzzz
""")
z = g("""
zzz
.z.
zzz
""")
BANG = g("""
bb
bb
bb
..
bb
""")
LAPTOP = g("""
.....kk
.....kLk
.....kLk
....kLk.
.kkkkLk.
kdddddddk
.kkkkkkk.
""")
GEM = g("""
.kkk.
kgGgk
kgggk
.kDk.
..k..
""")
BULB = g("""
.kkk.
kyyyk
kyYyk
.kyk.
..k..
""")
PROP_COLORS = {"m": PROP["pick_metal"], "w": PROP["pick_wood"], "k": PROP["outline"],
               "r": PROP["rock"], "H": PROP["rock_hi"], "z": PROP["z"], "b": PROP["bang"],
               "L": PROP["laptop"], "d": PROP["laptop_dark"], "g": PROP["gem"],
               "G": PROP["gem_hi"], "D": PROP["gem_dark"], "y": PROP["bulb"], "Y": "#ffffff"}


def props(c, items, box):
    l, r, top, bot = box
    mid = (top + bot) // 2 + 1
    for item in items:
        name, *args = item if isinstance(item, tuple) else (item,)
        if name == "rock":
            c.grid(ROCK, r + 7, GROUND - 3, PROP_COLORS)
        elif name == "pick_up":
            c.grid(PICK_UP, r + 3, mid - 5, PROP_COLORS)
        elif name == "pick_hit":
            c.grid(PICK_HIT, r + 3, mid - 2, PROP_COLORS)
        elif name == "sparks":
            for dx, dy in ((10, -3), (13, -2), (6, -1), (12, -5)):
                c.put(r + dx, GROUND - 3 + dy, PROP["spark"])
        elif name == "Z":
            dx, dy = args
            c.grid(Z, r + dx, dy, PROP_COLORS)
        elif name == "bang":
            c.grid(BANG, r + 5, top + 1 + (args[0] if args else 0), PROP_COLORS)
        elif name == "laptop":
            c.grid(LAPTOP, r + 2, GROUND - 6, PROP_COLORS)
            if args and args[0]:    # screen light flickers
                c.put(r + 6, GROUND - 4, PROP["screen"])
                c.put(r + 5, GROUND - 3, PROP["screen"])
        elif name == "dots":
            for i in range(args[0]):
                c.put(r + 2 + i * 2, top - 1, PROP["think"])
        elif name == "bulb":
            c.grid(BULB, r + 3, top, PROP_COLORS)
        elif name == "gem":
            c.grid(GEM, r, mid - 8 + (args[0] if args else 0), PROP_COLORS)
        elif name == "confetti":
            seed = args[0]
            pts = [(l - 4, 3), (l - 2, 9), (r + 3, 2), (r + 5, 8), (l + 3, 0), (r - 2, 1),
                   (r + 7, 5), (l - 5, 12)]
            for i, (x, y) in enumerate(pts):
                c.put(x + (seed % 2), (y + seed * 2) % (H - 4), PROP["confetti"][(i + seed) % 6])


def render(kind, pose):
    p = Pose(pose)
    body, box = draw_pet(kind, p)
    c = Canvas()
    back = [x for x in p.props if (x if isinstance(x, str) else x[0]) in ("rock", "laptop")]
    front = [x for x in p.props if x not in back]
    props(c, back, box)
    c.merge(body)
    props(c, front, box)
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
    "sleep":   rep([F(900, eyes="sleep", star="off", props=[("Z", 3, 8)]),
                    F(900, eyes="sleep", star="off", squash=1, props=[("Z", 4, 3)])], 2),
    "doze":    [F(1200, eyes="half"), F(300, eyes="blink"), F(1500, eyes="sleep"), F(300, eyes="half"),
                F(200, eyes="open"), F(800)],
    # ---- starting
    "wake":    [F(700, eyes="sleep", star="off"), F(300, eyes="half"), F(150, eyes="blink"), F(300),
                F(150, eyes="blink"), F(200, star="glow"), F(900, eyes="happy", mouth="smile")],
    # ---- busy
    "mine":    rep([F(380, paws="hold_up", eyes="right", props=["rock", "pick_up"]),
                    F(110, paws="hold", eyes="focus", squash=1, props=["rock", "pick_hit"]),
                    F(260, paws="hold", eyes="focus", squash=1, props=["rock", "pick_hit", "sparks"])], 4),
    "type":    rep([F(140, paws="type", eyes="right", props=[("laptop", True)]),
                    F(140, paws="type2", eyes="right", props=[("laptop", False)])], 8),
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
    with open(os.path.join(out, "pet.css"), "w") as f:
        f.write("/* Generated by ~/.local/lib/pet/pet.py build: one class per pet frame */\n")
        f.write(f"#custom-claude {{ background-size: {W * SCALE // 2}px {H * SCALE // 2}px; }}\n")
        f.write("\n".join(css) + "\n")
    with open(os.path.join(out, "anims.json"), "w") as f:
        json.dump({"width": W * SCALE // 2, "anims": anims}, f)
    print(f"{len(ids)} frames -> {out}")


def sheet(path, bg="#596690"):
    from PIL import Image
    tiles = []
    for kind in PETS:
        for name, seq in ANIMS.items():
            if ONLY.get(name, kind) != kind:
                continue
            for pose, _ in seq[:6]:
                tiles.append(image(render(kind, pose), 4))
    cols, pad = 6, 6
    tw, th = W * 4, H * 4
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
