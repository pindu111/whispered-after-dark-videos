"""Procedural horror illustrations (1080x1920). Each scene returns an RGB PIL image."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1080, 1920
INK = (6, 5, 8)


def _rng(seed):
    return np.random.default_rng(seed)


def sky(seed, top=(14, 16, 28), bottom=(46, 38, 52), moon=None):
    y = np.linspace(0, 1, H)[:, None, None]
    img = np.array(top)[None, None] * (1 - y) + np.array(bottom)[None, None] * y
    img = np.repeat(img, W, axis=1)
    im = Image.fromarray(img.astype("uint8"))
    if moon:
        mx, my, r = moon
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse([mx - r * 4, my - r * 4, mx + r * 4, my + r * 4], fill=70)
        glow = glow.filter(ImageFilter.GaussianBlur(r * 1.6))
        im = Image.composite(Image.new("RGB", (W, H), (150, 150, 170)), im, glow)
        d = ImageDraw.Draw(im)
        d.ellipse([mx - r, my - r, mx + r, my + r], fill=(222, 218, 205))
        rng = _rng(seed)
        for _ in range(7):  # craters
            cx, cy = mx + rng.integers(-r // 2, r // 2), my + rng.integers(-r // 2, r // 2)
            cr = int(rng.integers(r // 10, r // 4))
            d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(200, 196, 185))
    return im


def fog(im, seed, amount=1.0, y0=0.55, color=(120, 115, 130)):
    rng = _rng(seed + 7)
    f = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(f)
    for _ in range(26):
        x, y = rng.integers(-400, W), rng.integers(int(H * y0), H)
        d.ellipse([x, y, x + rng.integers(500, 1100), y + rng.integers(80, 220)], fill=int(rng.integers(15, 45) * amount))
    f = f.filter(ImageFilter.GaussianBlur(70))
    return Image.composite(Image.new("RGB", (W, H), color), im, f)


def tree(d, x, base, h, seed, width=26):
    rng = _rng(seed)

    def branch(x0, y0, ang, length, w, depth):
        if depth == 0 or length < 12:
            return
        x1 = x0 + math.cos(ang) * length
        y1 = y0 - math.sin(ang) * length
        d.line([x0, y0, x1, y1], fill=INK, width=max(1, int(w)))
        for _ in range(2 if depth > 2 else 3):
            branch(x1, y1, ang + rng.uniform(-0.7, 0.7), length * rng.uniform(0.6, 0.78), w * 0.68, depth - 1)

    d.polygon([(x - width, base), (x + width, base), (x + width * 0.4, base - h * 0.55), (x - width * 0.4, base - h * 0.55)], fill=INK)
    branch(x, base - h * 0.5, math.pi / 2 + rng.uniform(-0.15, 0.15), h * 0.32, width * 0.8, 7)


def vignette(im, strength=0.85):
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H * 0.45) / (H * 0.62)) ** 2)
    m = np.clip(1 - (d ** 2) * strength, 0.08, 1)[..., None]
    return Image.fromarray((np.asarray(im).astype(float) * m).astype("uint8"))


def grain(im, seed, amt=7):
    a = np.asarray(im).astype(float) + _rng(seed).normal(0, amt, (H, W, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8"))


def finish(im, seed, tint=(1.0, 0.92, 1.0)):
    a = np.asarray(im).astype(float) * np.array(tint)
    im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
    return grain(vignette(im), seed)


# ---------------------------------------------------------------- scenes
def house(seed):
    im = sky(seed, moon=(780, 420, 95))
    im = fog(im, seed, 0.7, 0.35)
    d = ImageDraw.Draw(im)
    hill = [(0, 1260), (300, 1160), (620, 1130), (900, 1190), (W, 1240), (W, H), (0, H)]
    d.polygon(hill, fill=INK)
    # house
    hx, hy = 330, 1150
    d.rectangle([hx, hy - 330, hx + 380, hy], fill=INK)
    d.polygon([(hx - 40, hy - 330), (hx + 190, hy - 520), (hx + 420, hy - 330)], fill=INK)
    d.rectangle([hx + 280, hy - 560, hx + 330, hy - 420], fill=INK)  # chimney
    d.polygon([(hx + 120, hy - 420), (hx + 190, hy - 480), (hx + 260, hy - 420)], fill=INK)  # gable
    lit = Image.new("L", (W, H), 0)
    ld = ImageDraw.Draw(lit)
    ld.rectangle([hx + 60, hy - 250, hx + 130, hy - 160], fill=255)
    glow = lit.filter(ImageFilter.GaussianBlur(28))
    im = Image.composite(Image.new("RGB", (W, H), (220, 150, 70)), im, ImageChops.multiply(glow, Image.new("L", (W, H), 150)))
    im.paste((235, 170, 90), (hx + 60, hy - 250, hx + 130, hy - 160))
    d = ImageDraw.Draw(im)
    d.line([hx + 95, hy - 250, hx + 95, hy - 160], fill=INK, width=6)
    d.line([hx + 60, hy - 205, hx + 130, hy - 205], fill=INK, width=6)
    tree(d, 140, 1300, 900, seed + 1, 30)
    tree(d, 960, 1330, 760, seed + 2, 24)
    im = fog(im, seed + 3, 0.9, 0.7)
    return finish(im, seed)


def hallway(seed):
    im = Image.new("RGB", (W, H), (20, 18, 24))
    d = ImageDraw.Draw(im)
    vx, vy = W // 2, 860
    dw, dh = 170, 330  # far door size
    # walls / floor / ceiling as shaded polygons
    d.polygon([(0, 0), (vx - dw, vy - dh), (vx - dw, vy + dh * 0.6), (0, H)], fill=(30, 26, 32))
    d.polygon([(W, 0), (vx + dw, vy - dh), (vx + dw, vy + dh * 0.6), (W, H)], fill=(24, 21, 27))
    d.polygon([(0, H), (vx - dw, vy + dh * 0.6), (vx + dw, vy + dh * 0.6), (W, H)], fill=(16, 13, 16))
    d.polygon([(0, 0), (vx - dw, vy - dh), (vx + dw, vy - dh), (W, 0)], fill=(12, 11, 15))
    # floorboards
    for i in range(-6, 7):
        d.line([vx + i * 40, vy + dh * 0.6, vx + i * 260, H], fill=(10, 8, 10), width=3)
    # side doors
    for side in (-1, 1):
        for t in (0.25, 0.55):
            x0 = vx + side * (dw + (W / 2 - dw) * (1 - t))
            x1 = vx + side * (dw + (W / 2 - dw) * (1 - t - 0.12))
            top = vy - dh - (vy - dh) * (1 - t) * 0.75
            bot = vy + dh * 0.6 + (H - vy - dh * 0.6) * (1 - t) * 0.95
            d.polygon([(x0, top), (x1, top + 30 * side * 0), (x1, bot), (x0, bot)], fill=(9, 8, 11))
    # far door ajar with light
    d.rectangle([vx - 80, vy - 210, vx + 80, vy + dh * 0.6], fill=(5, 4, 6))
    light = Image.new("L", (W, H), 0)
    ImageDraw.Draw(light).polygon([(vx + 40, vy - 210), (vx + 80, vy - 210), (vx + 80, vy + dh * 0.6), (vx + 40, vy + dh * 0.6)], fill=255)
    ImageDraw.Draw(light).polygon([(vx + 40, vy + dh * 0.6), (vx + 80, vy + dh * 0.6), (vx + 420, H), (vx + 120, H)], fill=90)
    im = Image.composite(Image.new("RGB", (W, H), (210, 190, 150)), im, light.filter(ImageFilter.GaussianBlur(10)))
    # figure silhouette in the gap
    d = ImageDraw.Draw(im)
    d.ellipse([vx + 46, vy - 150, vx + 76, vy - 112], fill=INK)
    d.rectangle([vx + 48, vy - 112, vx + 74, vy + 60], fill=INK)
    return finish(im, seed, (1.0, 0.95, 0.95))


def table(seed, plates=3):
    im = Image.new("RGB", (W, H), (22, 18, 20))
    d = ImageDraw.Draw(im)
    # lamp cone
    cone = Image.new("L", (W, H), 0)
    ImageDraw.Draw(cone).polygon([(W / 2 - 60, 520), (W / 2 + 60, 520), (W / 2 + 560, 1500), (W / 2 - 560, 1500)], fill=110)
    im = Image.composite(Image.new("RGB", (W, H), (200, 170, 120)), im, cone.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(im)
    d.line([W / 2, 0, W / 2, 440], fill=INK, width=6)
    d.polygon([(W / 2 - 110, 540), (W / 2 + 110, 540), (W / 2 + 40, 440), (W / 2 - 40, 440)], fill=INK)
    d.ellipse([W / 2 - 30, 520, W / 2 + 30, 560], fill=(255, 225, 160))
    # table top (perspective ellipse)
    d.ellipse([80, 1080, W - 80, 1520], fill=(40, 28, 22))
    d.ellipse([80, 1060, W - 80, 1500], fill=(66, 46, 34))
    d.rectangle([150, 1290, 190, 1800], fill=INK)
    d.rectangle([W - 190, 1290, W - 150, 1800], fill=INK)
    pos = [(W / 2 - 250, 1270), (W / 2 + 250, 1270), (W / 2, 1180)][:plates]
    for i, (px, py) in enumerate(pos):
        d.ellipse([px - 120, py - 50, px + 120, py + 50], fill=(196, 190, 180))
        d.ellipse([px - 80, py - 32, px + 80, py + 32], fill=(170, 164, 156))
        d.line([px - 150, py - 30, px - 150, py + 40], fill=(150, 150, 150), width=6)
        d.line([px + 150, py - 30, px + 150, py + 40], fill=(150, 150, 150), width=6)
    # empty chair behind the far plate
    d.rectangle([W / 2 - 110, 880, W / 2 + 110, 1110], fill=INK)
    d.rectangle([W / 2 - 90, 900, W / 2 + 90, 1090], fill=(14, 11, 12))
    return finish(im, seed)


def window(seed, figure=True):
    im = sky(seed, (10, 14, 26), (30, 34, 50), moon=(640, 600, 80))
    rng = _rng(seed)
    d = ImageDraw.Draw(im)
    for i in range(9):
        tree(d, int(rng.integers(0, W)), 1500, int(rng.integers(700, 1100)), seed + 10 + i, 18)
    if figure:
        fx = 430
        d.ellipse([fx - 50, 830, fx + 50, 950], fill=INK)
        d.polygon([(fx - 40, 940), (fx + 40, 940), (fx + 110, 1500), (fx - 110, 1500)], fill=INK)
    im = fog(im, seed, 1.0, 0.6)
    # room / window frame
    frame = Image.new("RGB", (W, H), (12, 10, 13))
    mask = Image.new("L", (W, H), 255)
    md = ImageDraw.Draw(mask)
    md.rectangle([170, 380, W - 170, 1500], fill=0)
    im = Image.composite(frame, im, mask)
    d = ImageDraw.Draw(im)
    d.rectangle([170, 380, W - 170, 1500], outline=(28, 24, 26), width=34)
    d.line([W / 2, 380, W / 2, 1500], fill=(28, 24, 26), width=26)
    d.line([170, 940, W - 170, 940], fill=(28, 24, 26), width=26)
    d.rectangle([120, 1500, W - 120, 1560], fill=(34, 28, 30))
    # rain streaks / condensation
    for _ in range(90):
        x, y = rng.integers(190, W - 190), rng.integers(400, 1480)
        d.line([x, y, x + 1, y + rng.integers(10, 50)], fill=(90, 95, 115), width=2)
    return finish(im, seed, (0.9, 0.95, 1.05))


def forest(seed):
    im = sky(seed, (8, 12, 14), (34, 44, 44), moon=(300, 330, 60))
    rng = _rng(seed)
    for layer, (shade, n, wid) in enumerate([((30, 36, 38), 10, 14), ((18, 22, 24), 8, 22), (INK, 6, 36)]):
        d = ImageDraw.Draw(im)
        for i in range(n):
            x = int(rng.integers(-40, W + 40))
            d.rectangle([x - wid, 0, x + wid, H], fill=shade)
        im = fog(im, seed + layer * 5, 0.8, 0.2 + layer * 0.15, (70, 85, 85))
    d = ImageDraw.Draw(im)
    d.polygon([(W / 2 - 40, 1150), (W / 2 + 40, 1150), (W / 2 + 420, H), (W / 2 - 420, H)], fill=(40, 42, 38))
    # two eyes in the dark
    for ex in (W / 2 + 228, W / 2 + 270):
        d.ellipse([ex - 9, 1040, ex + 9, 1052], fill=(200, 210, 170))
    return finish(im, seed, (0.9, 1.0, 0.98))


def door(seed):
    im = Image.new("RGB", (W, H), (20, 17, 19))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 90):  # wallpaper stripes
        d.rectangle([x, 0, x + 40, H], fill=(24, 20, 22))
    d.rectangle([240, 300, W - 240, 1640], fill=(34, 24, 20))
    for y0, y1 in ((380, 900), (980, 1560)):
        d.rectangle([310, y0, W - 310, y1], outline=(24, 16, 14), width=14)
    d.ellipse([W - 340, 990, W - 300, 1030], fill=(120, 100, 60))
    d.rectangle([0, 1640, W, H], fill=(12, 10, 10))
    light = Image.new("L", (W, H), 0)
    ImageDraw.Draw(light).polygon([(240, 1640), (W - 240, 1640), (W - 100, H), (100, H)], fill=150)
    im = Image.composite(Image.new("RGB", (W, H), (210, 180, 120)), im, light.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(im)
    d.rectangle([240, 1634, W - 240, 1646], fill=(255, 220, 160))
    # two shadows of feet under the door
    for fx in (W / 2 - 90, W / 2 + 40):
        d.rectangle([fx, 1634, fx + 60, 1646], fill=INK)
    return finish(im, seed)


def note(seed):
    im = table(seed, plates=0)
    d = ImageDraw.Draw(im)
    px, py = W / 2, 1270
    d.ellipse([px - 170, py - 70, px + 170, py + 70], fill=(170, 164, 156))
    paper = Image.new("RGBA", (300, 200), (225, 215, 190, 255))
    pd = ImageDraw.Draw(paper)
    for i in range(5):
        pd.line([30, 40 + i * 30, 30 + 230 - (i % 2) * 60, 40 + i * 30 + (i % 3)], fill=(60, 40, 40, 255), width=4)
    paper = paper.rotate(-12, expand=True)
    im.paste(paper, (int(px - paper.width / 2), int(py - paper.height / 2 - 20)), paper)
    return im


def dark(seed):
    im = Image.new("RGB", (W, H), (14, 10, 12))
    im = fog(im, seed, 1.2, 0.0, (60, 30, 34))
    return finish(im, seed)


SCENES = {"house": house, "hallway": hallway, "table": table, "window": window,
          "forest": forest, "door": door, "note": note, "dark": dark}


def render(name, seed):
    return SCENES.get(name, dark)(seed)
