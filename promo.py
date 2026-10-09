"""آگهی رسانه ایرانا: آوای بانو روی آهنگی شکوهمند (ساخته‌ی خود ما)، به‌صورت mp3 و ویدیوی عمودی.

اجرا در GitHub Actions (کارگاه «آگهی ایرانا»):
  PROMO_VOICES="نام:شناسه,نام:شناسه"  python3 promo.py
خروجی‌ها در پوشه‌ی _promo.
"""
import json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("PROMO_DIR", os.path.join(HERE, "_promo"))
SR = 44100
API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
MODELS = [m for m in os.environ.get("TTS_MODELS", "eleven_v3,eleven_multilingual_v2").split(",") if m]

# متن آگهی: هر سطر جداگانه خوانده می‌شود؛ عدد پس از آن، درنگ پس از سطر (ثانیه) است.
SCRIPT = [
    ("رسانه ایرانا.", 0.9),
    ("تازه‌ترین رویدادهای ایران.", 0.6),
    ("شبانروزی، سر هر ساعت کشور.", 1.3),
    ("از خیابان‌های ایران تا پایتخت‌های جهان، از ایستادگی مردم تا گام‌های آزادی‌خواهان، "
     "و سخنان شاهزاده رضا پهلوی، شهریار ایران.", 0.9),
    ("هر ساعت، با صدای ایران، در راه رهایی و آزادی.", 1.2),
    ("رادیو ایرانا را در تلگرام بشنوید، و اپ ایرانا را بر گوشی خود بنشانید.", 1.4),
    ("رسانه ایرانا. تازه‌ترین رویدادهای ایران.", 0.0),
]
INTRO = 3.2      # آهنگ پیش از نخستین واژه
OUTRO = 4.5      # آهنگ پس از واپسین واژه


def fail(msg):
    msg = str(msg).replace(API_KEY, "***") if API_KEY else str(msg)
    print(f"::error::{msg}", flush=True); sys.exit(1)


# ---------- آوا ----------

def tts(text, voice, path):
    last = None
    for model in MODELS:
        body = {"text": text, "model_id": model}
        if model != "eleven_v3":
            body["voice_settings"] = {"stability": 0.45, "similarity_boost": 0.85, "style": 0.35, "use_speaker_boost": True}
        else:
            body["voice_settings"] = {"stability": 0.5}
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
            data=json.dumps(body).encode(),
            headers={"xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as f:
                    f.write(r.read())
                return model
            except urllib.error.HTTPError as e:
                last = f"{voice} {model}: {e.code} {e.read()[:300]!r}"
                if e.code in (400, 422): break
                time.sleep(5 * (attempt + 1))
    fail(f"ElevenLabs: {last}")


def load(path):
    raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def trim(x, thr=0.01):
    a = np.abs(x).max(axis=1); idx = np.where(a > thr)[0]
    return x if len(idx) == 0 else x[max(0, idx[0] - 600): idx[-1] + 2000]


# ---------- آهنگ شکوهمند ----------

def note(n): return 440 * 2 ** ((n - 69) / 12)


def lowpass(x, fc):
    X = np.fft.rfft(x, axis=0)
    h = 1 / (1 + (np.fft.rfftfreq(len(x), 1 / SR) / fc) ** 4)
    return np.fft.irfft(X * (h[:, None] if X.ndim == 2 else h), n=len(x), axis=0)


def env(n, a, r, hold=1.0):
    e = np.ones(n) * hold
    ai, ri = max(1, int(a * SR)), max(1, int(r * SR))
    e[:ai] *= np.linspace(0, 1, ai)
    e[-ri:] *= np.linspace(1, 0, ri)
    return e


def saw(freq, dur, nh=10, det=0.0):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for f0 in ((freq,) if not det else (freq * (1 - det), freq, freq * (1 + det))):
        for h in range(1, nh + 1):
            if f0 * h > 12000: break
            s += np.sin(2 * np.pi * f0 * h * t + h) / h
    return s


def put(buf, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= len(buf): return
    sig = sig[: len(buf) - i]
    if sig.ndim == 1:
        buf[i:i + len(sig), 0] += gain * sig * (1 - pan)
        buf[i:i + len(sig), 1] += gain * sig * (1 + pan)
    else:
        buf[i:i + len(sig)] += gain * sig


def timpani(dur=2.2, pitch=38):
    t = np.arange(int(dur * SR)) / SR
    f = note(pitch) * (1 + 0.15 * np.exp(-t * 18))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    noise = np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t * 30) * 0.4
    return body + lowpass(noise, 900)


def roll(dur, pitch=38):
    out = np.zeros(int(dur * SR) + SR)
    n = int(dur * 14)
    for k in range(n):
        g = 0.15 + 0.85 * (k / n) ** 2
        s = timpani(0.6, pitch) * g
        i = int(k / 14 * SR); out[i:i + len(s)] += s[: len(out) - i]
    return out


def swell(dur, f0=3000):
    noise = np.random.default_rng(7).standard_normal(int(dur * SR))
    return lowpass(noise, f0) * np.linspace(0, 1, len(noise)) ** 3


def bell(freq, dur=3.0):
    t = np.arange(int(dur * SR)) / SR
    return sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t * d) for m, a, d in
               ((1, 1, 1.4), (2.76, .5, 2.4), (5.4, .25, 4), (8.9, .12, 6)))


