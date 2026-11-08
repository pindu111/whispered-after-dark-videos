"""Channel logo (800x800) and banner (2560x1440, text kept inside the 1546x423 safe area)."""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

NAME = sys.argv[1] if len(sys.argv) > 1 else "The Quiet Hour"
TAG = "A new scary story every night"
FONT = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"
FONT_I = "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf"
INK, RED, MOON = (6, 5, 8), (200, 30, 36), (225, 220, 205)


def f(path, size, weight):
    ft = ImageFont.truetype(path, size)
    try:
        ft.set_variation_by_axes([weight])
    except Exception:
        pass
    return ft


def gradient(w, h, top, bottom):
    y = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top)[None, None] * (1 - y) + np.array(bottom)[None, None] * y
    return Image.fromarray(np.repeat(a, w, axis=1).astype("uint8"))


def glow(im, box, color, blur, strength):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse(box, fill=strength)
    m = m.filter(ImageFilter.GaussianBlur(blur))
    return Image.composite(Image.new("RGB", im.size, color), im, m)


def crescent(im, cx, cy, r):
    m = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(m)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    md.ellipse([cx - r * 1.55, cy - r * 1.25, cx + r * 0.45, cy + r * 0.75], fill=0)
    return Image.composite(Image.new("RGB", im.size, MOON), im, m)


def house(d, x, base, s):
    """Silhouette house; returns window box so the caller can light it."""
    d.rectangle([x, base - 330 * s, x + 380 * s, base], fill=INK)
    d.polygon([(x - 40 * s, base - 330 * s), (x + 190 * s, base - 520 * s), (x + 420 * s, base - 330 * s)], fill=INK)
    d.rectangle([x + 280 * s, base - 560 * s, x + 330 * s, base - 420 * s], fill=INK)
    return [x + 150 * s, base - 250 * s, x + 230 * s, base - 150 * s]


def light_window(im, box):
    im = glow(im, [box[0] - 60, box[1] - 60, box[2] + 60, box[3] + 60], (220, 140, 60), 40, 150)
    d = ImageDraw.Draw(im)
    d.rectangle(box, fill=(240, 175, 90))
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    w = max(3, int((box[2] - box[0]) * 0.08))
    d.line([cx, box[1], cx, box[3]], fill=INK, width=w)
    d.line([box[0], cy, box[2], cy], fill=INK, width=w)
    # a figure in the lower-left pane
    pw = (box[2] - box[0]) / 2
    d.ellipse([box[0] + pw * 0.3, cy + pw * 0.15, box[0] + pw * 0.7, cy + pw * 0.55], fill=INK)
    d.rectangle([box[0] + pw * 0.32, cy + pw * 0.5, box[0] + pw * 0.68, box[3]], fill=INK)
    return im


def logo(path):
    S = 800
    im = gradient(S, S, (16, 14, 26), (52, 30, 40))
    im = glow(im, [450, 20, 830, 400], (150, 140, 160), 70, 90)
    d = ImageDraw.Draw(im)
    im = crescent(im, 640, 190, 72)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 640), (260, 590), (560, 600), (S, 650), (S, S), (0, S)], fill=INK)
    win = house(d, 215, 640, 0.95)
    im = light_window(im, win)
    # circular safe crop preview edge: keep content inside the middle circle
    out = Image.new("RGB", (S, S), INK)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([0, 0, S, S], fill=255)
    out.paste(im, (0, 0), m)
    out.save(path)


def banner(path):
    W, H = 2560, 1440
    im = gradient(W, H, (12, 12, 22), (46, 30, 40))
    im = glow(im, [1920, 210, 2360, 650], (150, 140, 160), 90, 90)
    d = ImageDraw.Draw(im)
    im = crescent(im, 2140, 430, 60)
    d = ImageDraw.Draw(im)
    # hills + houses along the bottom of the safe band
    d.polygon([(0, 960), (500, 900), (1100, 920), (1700, 880), (W, 950), (W, H), (0, H)], fill=INK)
    win = house(d, 1890, 905, 0.62)
    im = light_window(im, win)
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(4)
    for x in (430, 760, 1720, 2380):  # bare trees
        h = int(rng.integers(260, 380))
        d.rectangle([x - 8, 930 - h, x + 8, 960], fill=INK)
        for k in range(5):
            y = 930 - h + k * 40
            dx = int(rng.integers(40, 110)) * (1 if k % 2 else -1)
            d.line([x, y + 40, x + dx, y], fill=INK, width=6)
    # fog
    fg = Image.new("L", (W, H), 0)
    fd = ImageDraw.Draw(fg)
    for _ in range(30):
        x, y = rng.integers(-400, W), rng.integers(820, 1100)
        fd.ellipse([x, y, x + rng.integers(500, 1200), y + rng.integers(60, 160)], fill=int(rng.integers(15, 40)))
    im = Image.composite(Image.new("RGB", (W, H), (110, 105, 120)), im, fg.filter(ImageFilter.GaussianBlur(70)))
    # text inside the safe area (x 507-2053, y 508-931)
    d = ImageDraw.Draw(im)
    sf = f(FONT_I, 58, 400)
    size = 150  # shrink until the name clears the house (ends before x=1820)
    while True:
        tf = f(FONT, size, 700)
        if d.textlength(NAME, font=tf) <= 1260 or size <= 90:
            break
        size -= 4
    words = NAME.split()
    first, last = " ".join(words[:-1]), words[-1]
    tx, ty = 560, 560 + (150 - size) // 2
    d.text((tx, ty), first + " ", font=tf, fill=(238, 232, 228))
    d.text((tx + d.textlength(first + " ", font=tf), ty), last, font=tf, fill=RED)
    d.text((tx + 6, 760), TAG, font=sf, fill=(190, 182, 182))
    im.save(path)


if __name__ == "__main__":
    logo("brand/logo.png")
    banner("brand/banner.png")
