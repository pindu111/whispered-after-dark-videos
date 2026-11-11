"""Whispered After Dark — "paid editor" Short renderer.

Usage: python3 pro_short.py story.json out.mp4

What it does on top of make_short.py:
  * word-by-word animated captions (Anton, pop-in, active word in red), 1-3 words at a time
  * tight pacing; cinematic transitions between every line (xfade), flash frames on big beats
  * Ken Burns moves that change direction every shot; hook snap-zoom; camera shake + RGB split on the twist
  * film grain, light flicker, vignette, thin red progress bar
  * full sound design: dark pad + music-box lullaby, ducked under the voice, whooshes on every cut,
    heartbeat that builds, riser -> dead silence -> sub-drop on the twist, loudness-normalised master
"""
import json, os, subprocess, sys, re, zlib
import numpy as np
import soundfile as sf
from scipy import signal
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scenes, photos  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
UPSCALE = 2.0                         # zoompan works on an upscaled frame so slow moves stay smooth
HOOK_POS, CAP_POS = (540, 880), (540, 1130)
HOOK_FS, CAP_FS = 172, 158


def configure(landscape=False):
    """Switch every size-dependent setting between vertical Shorts and 16:9 long-form."""
    global W, H, UPSCALE, HOOK_POS, CAP_POS, HOOK_FS, CAP_FS
    if landscape:
        W, H, UPSCALE = 1920, 1080, 1.5
        HOOK_POS, CAP_POS = (960, 520), (960, 800)
        HOOK_FS, CAP_FS = 124, 112
        photos.FETCH_W = 2400
    else:
        W, H, UPSCALE = 1080, 1920, 2.0
        HOOK_POS, CAP_POS = (540, 880), (540, 1130)
        HOOK_FS, CAP_FS = 172, 158
        photos.FETCH_W = 1400
    photos.W, photos.H = W, H
VOICE, SPEED = "am_michael", 0.95
T = 0.25            # transition length
GAP = 0.18          # air after each line
PRE_TWIST = 0.55    # dead silence before the twist line
HOLD_END = 1.5      # how long the twist sits on screen
FONTS = os.path.join(HERE, "fonts")
TRANSITIONS = ["smoothup", "zoomin", "hblur", "fade", "slideleft", "circleopen", "smoothdown", "radial", "dissolve"]


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode:
        raise SystemExit("ffmpeg failed:\n" + r.stderr.decode()[-2000:])


# ------------------------------------------------------------------ voice
def narrate(lines, work):
    from kokoro_onnx import Kokoro
    models = os.environ.get("KOKORO_DIR", f"{HERE}/models")
    k = Kokoro(f"{models}/kokoro-v1.0.onnx", f"{models}/voices-v1.0.bin")
    clips = []
    for i, t in enumerate(lines):
        a, sr = k.create(t, voice=VOICE, speed=SPEED, lang="en-us")
        raw = f"{work}/raw{i:02d}.wav"
        sf.write(raw, a, sr)
        out = f"{work}/vo{i:02d}.wav"
        # slightly deeper, compressed, present, with a short dark room
        run(["ffmpeg", "-y", "-i", raw, "-af",
             "asetrate=24000*0.95,aresample=44100,atempo=1.0526,highpass=f=75,"
             "equalizer=f=180:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=3,"
             "acompressor=threshold=-20dB:ratio=3.5:attack=5:release=120:makeup=4,"
             "aecho=0.85:0.5:45|90:0.12|0.06,alimiter=limit=0.9",
             "-ac", "1", out])
        v, _ = sf.read(out, dtype="float32")
        # trim leading/trailing silence so pacing is tight
        env = np.abs(v)
        idx = np.where(env > env.max() * 0.03)[0]
        v = v[max(0, idx[0] - int(0.02 * SR)): min(len(v), idx[-1] + int(0.12 * SR))]
        clips.append(v)
    return clips


def word_times(text, start, dur):
    """Spread words across the spoken duration, weighted by length, with extra time at punctuation."""
    words = text.split()
    weights = []
    for w in words:
        wt = len(re.sub(r"[^\w']", "", w)) + 1.6
        if re.search(r"[,.;:!?…]\W*$", w):
            wt += 2.2
        weights.append(wt)
    tot = sum(weights)
    out, t = [], start
    for w, wt in zip(words, weights):
        d = dur * wt / tot
        out.append((w, t, t + d))
        t += d
    return out