def score(total, hit, final):
    """total: درازا؛ hit: زمان ضربه‌ی آغاز (رسانه ایرانا)؛ final: زمان آکورد پایانی."""
    buf = np.zeros((int((total + 1) * SR), 2))
    # پیش‌درآمد: خیزش و رول تیمپانی به سوی ضربه
    put(buf, roll(hit - 0.3), 0.3, 0.35)
    put(buf, swell(hit), 0, 0.10)
    for n, p in ((38, -.4), (45, .4), (50, 0)):
        s = saw(note(n), hit + 0.2, 8, 0.003); put(buf, lowpass(s * env(len(s), hit, 0.2), 700), 0, 0.05, p)
    # پیشرفت آکوردها از ضربه تا پایان
    prog = [[38, 50, 53, 57, 62], [34, 46, 50, 53, 58], [41, 53, 57, 60, 65], [36, 48, 52, 55, 60],
            [43, 55, 58, 62, 67], [34, 46, 50, 53, 58], [45, 52, 57, 61, 64], [38, 50, 53, 57, 62]]
    span = final - hit
    step = max(3.2, span / 8)
    t, k = hit, 0
    while t < final - 0.5:
        ch = prog[k % len(prog)]
        d = min(step, final - t) + 0.8
        for j, n in enumerate(ch):
            s = saw(note(n), d, 9 if j else 6, 0.004)
            s = lowpass(s, 1400 if j else 500) * env(len(s), 0.6, 0.8)
            put(buf, s, t, 0.045 if j else 0.08, (-0.5 + j / 4) if j else 0)
        put(buf, timpani(2.4, ch[0] if ch[0] >= 36 else ch[0] + 12), t, 0.22)
        e8 = 60 / 84 / 2                     # پویش زهی‌ها، هشتم‌های ۸۴ ضرب
        for q in range(int((d - 0.8) / e8)):
            n = (ch[0] + 12, ch[2], ch[0] + 12, ch[3])[q % 4]
            s = saw(note(n), e8 * 0.9, 10, 0.003)
            put(buf, lowpass(s * env(len(s), 0.01, 0.12), 1500), t + q * e8, 0.035 + (0.012 if q % 4 == 0 else 0), 0.25 if q % 2 else -0.25)
        if k % 2 == 0:            # هورن‌های نرم
            s = saw(note(ch[3]), d * 0.9, 12, 0.002)
            put(buf, lowpass(s * env(len(s), 0.9, 1.0), 1800), t, 0.03, 0.3)
        t += step; k += 1
    # ضربه‌ی آغاز: برنج و ناقوس
    for n in (50, 57, 62, 66, 69):
        s = saw(note(n), 2.5, 14, 0.003); put(buf, lowpass(s * env(len(s), 0.04, 2.0), 3500), hit, 0.05)
    put(buf, timpani(3, 38), hit, 0.6)
    put(buf, bell(note(86)), hit, 0.06)
    # پایان: رول، سپس آکورد بزرگ ر ماژور
    put(buf, roll(2.0), final - 2.0, 0.3)
    put(buf, swell(2.0, 5000), final - 2.0, 0.08)
    tail = total - final + 0.8
    for j, n in enumerate((26, 38, 50, 54, 57, 62, 66, 69, 74)):
        s = saw(note(n), tail, 14 if n > 40 else 6, 0.004)
        s = lowpass(s, 3000 if n > 40 else 600) * env(len(s), 0.08, tail * 0.7)
        put(buf, s, final, 0.05 if n > 40 else 0.09, (-0.6 + j / 6))
    put(buf, timpani(4, 38), final, 0.7)
    put(buf, bell(note(81)), final, 0.07); put(buf, bell(note(86)), final + 0.4, 0.05)
    # تالار: پژواک ساده
    for dly, g in ((0.071, .32), (0.113, .25), (0.167, .18), (0.239, .12)):
        i = int(dly * SR); buf[i:] += g * np.roll(buf, 1, axis=1)[:-i] * 0.6
    return buf[: int(total * SR)]


