"""Weekly long-form compilation for Whispered After Dark (1920x1080).

Usage:
  python3 make_weekly.py weekly/WEEK/plan.json                 # render everything missing, then assemble
  python3 make_weekly.py weekly/WEEK/plan.json --piece seg03   # render a single piece (keeps each call short)
  python3 make_weekly.py weekly/WEEK/plan.json --list          # list piece names

plan.json:
  {"title": "...", "stories": ["stories/001-....json", ...], "exclusive": "weekly/WEEK/exclusive.json"}

Output (next to plan.json): video.mp4, thumbnail.jpg, meta.json (YouTube title, description with chapters, tags).
Video is encoded at ~1.2 Mbit/s so an 8-9 minute video stays under GitHub's 100 MB file limit.
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pro_short as ps  # noqa: E402
import photos  # noqa: E402

W, H, FPS = 1920, 1080, 30
VBR = "1200k"
ANTON = os.path.join(HERE, "fonts", "Anton-Regular.ttf")
REPO = os.path.dirname(HERE)


def ff(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode:
        raise SystemExit("ffmpeg failed:\n" + r.stderr.decode()[-2000:])


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return float(out.strip())


def load(path):
    return json.load(open(os.path.join(REPO, path) if not os.path.isabs(path) else path))


def first_photo(story):
    for c in story["cards"]:
        if c.get("photo"):
            return c["photo"]
    return None


def graded_bg(url, dest, seed, target=48, blur=0):
    ps.configure(landscape=True)
    im = photos.render(url, dest, seed, target=target) if url else None
    if im is None:
        im = photos.cover(ps.scenes.render("dark", seed))
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


def text_center(d, y, txt, font, fill, stroke=6):
    w = d.textlength(txt, font=font)
    d.text(((W - w) / 2, y), txt, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


# ------------------------------------------------------------------ pieces
def chapter_card(label, title, url, seed, out, length=2.6):
    work = out + "_work"
    os.makedirs(work, exist_ok=True)
    im = graded_bg(url, f"{work}/bg.jpg", seed, target=40, blur=5)
    d = ImageDraw.Draw(im)
    text_center(d, 380, label.upper(), ImageFont.truetype(ANTON, 70), (224, 40, 40), 4)
    big = ImageFont.truetype(ANTON, 160)
    while d.textlength(title.upper(), font=big) > W - 200 and big.size > 80:
        big = ImageFont.truetype(ANTON, big.size - 8)
    text_center(d, 480, title.upper(), big, (245, 241, 236), 8)
    png = f"{work}/card.png"
    im.save(png)
    frames = int(length * FPS)
    vf = (f"scale=2880:1620,zoompan=z='1.0+0.05*on/{frames}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={frames}:"
          f"s={W}x{H}:fps={FPS},noise=alls=8:allf=t+u,vignette=PI/5,fade=t=in:st=0:d=0.3,"
          f"fade=t=out:st={length - 0.35:.2f}:d=0.35,setsar=1,format=yuv420p")
    # sound: whoosh in, low hit, a breath of drone
    n = int(length * ps.SR)
    a = np.zeros(n)
    ps.place(a, ps.whoosh(seed=seed), 0.0, 0.5)
    ps.place(a, ps.boom(2.0), 0.28, 0.6)
    a += 0.18 * ps.pad(length)[:n] * np.linspace(0.3, 1, n) * np.linspace(1, 0, n) ** 0.5
    wav = f"{work}/a.wav"
    sf.write(wav, np.stack([a, a], 1).astype("float32") * 0.8, ps.SR)
    ff(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", png, "-i", wav, "-vf", vf,
        "-frames:v", str(frames), "-c:v", "libx264", "-b:v", VBR, "-maxrate", "1800k", "-bufsize", "3600k",
        "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-af", "loudnorm=I=-16:TP=-1.5", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", out])


def mini_story(texts, photo_urls, title):
    return {"title": title, "plain_hook": True,
            "cards": [{"text": t, "scene": "dark", "photo": u} for t, u in zip(texts, photo_urls)]}


def thumbnail(url, out, seed, line1="DON'T WATCH", line2="ALONE"):
    ps.configure(landscape=True)
    im = photos.render(url, out + "_bg.jpg", seed, target=85, contrast=1.4) if url else None
    if im is None:
        im = photos.cover(ps.scenes.render("window", seed))
    im = im.resize((1280, 720), Image.LANCZOS)
    # red glow behind the words
    glow = Image.new("L", im.size, 0)
    ImageDraw.Draw(glow).ellipse([80, 200, 900, 700], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    im = Image.composite(Image.new("RGB", im.size, (150, 10, 14)), im, glow)
    d = ImageDraw.Draw(im)
    f1, f2 = ImageFont.truetype(ANTON, 150), ImageFont.truetype(ANTON, 200)
    d.text((60, 190), line1, font=f1, fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0))
    d.text((60, 350), line2, font=f2, fill=(230, 32, 36), stroke_width=12, stroke_fill=(0, 0, 0))
    im.save(out, quality=92)


# ------------------------------------------------------------------ plan
def pieces(plan, base):
    stories = [load(p) for p in plan["stories"]]
    exclusive = load(plan["exclusive"]) if plan.get("exclusive") else None
    hook_photo = first_photo(exclusive) if exclusive else first_photo(stories[0])
    k = len(stories)
    nums = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
    intro_lines = [f"{nums[k] if k < len(nums) else k} stories from this week."]
    intro_photos = [first_photo(stories[0])]
    if exclusive:
        intro_lines.append("And one you've never heard before.")
        intro_photos.append(first_photo(stories[len(stories) // 2]))
    intro_lines.append("Don't watch these alone.")
    intro_photos.append(hook_photo)
    out = [("intro", "story", mini_story(intro_lines, intro_photos, "intro-" + plan["title"]), "Intro")]
    for i, s in enumerate(stories, 1):
        out.append((f"ch{i:02d}", "card", (f"Story {i}", s["title"], first_photo(s)), None))
        out.append((f"seg{i:02d}", "story", s, s["title"]))
    if exclusive:
        out.append(("chx", "card", ("Exclusive: only on the long video", exclusive["title"], first_photo(exclusive)), None))
        out.append(("segx", "story", exclusive, exclusive["title"] + " (exclusive)"))
    out.append(("outro", "story", mini_story(
        ["That's every story this week.", "A new one tonight. Subscribe."],
        [first_photo(stories[-1]), hook_photo], "outro-" + plan["title"]), None))
    return out, hook_photo


def render_piece(name, kind, payload, base, seed):
    path = os.path.join(base, "pieces", f"{name}.mp4")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path.replace(".mp4", ".part.mp4")
    if kind == "card":
        chapter_card(*payload, seed=seed, out=tmp)
    else:
        ps.main(payload, tmp, landscape=True, bar=False, end_fade=True, vbitrate=VBR)
    os.replace(tmp, path)
    print("rendered", name, f"{dur(path):.1f}s")
    return path


def fmt(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def main():
    plan_path = sys.argv[1]
    base = os.path.dirname(os.path.abspath(plan_path))
    plan = json.load(open(plan_path))
    items, hook_photo = pieces(plan, base)
    if "--list" in sys.argv:
        print(" ".join(n for n, *_ in items))
        return
    only = sys.argv[sys.argv.index("--piece") + 1] if "--piece" in sys.argv else None
    paths = []
    for idx, (name, kind, payload, chapter) in enumerate(items):
        if only and name != only:
            continue
        paths.append((render_piece(name, kind, payload, base, 100 + idx), chapter, name))
    if only:
        return
    # assemble (all pieces share codec settings, so a stream copy is enough)
    lst = os.path.join(base, "pieces", "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p, _, _ in paths))
    video = os.path.join(base, "video.mp4")
    ff(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", video])
    # chapters: each chapter starts at its title card
    chapters, t, pending = [], 0.0, None
    for p, chapter, name in paths:
        if name.startswith("ch"):
            pending = t
        if chapter:
            chapters.append((pending if pending is not None else t, chapter))
            pending = None
        t += dur(p)
    chapters[0] = (0.0, chapters[0][1])
    thumb = os.path.join(base, "thumbnail.jpg")
    thumbnail(hook_photo, thumb, 7)
    credits = sorted({c.get("photo_credit") for p in plan["stories"] + ([plan["exclusive"]] if plan.get("exclusive") else [])
                      for c in load(p)["cards"] if c.get("photo_credit")})
    desc = (plan.get("teaser", "Seven original scary stories from this week, plus one you won't find anywhere else.")
            + "\n\nTurn the lights off. Headphones on.\n\n"
            + "\n".join(f"{fmt(s)} {c}" for s, c in chapters)
            + "\n\nA new original scary story every night on Whispered After Dark."
            + (f"\n\nPhotos: {', '.join(credits)} on Unsplash" if credits else "")
            + "\n\n#scarystories #horrorstories #creepy #scary")
    meta = {"youtube_title": plan["title"], "description": desc, "duration": dur(video),
            "tags": ["scary stories", "horror stories", "scary stories to fall asleep to", "creepy stories",
                     "true scary stories", "horror compilation", "whispered after dark"],
            "chapters": [[fmt(s), c] for s, c in chapters]}
    json.dump(meta, open(os.path.join(base, "meta.json"), "w"), indent=2)
    print(video, f"{meta['duration'] / 60:.1f} min", f"{os.path.getsize(video) / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
