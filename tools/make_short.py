"""Render a narrated, illustrated scary-story YouTube Short (1080x1920, 30fps).

Usage: python3 make_short.py story.json out.mp4
story.json: {"title": "...", "title_scene": "house",
             "cards": [{"text": "...", "scene": "table"}, ...], "outro": "..."}
Scenes: house hallway table window forest door note dark
"""
import json, os, subprocess, sys, textwrap, zlib
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import scenes

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"
FONT_I = "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf"
VOICE, SPEED = "am_michael", 0.9
PAD = 0.55  # silence after each line


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


# scenes whose subject sits low on screen get their caption up top
TOP_CAPTION = {"table", "note", "door"}


def caption(im, text, kind, scene=""):
    im = im.copy()
    d = ImageDraw.Draw(im)
    if kind == "title":
        f, wrap, y_mid = font(FONT, 112, 700), 13, H * 0.20
    elif kind == "outro":
        f, wrap, y_mid = font(FONT_I, 64, 400), 22, H * 0.66
    else:
        f, wrap, y_mid = font(FONT, 70, 600), 22, (H * 0.26 if scene in TOP_CAPTION else H * 0.68)
    lines = textwrap.wrap(text, wrap)
    lh = int(f.size * 1.3)
    top = int(y_mid - lh * len(lines) / 2)
    # dark band behind the words so they read over any scene
    band = Image.new("L", (W, H), 0)
    ImageDraw.Draw(band).rectangle([0, top - 70, W, top + lh * len(lines) + 70], fill=170)
    band = band.filter(ImageFilter.GaussianBlur(50))
    im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, band)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=f)
        sd.text(((W - tw) / 2 + 3, top + i * lh + 5), ln, font=f, fill=(0, 0, 0, 255))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    im.paste(sh, (0, 0), sh)
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=f)
        col = (205, 32, 36) if kind == "title" and i == len(lines) - 1 else (240, 236, 232)
        d.text(((W - tw) / 2, top + i * lh), ln, font=f, fill=col)
    return im


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode:
        raise SystemExit(r.stderr.decode()[-1500:])


def narrate(lines, work):
    from kokoro_onnx import Kokoro
    models = os.environ.get("KOKORO_DIR", f"{HERE}/models")
    k = Kokoro(f"{models}/kokoro-v1.0.onnx", f"{models}/voices-v1.0.bin")
    out = []
    for i, t in enumerate(lines):
        a, sr = k.create(t, voice=VOICE, speed=SPEED, lang="en-us")
        p = f"{work}/v{i:02d}.wav"
        sf.write(p, np.concatenate([a, np.zeros(int(sr * PAD), a.dtype)]), sr)
        out.append((p, len(a) / sr + PAD))
    return out


def main(story_path, out):
    story = json.load(open(story_path))
    work = os.path.splitext(out)[0] + "_parts"
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    outro = story.get("outro", "Follow for a new story every night.")
    # cold open: the hook line plays from frame one; the title lives only in the YouTube title
    items = [(c["text"], c.get("scene", "dark"), "body") for c in story["cards"]]
    items += [(outro, "dark", "outro")]
    voice = narrate([t for t, _, _ in items], work)

    base = zlib.crc32(story["title"].encode()) % 5000  # different art per story
    parts = []
    for i, ((text, scene, kind), (_, dur)) in enumerate(zip(items, voice)):
        dur = max(dur, 2.2)
        png = f"{work}/s{i:02d}.png"
        caption(scenes.render(scene, base + i), text, kind, scene).save(png)
        frames = int(round(dur * FPS))
        tmp, final = f"{work}/s{i:02d}.tmp.mp4", f"{work}/s{i:02d}.mp4"
        drift = "+0.06" if i % 2 else "-0.06"  # alternate slow pan direction
        vf = (f"scale=1296:2304,zoompan=z='1.04+0.07*on/{frames}'"
              f":x='(iw-iw/zoom)/2*(1{drift}*on/{frames})':y='(ih-ih/zoom)/2'"
              f":d={frames}:s={W}x{H}:fps={FPS},format=yuv420p,"
              + ("" if i == 0 else "fade=t=in:st=0:d=0.35,")  # first frame fully visible
              + f"fade=t=out:st={dur - 0.35:.2f}:d=0.35")
        run(["ffmpeg", "-y", "-i", png, "-vf", vf, "-frames:v", str(frames), "-c:v", "libx264",
             "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp])
        os.replace(tmp, final)
        parts.append((final, frames / FPS))

    total = sum(d for _, d in parts)
    open(f"{work}/list.txt", "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p, _ in parts))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt", "-c", "copy", f"{work}/silent.mp4"])

    # narration track: each clip padded to its scene length, joined in order
    vlist = []
    for i, ((p, _), (_, d)) in enumerate(zip(voice, parts)):
        q = f"{work}/vp{i:02d}.wav"
        run(["ffmpeg", "-y", "-i", p, "-af", f"apad=whole_dur={d:.3f}", "-ar", "44100", "-ac", "1", q])
        vlist.append(q)
    open(f"{work}/vlist.txt", "w").write("".join(f"file '{os.path.abspath(q)}'\n" for q in vlist))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{work}/vlist.txt", f"{work}/voice.wav"])

    drone = (f"aevalsrc='0.20*sin(2*PI*55*t)+0.15*sin(2*PI*55.7*t)+0.07*sin(2*PI*82.4*t)"
             f"+0.05*sin(2*PI*110.9*t)*sin(2*PI*0.13*t)':s=44100:d={total:.3f}")
    fc = ("[0]asetrate=44100*0.95,aresample=44100,atempo=1.0526,"
          "aecho=0.8:0.55:70|140:0.22|0.12,highpass=f=70,volume=1.6[v];"
          "[2]lowpass=f=400[n];[1][n]amix=inputs=2:normalize=0,tremolo=f=0.25:d=0.35,volume=0.45[bg];"
          f"[v][bg]amix=inputs=2:normalize=0,afade=t=in:d=0.05,afade=t=out:st={total - 1.5:.2f}:d=1.5,"
          "volume=5dB,alimiter=limit=0.95,pan=stereo|c0=c0|c1=c0[a]")
    run(["ffmpeg", "-y", "-i", f"{work}/voice.wav", "-f", "lavfi", "-i", drone,
         "-f", "lavfi", "-i", f"anoisesrc=c=brown:a=0.06:d={total:.3f}",
         "-filter_complex", fc, "-map", "[a]", "-c:a", "aac", "-b:a", "160k", f"{work}/mix.m4a"])
    tmp = out + ".tmp.mp4"
    run(["ffmpeg", "-y", "-i", f"{work}/silent.mp4", "-i", f"{work}/mix.m4a", "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", tmp])
    os.replace(tmp, out)
    print(f"{out}  {total:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
