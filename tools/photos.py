"""Turn an Unsplash photo into a dark, graded 1080x1920 horror frame."""
import os
import urllib.request
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

W, H = 1080, 1920


def fetch(url, dest):
    """Download once; returns the local path or None on any failure."""
    if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
        return dest
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query))
    q.update({"w": "1400", "fm": "jpg", "q": "85"})  # 1400px wide is plenty for 1080 output
    url = urlunsplit(parts._replace(query=urlencode(q)))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "whispered-after-dark"})
        with urllib.request.urlopen(req, timeout=40) as r, open(dest, "wb") as f:
            f.write(r.read())
        Image.open(dest).verify()
        return dest
    except Exception as e:
        print(f"photo download failed ({e}); using illustration")
        return None


def cover(im):
    """Scale and centre-crop to fill 1080x1920."""
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def grade(im, seed):
    """Cold, desaturated, crushed blacks, vignette and grain, so every photo matches the channel look."""
    im = cover(im.convert("RGB"))
    im = ImageEnhance.Color(im).enhance(0.5)
    im = ImageEnhance.Contrast(im).enhance(1.15)
    a = np.asarray(im).astype(float)
    # bring every photo to the same moody exposure: dark photos are lifted, bright ones pulled down
    mean = a.mean() + 1e-6
    a = a * np.clip(68 / mean, 0.35, 3.0)
    a = a * np.array([0.92, 0.97, 1.08])  # cold tint
    a = np.clip((a - 6) * 1.04, 0, 255)  # slightly crushed blacks
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H * 0.45) / (H * 0.62)) ** 2)
    a *= np.clip(1 - d ** 2 * 0.9, 0.1, 1)[..., None]
    a += np.random.default_rng(seed).normal(0, 6, (H, W, 1))
    im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"))
    return im.filter(ImageFilter.GaussianBlur(0.4))


def render(url, dest, seed):
    p = fetch(url, dest)
    return grade(Image.open(p), seed) if p else None