# ------------------------------------------------------------------ captions (ASS)
def ass_time(t):
    t = max(0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def clean(w):
    w = w.replace("“", "").replace("”", "").replace('"', "")
    w = re.sub(r"[,.;:]+$", "", w)
    return w.upper()


def chunks(words):
    """1-3 words per caption; break after punctuation."""
    cur = []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or re.search(r"[,.;:!?…\"”]\W*$", w[0]):
            yield cur
            cur = []
    if cur:
        yield cur


def write_ass(cards_words, path, hook_end):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Anton,{CAP_FS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,9,5,5,70,70,0,1
Style: Hook,Anton,{HOOK_FS},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,10,6,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    RED, WHITE = r"{\c&H2C2CE8&}", r"{\c&HFFFFFF&}"
    POP = r"{\fscx70\fscy70\t(0,90,\fscx108\fscy108)\t(90,160,\fscx100\fscy100)}"
    ev = []
    # --- hook: the WHOLE line is on screen from frame one; the spoken word lights up red
    hook = cards_words[0]
    hook_end = cards_words[1][0][1] - 0.05 if len(cards_words) > 1 else hook[-1][2] + 1
    for wi, (w, s, e) in enumerate(hook):
        a = 0.0 if wi == 0 else s
        b = hook[wi + 1][1] if wi + 1 < len(hook) else hook_end
        txt = " ".join((RED if j == wi else WHITE) + clean(w2) for j, (w2, _, _) in enumerate(hook))
        anim = ""  # full size on frame one
        ev.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Hook,,0,0,0,,{{\\pos({HOOK_POS[0]},{HOOK_POS[1]})}}{anim}{txt}")
    # --- every other line: 1-3 word groups that pop in, never overlapping
    groups = []
    for ci, words in enumerate(cards_words[1:], 1):
        is_twist = ci == len(cards_words) - 1
        for ch in chunks(words):
            groups.append((ch, ch[-1][2] + (HOLD_END - 0.2 if is_twist and ch is not None else 0.3), is_twist))
    for gi, (ch, c_end, is_twist) in enumerate(groups):
        if gi + 1 < len(groups):
            c_end = min(c_end, groups[gi + 1][0][0][1] - 0.01)
        for wi, (w, s, e) in enumerate(ch):
            end = ch[wi + 1][1] if wi + 1 < len(ch) else c_end
            parts = [(RED if wj == wi else WHITE) + clean(w2) for wj, (w2, _, _) in enumerate(ch) if wj <= wi]
            anim = POP if wi == 0 else ""
            ev.append(f"Dialogue: 0,{ass_time(s)},{ass_time(end)},Cap,,0,0,0,,{{\\pos({CAP_POS[0]},{CAP_POS[1]})}}{anim}{' '.join(parts)}")
    open(path, "w").write(head + "\n".join(ev) + "\n")


# ------------------------------------------------------------------ shots
MOVES = [  # (zoom expr, x expr, y expr) — frames n=on, N=total frames
    ("1.06+0.10*on/{N}", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),                 # push in
    ("1.18-0.10*on/{N}", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),                 # pull out
    ("1.14", "(iw-iw/zoom)*(0.15+0.7*on/{N})", "(ih-ih/zoom)/2"),             # pan right
    ("1.14", "(iw-iw/zoom)*(0.85-0.7*on/{N})", "(ih-ih/zoom)/2"),             # pan left
    ("1.10+0.06*on/{N}", "(iw-iw/zoom)/2", "(ih-ih/zoom)*(0.8-0.6*on/{N})"),  # tilt up + push
]


def shot(i, n, bg_png, length, work):
    frames = int(round(length * FPS))
    if i == 0:  # hook: snap from close crop outward in 0.5s, then slow push
        z = f"if(lt(on,15),1.28-0.18*on/15,1.10+0.04*(on-15)/{frames})"
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    elif i == n - 1:  # twist: slow creeping push-in
        z, x, y = f"1.02+0.16*on/{frames}", "(iw-iw/zoom)/2", "(ih-ih/zoom)*0.45"
    else:
        z, x, y = (m.format(N=frames) for m in MOVES[(i * 3 + 1) % len(MOVES)])
    vf = (f"scale={int(W*UPSCALE)}:{int(H*UPSCALE)}:flags=lanczos,zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS}")
    if i == n - 1:  # shake that dies away + chromatic split
        vf += (f",crop={W-40}:{H-70}:'20+18*exp(-2.2*t)*sin(t*53)':'35+18*exp(-2.2*t)*sin(t*67)',"
               f"scale={W}:{H},rgbashift=rh=5:bh=-5:rv=1:bv=-1")
    vf += ",format=yuv420p"
    out = f"{work}/shot{i:02d}.mp4"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", bg_png, "-vf", vf, "-frames:v", str(frames),
         "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p", out])
    return out


