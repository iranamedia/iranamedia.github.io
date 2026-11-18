"""آگهی اپ رسانه ایرانا: ویدیوی کوتاه با گوینده‌ی زن دیگری (ElevenLabs) که بیننده را به دریافت اپ می‌خواند.
ساخته‌ها: <out>/app-ad-<voice>-tall.mp4 (۱۰۸۰×۱۹۲۰، تلگرام/ریلز/شورتس) و -wide.mp4 (۱۹۲۰×۱۰۸۰، یوتیوب).
اجرا: python3 tools/app_ad.py <out-dir> [voice_id ...]      (بی ELEVENLABS_API_KEY: بی‌صدا، برای آزمودن نما)"""
import json, os, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import tv  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

URL = "https://iranamedia.github.io/irana.apk"
SHORT_URL = "iranamedia.github.io/irana.apk"
VOICES = {"lily": "pFZP5JQG7iQjIQuC4Bue", "jessica": "cgSgspJ2msm6clMCkdW9"}
SCRIPT = [
    ("intro", "رسانه ایرانا، اکنون در گوشی شما!"),
    ("what", "خبرهای ایران سر هر ساعت، رادیو و سیمای ایرانا، و پیام‌های شهریار ایران؛ همه در یک اپ."),
    ("light", "سبک و رایگان است، و آخرین خبرها را بی‌اینترنت هم نشان می‌دهد."),
    ("get", "برای دریافت، روی پیوند همین آگهی بزنید."),
    ("end", "رسانه ایرانا؛ خبرهای ایران، سر هر ساعت."),
]
BG, GOLD, WHITE, MIST = tv.BG, tv.GOLD, tv.WHITE, tv.MIST


def tts(text, path, voice):
    """ElevenLabs با همان مدل‌ها و درست‌خوانی رادیو؛ بی بازگشت به گوینده‌ی دیگر."""
    import radio
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        n = max(2.2, len(text) / 14)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-t", f"{n:.2f}", path], check=True)
        return
    last = None
    for model in radio.MODELS:
        body = {"text": radio.speakable(text), "model_id": model}
        vs = radio.settings_for(model)
        if vs:
            body["voice_settings"] = vs
        req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
                                     data=json.dumps(body).encode(),
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                f.write(r.read())
            return
        except urllib.error.HTTPError as e:
            last = f"{model}: {e.code} {e.read()[:200]!r}"
    raise SystemExit(f"ElevenLabs: {last}")


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))


def ctext(d, cx, y, text, f, fill, depth=0):
    if depth:
        for k in range(depth, 0, -1):
            d.text((cx + k, y + k), text, font=f, fill=(6, 12, 30), anchor="ma", direction="rtl", language="fa")
    d.text((cx, y), text, font=f, fill=fill, anchor="ma", direction="rtl", language="fa")


def lines(d, text, f, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f, direction="rtl", language="fa") <= width or not cur:
            cur = t
        else:
            out.append(cur); cur = w
    return out + ([cur] if cur else [])