# ---------- آمیختن ----------

def build(name, voice, d):
    lines, model = [], None
    for i, (text, gap) in enumerate(SCRIPT):
        p = os.path.join(d, f"{name}_{i}.mp3")
        model = tts(text, voice, p)
        lines.append((trim(load(p)), gap))
    t, place = INTRO, []
    for x, gap in lines:
        place.append(t); t += len(x) / SR + gap
    final = place[-1] - 0.25
    total = t + OUTRO
    music = score(total, INTRO - 0.15, final)
    vox = np.zeros_like(music)
    for (x, _), at in zip(lines, place):
        put(vox, x, at)
    # پایین آوردن آهنگ زیر آوا
    a = np.abs(vox).max(axis=1)
    k = int(0.25 * SR); env_v = np.convolve(a > 0.02, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(env_v * 1.5, 0, 1)
    mix = music * duck[:, None] * 0.9 + vox * 1.0
    mix /= max(1e-6, np.abs(mix).max()) / 0.95
    wav = os.path.join(d, f"{name}.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    wav], input=mix.astype(np.float64).tobytes(), check=True)
    mp3 = os.path.join(OUT, f"irana-promo-{name}.mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-14:TP=-1:LRA=9",
                    "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k",
                    "-metadata", "title=آگهی رسانه ایرانا", "-metadata", "artist=رسانه ایرانا", mp3], check=True)
    print(name, model, f"{total:.1f}s", flush=True)
    return mp3


def promo_card(path):
    from PIL import ImageDraw
    import social
    img = social.background(); d = ImageDraw.Draw(img, "RGBA")
    from PIL import Image, ImageOps
    W, H = social.W, social.H
    logo = ImageOps.fit(Image.open(social.LOGO).convert("RGB"), (380, 380))
    mask = Image.new("L", (380, 380), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, 379, 379], 80, fill=255)
    lx, ly = (W - 380) // 2, 230
    d.rounded_rectangle([lx - 14, ly - 14, lx + 393, ly + 393], 92, outline=social.GOLD, width=6)
    img.paste(logo, (lx, ly), mask)
    y = ly + 440
    kw = dict(anchor="ma", direction="rtl", language="fa")
    d.text((W // 2, y), "رسانه ایرانا", font=social.font("Black", 150), fill=social.GOLD, **kw); y += 230
    d.text((W // 2, y), "I R A N A M E D I A", font=social.font("Medium", 40), fill=social.MIST, anchor="ma"); y += 90
    d.line([(160, y), (W // 2 - 30, y)], fill=social.GOLD, width=2); d.line([(W // 2 + 30, y), (W - 160, y)], fill=social.GOLD, width=2)
    d.polygon([(W // 2, y - 14), (W // 2 + 14, y), (W // 2, y + 14), (W // 2 - 14, y)], fill=social.GOLD); y += 70
    d.text((W // 2, y), "تازه‌ترین رویدادهای ایران", font=social.font("Bold", 66), fill=social.IVORY, **kw); y += 110
    d.text((W // 2, y), "شبانروزی سر هر ساعت کشور", font=social.font("Medium", 50), fill=social.MIST, **kw)
    x, wy, w, h = social.WAVE
    d.rounded_rectangle([x - 20, wy - 20, x + w + 20, wy + h + 20], 28, fill=social.NIGHT + (150,), outline=social.GOLD + (60,), width=2)
    d.text((W // 2, H - 120), f"{social.CHANNEL}   ·   {social.APP}", font=social.font("Medium", 34), fill=social.MIST, anchor="ma")
    img.save(path); return path


def main():
    os.makedirs(OUT, exist_ok=True)
    voices = [v.split(":", 1) for v in os.environ.get("PROMO_VOICES", "").split(",") if ":" in v]
    if not voices: fail("PROMO_VOICES is empty")
    import social
    card = promo_card(os.path.join(OUT, "promo-card.png"))
    with tempfile.TemporaryDirectory() as d:
        for name, vid in voices:
            mp3 = build(name.strip(), vid.strip(), d)
            social.video(card, mp3, mp3[:-4] + ".mp4")


if __name__ == "__main__":
    main()