# ------------------------------------------------------------------ sound design
def t2s(t):
    return int(round(t * SR))


def place(buf, clip, t, gain=1.0):
    a = t2s(t)
    if a < 0:
        clip, a = clip[-a:], 0
    if a >= len(buf) or len(clip) == 0:
        return
    b = min(len(buf), a + len(clip))
    buf[a:b] += clip[: b - a] * gain


def boom(dur=2.2):
    t = np.arange(t2s(dur)) / SR
    sub = np.sin(2 * np.pi * (34 + 70 * np.exp(-10 * t)) * t) * np.exp(-1.8 * t)
    crack = np.random.default_rng(3).normal(0, 1, len(t)) * np.exp(-28 * t)
    crack = signal.sosfilt(signal.butter(2, 2500, "low", fs=SR, output="sos"), crack)
    return 0.95 * sub + 0.45 * crack


def whoosh(dur=0.55, seed=0):
    n = t2s(dur)
    t = np.arange(n) / SR
    x = np.random.default_rng(seed).normal(0, 1, n)
    out = np.zeros(n)
    # sweep a band-pass from high to low across the whoosh
    for k, (a, b) in enumerate(zip(np.linspace(0, n, 9)[:-1], np.linspace(0, n, 9)[1:])):
        f = 3800 * (0.55 ** k) + 250
        sos = signal.butter(2, [f * 0.6, min(f * 1.6, SR / 2 - 100)], "band", fs=SR, output="sos")
        seg = signal.sosfilt(sos, x)[int(a):int(b)]
        out[int(a):int(b)] = seg
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return out * env * 0.9


def heartbeat(n_beats, bpm=72):
    gap = 60 / bpm
    total = t2s(gap * n_beats + 0.5)
    buf = np.zeros(total)
    th = np.arange(t2s(0.35)) / SR
    thump = np.sin(2 * np.pi * 48 * th) * np.exp(-14 * th)
    for b in range(n_beats):
        g = 0.35 + 0.65 * b / max(1, n_beats - 1)
        place(buf, thump, b * gap, g)
        place(buf, thump * 0.7, b * gap + 0.22, g)
    return buf


def riser(dur=2.4):
    n = t2s(dur)
    t = np.arange(n) / SR
    noise = np.random.default_rng(9).normal(0, 1, n)
    hp = signal.sosfilt(signal.butter(2, 900, "high", fs=SR, output="sos"), noise)
    tone = np.sin(2 * np.pi * np.cumsum(120 + 700 * (t / dur) ** 2) / SR)
    env = (t / dur) ** 2.2
    return (0.5 * hp + 0.4 * tone) * env


def pad(total):
    """Dark A-minor drone with slow movement."""
    t = np.arange(t2s(total)) / SR
    out = np.zeros_like(t)
    for f, g in ((55, 0.5), (55.4, 0.35), (82.41, 0.3), (110, 0.25), (130.81, 0.18), (164.8, 0.08)):
        saw = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 6))
        out += g * saw * (0.7 + 0.3 * np.sin(2 * np.pi * (0.05 + f / 5000) * t))
    out = signal.sosfilt(signal.butter(2, 650, "low", fs=SR, output="sos"), out)
    return out / (np.abs(out).max() + 1e-9) * 0.6