def backdrop(Wd, Hd):
    im = Image.new("RGB", (Wd, Hd), BG)
    g = Image.new("L", (Wd, Hd), 0)
    ImageDraw.Draw(g).ellipse((-Wd * 0.3, -Hd * 0.2, Wd * 1.3, Hd * 0.9), fill=90)
    im.paste(Image.new("RGB", (Wd, Hd), (30, 52, 110)), (0, 0), g.filter(ImageFilter.GaussianBlur(min(Wd, Hd) // 4)))
    d = ImageDraw.Draw(im)
    d.rectangle((0, Hd - 10, Wd, Hd), fill=GOLD)
    return im


def logo(size):
    lg = Image.open(os.path.join(HERE, "assets", "irana_logo_transparent.png")).convert("RGBA")
    return lg.resize((size, int(lg.height * size / lg.width)), Image.LANCZOS)


def phone(height):
    """گوشی با نمای اپ ایرانا در آن."""
    scr = Image.open(os.path.join(HERE, "assets", "app_screen.jpg")).convert("RGB")
    sw = int(height * 0.462)
    sh = int(scr.height * sw / scr.width)
    scr = scr.resize((sw, sh), Image.LANCZOS).crop((0, 0, sw, min(sh, int(height * 0.94))))
    pad = int(height * 0.03)
    body = Image.new("RGBA", (scr.width + 2 * pad, scr.height + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((0, 0, body.width - 1, body.height - 1), radius=pad * 2, fill=(12, 14, 20, 255), outline=GOLD + (255,), width=4)
    m = Image.new("L", scr.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, scr.width - 1, scr.height - 1), radius=pad, fill=255)
    body.paste(scr, (pad, pad), m)
    sh_ = Image.new("RGBA", (body.width + 80, body.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh_).rounded_rectangle((40, 50, body.width + 40, body.height + 40), radius=pad * 2, fill=(0, 0, 0, 150))
    sh_ = sh_.filter(ImageFilter.GaussianBlur(25))
    sh_.alpha_composite(body, (40, 40))
    return sh_


def qr(size):
    try:
        import qrcode
    except ImportError:
        return None
    q = qrcode.QRCode(border=2, box_size=10)
    q.add_data(URL); q.make(fit=True)
    return q.make_image(fill_color=(10, 21, 48), back_color=(245, 236, 214)).convert("RGB").resize((size, size), Image.NEAREST)


def scene(kind, Wd, Hd, path):
    tall = Hd > Wd
    im = backdrop(Wd, Hd)
    d = ImageDraw.Draw(im)
    big, mid, small = tv.font("Black", 88 if tall else 84), tv.font("Bold", 58 if tall else 52), tv.font("Medium", 42 if tall else 38)
    cx = Wd // 2
    lg = logo(150 if tall else 120)
    im.paste(lg, (Wd - lg.width - 40, 40), lg)
    if kind in ("intro", "end"):
        L = logo(int(min(Wd, Hd) * 0.42))
        im.paste(L, (cx - L.width // 2, int(Hd * (0.16 if tall else 0.10))), L)
        y = int(Hd * (0.16 if tall else 0.10)) + L.height + 50
        text = "رسانه ایرانا، اکنون در گوشی شما" if kind == "intro" else "خبرهای ایران، سر هر ساعت"
        for ln in lines(d, text, big, Wd * 0.86):
            ctext(d, cx, y, ln, big, WHITE, 5); y += int(big.size * 1.3)
        if kind == "end":
            ctext(d, cx, y + 20, SHORT_URL, mid, GOLD)
            ctext(d, cx, y + 110, "کانال تلگرام IranaMediaNews", small, MIST)
    elif kind in ("what", "light"):
        ph = phone(int(Hd * (0.56 if tall else 0.84)))
        bullets = (["خبرهای ایران، سر هر ساعت", "رادیو ایرانا", "سیمای ایرانا با گویندگان", "پیام‌های شهریار ایران"]
                   if kind == "what" else ["سبک: کمتر از ۱۰۰ کیلوبایت", "رایگان", "آخرین خبرها، بی‌اینترنت هم", "نصب آسان، بی‌نیاز به گوگل‌پلی"])
        if tall:
            im.paste(ph, (cx - ph.width // 2, int(Hd * 0.40)), ph)
            y = int(Hd * 0.12)
            for b in bullets:
                ctext(d, cx, y, b, mid, WHITE, 3); y += int(mid.size * 1.55)
        else:
            im.paste(ph, (int(Wd * 0.08), (Hd - ph.height) // 2), ph)
            y = int(Hd * 0.26); rx = int(Wd * 0.90)
            for b in bullets:
                for k in range(3, 0, -1):
                    d.text((rx + k, y + k), b, font=mid, fill=(6, 12, 30), anchor="ra", direction="rtl", language="fa")
                d.text((rx, y), b, font=mid, fill=WHITE, anchor="ra", direction="rtl", language="fa"); y += int(mid.size * 1.8)
    elif kind == "get":
        bw, bh = int(Wd * (0.78 if tall else 0.5)), int(Hd * (0.09 if tall else 0.15))
        by = int(Hd * (0.30 if tall else 0.22))
        d.rounded_rectangle((cx - bw // 2 + 8, by + 10, cx + bw // 2 + 8, by + bh + 10), radius=bh // 2, fill=(110, 80, 20))
        d.rounded_rectangle((cx - bw // 2, by, cx + bw // 2, by + bh), radius=bh // 2, fill=GOLD)
        ctext(d, cx, by + bh // 2 - big.size // 2 - 8, "دریافت اپ ایرانا", big, BG)
        y = by + bh + 50
        ctext(d, cx, y, SHORT_URL, mid, WHITE); y += 90
        q = qr(int(min(Wd, Hd) * (0.36 if tall else 0.30)))
        if q:
            im.paste(q, (cx - q.width // 2, y)); y += q.height + 30
            ctext(d, cx, y, "با دوربین گوشی بنگرید", small, MIST); y += 80
        ctext(d, cx, y, "یا روی پیوند زیر همین آگهی بزنید", small, GOLD)
        ctext(d, cx, Hd - 120, "ویژه‌ی گوشی‌های اندروید · آیفون: تارنما را در Safari به صفحه‌ی خانه بیفزایید", tv.font("Medium", 30 if tall else 28), MIST)
    im.convert("RGB").save(path)


def build(out, voice_name, voice_id):
    os.makedirs(out, exist_ok=True)
    work = os.path.join(out, f"_{voice_name}")
    os.makedirs(work, exist_ok=True)
    auds, durs = [], []
    for i, (_, text) in enumerate(SCRIPT):
        a = os.path.join(work, f"a{i}.mp3"); tts(text, a, voice_id)
        w = os.path.join(work, f"a{i}.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a, "-af", "apad=pad_dur=0.45", "-ar", "44100", "-ac", "2", w], check=True)
        auds.append(w); durs.append(dur(w))
    lst = os.path.join(work, "a.txt")
    open(lst, "w").write("".join(f"file '{a}'\n" for a in auds))
    audio = os.path.join(work, "voice.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", audio], check=True)
    made = []
    for tag, (Wd, Hd) in (("tall", (1080, 1920)), ("wide", (1920, 1080))):
        clips = []
        for i, ((kind, _), sec) in enumerate(zip(SCRIPT, durs)):
            png = os.path.join(work, f"{tag}_{i}.png"); scene(kind, Wd, Hd, png)
            c = os.path.join(work, f"{tag}_{i}.mp4")
            z = 0.04
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "25", "-loop", "1", "-i", png, "-t", f"{sec:.3f}",
                            "-vf", f"scale={Wd * 2}:{Hd * 2},zoompan=z='1+{z}*on/({sec:.3f}*25)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={Wd}x{Hd}:fps=25,"
                                   f"fade=t=in:d=0.25,fade=t=out:st={max(sec - 0.25, 0):.3f}:d=0.25,format=yuv420p",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", c], check=True)
            clips.append(c)
        vl = os.path.join(work, f"{tag}.txt")
        open(vl, "w").write("".join(f"file '{c}'\n" for c in clips))
        mp4 = os.path.join(out, f"app-ad-{voice_name}-{tag}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", vl, "-i", audio,
                        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4], check=True)
        print(mp4, f"{dur(mp4):.1f}s", flush=True)
        made.append(mp4)
    return made


if __name__ == "__main__":
    tv.fonts()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "_ad")
    names = sys.argv[2:] or list(VOICES)
    for n in names:
        build(out, n, VOICES.get(n, n))