def music_box(total, start, stop, seed):
    """Sparse, slightly detuned lullaby notes — the classic 'something is wrong' texture."""
    rng = np.random.default_rng(seed)
    scale = [440.0, 523.25, 659.25, 493.88, 587.33, 392.0, 349.23, 329.63]
    buf = np.zeros(t2s(total))
    tn = np.arange(t2s(2.5)) / SR
    t, step = start, 0
    phrase = [0, 2, 1, 3, 0, 4, 5, 7]
    while t < stop:
        f = scale[phrase[step % len(phrase)]] * (1 + rng.normal(0, 0.003))
        note = (np.sin(2 * np.pi * f * tn) + 0.35 * np.sin(2 * np.pi * 2 * f * tn)
                + 0.12 * np.sin(2 * np.pi * 3.01 * f * tn)) * np.exp(-2.6 * tn)
        place(buf, note, t, 0.22)
        t += 0.75 if step % 4 != 3 else 1.5
        step += 1
    # tape-style reverb tail
    ir = np.random.default_rng(1).normal(0, 1, t2s(1.8)) * np.exp(-3.2 * np.arange(t2s(1.8)) / SR)
    wet = signal.fftconvolve(buf, ir)[: len(buf)]
    return buf + wet / (np.abs(wet).max() + 1e-9) * 0.12


def smooth_env(x, ms=60):
    k = t2s(ms / 1000)
    return np.convolve(np.abs(x), np.ones(k) / k, mode="same")


def build_audio(voice_clips, starts, total, twist_start, seed, path):
    n = t2s(total + 0.5)
    vo = np.zeros(n)
    for v, s in zip(voice_clips, starts):
        place(vo, v, s)
    # music bed
    bed = 0.55 * pad(total + 0.5) + music_box(total + 0.5, 1.0, twist_start - 2.6, seed)
    bed = bed[:n]
    # duck under the voice
    duck = 1 - 0.55 * np.clip(smooth_env(vo, 120) / 0.08, 0, 1)
    bed *= duck
    # dead silence before the twist, then everything comes back low under the twist
    cut_a, cut_b = t2s(twist_start - PRE_TWIST), t2s(twist_start)
    fade = t2s(0.12)
    bed[cut_a - fade:cut_a] *= np.linspace(1, 0, fade)
    bed[cut_a:cut_b] = 0
    bed[cut_b:] *= 0.55
    sfx = np.zeros(n)
    place(sfx, boom(), 0.0, 0.75)                                  # opening hit
    for i, s in enumerate(starts[1:], 1):                          # whoosh into every cut
        place(sfx, whoosh(seed=seed + i), max(0, s - 0.3), 0.32)
    beats = max(4, int((twist_start - PRE_TWIST - starts[max(1, len(starts) - 3)]) / (60 / 72)))
    place(sfx, heartbeat(beats), twist_start - PRE_TWIST - beats * 60 / 72, 0.55)
    rz = riser()
    place(sfx, rz, twist_start - PRE_TWIST - len(rz) / SR, 0.35)
    sfx[cut_a:cut_b] *= 0.0
    place(sfx, boom(3.0), twist_start - 0.02, 1.0)                 # sub-drop on the twist
    room = np.random.default_rng(5).normal(0, 1, n)
    room = signal.sosfilt(signal.butter(1, 300, "low", fs=SR, output="sos"), room) * 0.02
    mix = 1.0 * vo + 0.32 * bed + 0.6 * sfx + room
    end = t2s(total)
    mix[end - t2s(1.0):end] *= np.linspace(1, 0, t2s(1.0)) ** 0.5
    mix = mix[:end]
    mix = np.tanh(mix * 1.1) * 0.9  # gentle glue
    stereo = np.stack([mix, mix], 1)
    sf.write(path, stereo.astype("float32"), SR)


# ------------------------------------------------------------------ main
def main(story_path, out, landscape=False, bar=True, end_fade=False, vbitrate=None):
    configure(landscape)
    story = json.load(open(story_path)) if isinstance(story_path, str) else story_path
    cards = story["cards"]
    n = len(cards)
    work = os.path.splitext(out)[0] + "_pro"
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    seed = zlib.crc32(story["title"].encode()) % 5000

    voice = narrate([c["text"] for c in cards], work)
    lens = [len(v) / SR for v in voice]

    # timeline: card i occupies [start_i, start_i + d_i); its voice starts at vstart_i
    d, vstart, t = [], [], 0.0
    for i, L in enumerate(lens):
        lead = 0.05 if i == 0 else (PRE_TWIST + 0.05 if i == n - 1 else T * 0.6)
        tail = HOLD_END if i == n - 1 else GAP
        d.append(lead + L + tail)
        vstart.append(t + lead)
        t += d[-1]
    starts = [sum(d[:i]) for i in range(n)]
    total = sum(d)

    # backgrounds
    pngs = []
    for i, c in enumerate(cards):
        kw = {"target": 92, "contrast": 1.35} if i == 0 and not story.get("plain_hook") else {}
        bg = photos.render(c["photo"], f"{work}/photo{i:02d}.jpg", seed + i, **kw) if c.get("photo") else None
        if bg is None:
            bg = scenes.render(c.get("scene", "dark"), seed + i)
            if landscape:
                bg = photos.cover(bg)
        p = f"{work}/bg{i:02d}.png"
        bg.save(p)
        pngs.append(p)

    shots = [shot(i, n, pngs[i], d[i] + (T if i < n - 1 else 0), work) for i in range(n)]

    # captions
    words = [word_times(c["text"], vs, L) for c, vs, L in zip(cards, vstart, lens)]
    ass = f"{work}/captions.ass"
    write_ass(words, ass, d[0])

    # audio
    mix = f"{work}/mix.wav"
    build_audio(voice, vstart, total, vstart[-1], seed, mix)

    # picture: xfade chain + grain + flicker + flashes + captions + progress bar
    inputs, fc = [], []
    for s in shots:
        inputs += ["-i", s]
    prev = "[0:v]"
    for i in range(1, n):
        tr = TRANSITIONS[(seed + i) % len(TRANSITIONS)]
        if i == n - 1:
            tr = "fadeblack"  # drop to black into the twist
        off = starts[i]
        fc.append(f"{prev}[{i}:v]xfade=transition={tr}:duration={T}:offset={off:.3f}[x{i}]")
        prev = f"[x{i}]"
    flash_at = [starts[n - 1] + PRE_TWIST * 0.9]  # white flash as the twist lands
    if n > 4:
        flash_at.append(starts[n // 2])
    flashes = ",".join(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='between(t,{a:.2f},{a + 0.07:.2f})'"
                       for a in flash_at)
    fc.append(f"{prev}noise=alls=9:allf=t+u,"
              f"eq=brightness='0.012*sin(2*PI*t*6.3)*sin(2*PI*t*2.1)':eval=frame,"
              f"vignette=PI/5,{flashes},"
              f"ass='{ass}':fontsdir='{FONTS}'[cap]")
    if bar:
        fc.append(f"color=c=0xE02828:s={W}x8:r={FPS}[bar]")
        fc.append(f"[cap][bar]overlay=x='-w+w*t/{total:.3f}':y=0:shortest=1,format=yuv420p[v0]")
    else:
        fc.append("[cap]format=yuv420p[v0]")
    fc.append(f"[v0]fade=t=out:st={total - 0.6:.3f}:d=0.6[v]" if end_fade else "[v0]null[v]")
    venc = (["-b:v", vbitrate, "-maxrate", str(int(vbitrate.rstrip('k')) * 3 // 2) + "k",
             "-bufsize", str(int(vbitrate.rstrip('k')) * 3) + "k"] if vbitrate else ["-crf", "18"])
    tmp = out + ".tmp.mp4"
    run(["ffmpeg", "-y", *inputs, "-i", mix, "-filter_complex", ";".join(fc),
         "-map", "[v]", "-map", f"{n}:a", "-t", f"{total:.3f}",
         "-c:v", "libx264", *venc, "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", tmp])
    os.replace(tmp, out)
    print(f"{out}  {total:.1f}s")
    return total


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0], args[1], landscape="--landscape" in sys.argv)
