"""تلویزیون ایرانا: از خبرنامه (bulletin/latest.json) و صدای رادیو (_site/latest.mp3 + timeline.json)
یک برنامه‌ی خبری تلویزیونی می‌سازد.

- آغاز: ویدیوی آغاز ایرانا (assets/irana_intro_final.mp4)
- سپس صدای دو گوینده (بکتاش و شارلوت، یکی در میان) با قاب خبری ۱۶:۹:
  نوار بالا (نشان، «رسانه ایرانا»، تاریخ و ساعت)، تیتر هر خبر، نوار پایین.
- اگر PIXABAY_API_KEY (یا PEXELS_API_KEY) باشد، پشت هر خبر فیلم نمادین آزاد با برچسب «تصویر نمادین».
- خروجی: _tv/irana-tv.mp4 (۱۹۲۰×۱۰۸۰، یوتیوب و تلگرام) و _tv/irana-tv-tall.mp4 (۱۰۸۰×۱۹۲۰، فیسبوک و اینستاگرام)
- اگر TELEGRAM_BOT_TOKEN باشد، ویدیوی افقی به کانال تلگرام فرستاده می‌شود.

اجرا: python3 tv.py [--no-send | --send-only]
"""
import json, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request, uuid

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.environ.get("SAVE_DIR", os.path.join(HERE, "_site"))
OUT = os.environ.get("TV_DIR", os.path.join(HERE, "_tv"))
BULLETIN = os.path.join(HERE, "bulletin", "latest.json")
FONTS = os.path.join(HERE, "assets", "fonts")
INTRO = os.path.join(HERE, "assets", "irana_intro_final.mp4")
LOGO = os.path.join(HERE, "assets", "irana_lion_gold_transparent.png")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "@IranaMediaNews")
PEXELS = os.environ.get("PEXELS_API_KEY", "")
PIXABAY = os.environ.get("PIXABAY_API_KEY", "")
BROLL_SOURCE = {"name": "Pexels"}

W, H = 1920, 1080
BG, BAR = (10, 21, 48), (18, 36, 90)
GOLD, WHITE, MIST = (224, 180, 82), (245, 236, 214), (188, 198, 223)
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-r", "25"]


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())


# ---------- نوشتار فارسی ----------

def font(weight, size):
    for name in (f"Vazirmatn-{weight}.ttf", "Vazirmatn-Bold.ttf"):
        p = os.path.join(FONTS, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
    return ImageFont.truetype("DejaVuSans-Bold.ttf", size, layout_engine=ImageFont.Layout.RAQM)


F = {}


def fonts():
    F.update(big=font("Black", 120), name=font("Black", 62), head=font("Bold", 74), lower=font("Bold", 60),
             list=font("Bold", 50), meta=font("Medium", 40), small=font("Medium", 32))


def tw(d, text, f):
    return d.textlength(text, font=f, direction="rtl", language="fa")


def at_right(d, x, y, text, f, fill):
    d.text((x, y), text, font=f, fill=fill, anchor="ra", direction="rtl", language="fa")


def at_left(d, x, y, text, f, fill):
    d.text((x, y), text, font=f, fill=fill, anchor="la", direction="rtl", language="fa")


def centered(d, y, text, f, fill):
    d.text((W / 2, y), text, font=f, fill=fill, anchor="ma", direction="rtl", language="fa")


def wrap(d, text, f, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if tw(d, t, f) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


# ---------- قاب‌ها ----------

def frame(b, transparent=False):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0) if transparent else BG + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 128], fill=BAR + (255,))
    d.rectangle([0, 128, W, 134], fill=GOLD + (255,))
    x = W - 56
    if os.path.exists(LOGO):
        lg = Image.open(LOGO).convert("RGBA").resize((108, 108), Image.LANCZOS)
        img.alpha_composite(lg, (x - 108, 10)); x -= 132
    at_right(d, x, 22, "رسانه ایرانا", F["name"], GOLD)
    at_left(d, 56, 40, b["stamp"], F["meta"], WHITE)
    d.rectangle([0, H - 106, W, H - 100], fill=GOLD + (255,))
    d.rectangle([0, H - 100, W, H], fill=BAR + (255,))
    at_left(d, 56, H - 76, "iranamedia.github.io  ·  t.me/IranaMediaNews", F["small"], MIST)
    return img, d


def slide_title(b, path):
    img, d = frame(b)
    if os.path.exists(LOGO):
        lg = Image.open(LOGO).convert("RGBA").resize((300, 300), Image.LANCZOS)
        img.alpha_composite(lg, ((W - 300) // 2, 165))
    centered(d, 480, "تیترهای این بخش", F["meta"], GOLD)
    y = 560
    for it in b["items"][:3]:
        for line in wrap(d, "◆ " + it["title"], F["list"], W - 360)[:2]:
            centered(d, y, line, F["list"], WHITE); y += 70
        y += 18
    img.convert("RGB").save(path)


def slide_end(b, path):
    img, d = frame(b)
    if os.path.exists(LOGO):
        lg = Image.open(LOGO).convert("RGBA").resize((420, 420), Image.LANCZOS)
        img.alpha_composite(lg, ((W - 420) // 2, 170))
    centered(d, 610, "رسانه ایرانا", F["big"], GOLD)
    centered(d, 780, "تازه‌ترین رویدادهای ایران · شبانروزی، سر هر ساعت", F["head"], WHITE)
    img.convert("RGB").save(path)


def slide_story(b, n, path, over_video=False):
    it, total = b["items"][n], min(len(b["items"]), 5)
    img, d = frame(b, transparent=over_video)
    count = f"خبر {str(n + 1).translate(FA)} از {str(total).translate(FA)}"
    if over_video:
        lines = wrap(d, it["title"], F["lower"], W - 300)[:3]
        top = H - 140 - (96 + len(lines) * 84)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle([70, top, W - 70, H - 126], radius=22, fill=BG + (220,))
        ld.rectangle([W - 76, top + 18, W - 70, H - 144], fill=GOLD + (255,))
        ld.rounded_rectangle([36, 150, 470, 206], radius=14, fill=(0, 0, 0, 150))
        img.alpha_composite(layer)
        d = ImageDraw.Draw(img)
        at_left(d, 56, 158, "تصویر نمادین · " + BROLL_SOURCE["name"], F["small"], MIST)
        at_right(d, W - 120, top + 18, count, F["small"], GOLD)
        y = top + 72
        for line in lines:
            centered(d, y, line, F["lower"], WHITE); y += 84
        img.save(path)
    else:
        centered(d, 170, count, F["meta"], GOLD)
        lines = wrap(d, it["title"], F["head"], W - 320)[:6]
        y = 250 + max(0, (H - 140 - 250 - len(lines) * 108) // 2)
        for line in lines:
            centered(d, y, line, F["head"], WHITE); y += 108
        img.convert("RGB").save(path)


# ---------- فیلم نمادین آزاد (Pixabay یا Pexels) ----------
# فقط تصویرهای کلی و نمادین؛ هرگز فیلمی که با خودِ رویداد اشتباه گرفته شود.
TOPICS = [
    (("نفتکش", "هرمز", "کشتی", "دریا", "بندر"), "oil tanker sea"),
    (("نفت", "بنزین", "انرژی", "گاز", "پالایشگاه"), "oil refinery"),
    (("هسته", "اورانیوم", "آژانس", "غنی‌سازی"), "nuclear power plant"),
    (("اعدام", "دادگاه", "قضایی", "حکم"), "gavel court"),
    (("زندان", "حبس", "بازداشت", "دستگیر"), "prison bars"),
    (("تحریم", "ریال", "تورم", "بازار", "اقتصاد", "دلار", "بانک"), "stock market screen"),
    (("ملل متحد", "سازمان ملل", "شورای امنیت", "گفت‌وگو", "مذاکره", "دیپلمات"), "united nations"),
    (("موشک", "پهپاد", "حمله", "جنگ", "نظامی"), "night city skyline"),
    (("پهلوی", "شهریار"), "iran flag"),
]
DEFAULT_TOPIC = "Tehran city"
_used = set()


def topic(it):
    t = it["title"] + " " + it.get("body", "")[:200]
    for keys, q in TOPICS:
        if any(k in t for k in keys):
            return q
    return DEFAULT_TOPIC


def _save(url, n):
    out = os.path.join(OUT, f"broll_{n}.mp4")
    req = urllib.request.Request(url, headers={"User-Agent": "IranaMedia/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r, open(out, "wb") as f:
        f.write(r.read())
    return out if os.path.getsize(out) >= 100_000 else None


def pixabay(q, n):
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": PIXABAY, "q": q, "per_page": 20, "safesearch": "true"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "IranaMedia/1.0"}), timeout=25) as r:
        hits = json.load(r).get("hits", [])
    for v in hits:
        if ("pb", v["id"]) in _used or v.get("duration", 0) < 5:
            continue
        files = [f for f in v.get("videos", {}).values() if f.get("url") and 1280 <= (f.get("width") or 0) <= 1920
                 and (f.get("width") or 0) > (f.get("height") or 0)]
        if not files:
            continue
        out = _save(max(files, key=lambda x: x["width"])["url"], n)
        if out:
            _used.add(("pb", v["id"])); BROLL_SOURCE["name"] = "Pixabay"
            print(f"b-roll {n}: '{q}' pixabay {v['id']}", flush=True)
            return out
    return None


def pexels(q, n):
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": q, "orientation": "landscape", "size": "medium", "per_page": 15})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": PEXELS}), timeout=25) as r:
        vids = json.load(r).get("videos", [])
    for v in vids:
        if ("px", v["id"]) in _used or v.get("duration", 0) < 5:
            continue
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"
                 and f.get("width") and 1280 <= f["width"] <= 1920]
        if not files:
            continue
        out = _save(max(files, key=lambda x: x["width"])["link"], n)
        if out:
            _used.add(("px", v["id"])); BROLL_SOURCE["name"] = "Pexels"
            print(f"b-roll {n}: '{q}' pexels {v['id']}", flush=True)
            return out
    return None


def broll(it, n):
    finders = ([pixabay] if PIXABAY else []) + ([pexels] if PEXELS else [])
    for q in (topic(it), DEFAULT_TOPIC):
        for find in finders:
            try:
                out = find(q, n)
                if out: return out
            except Exception as e:
                print(f"{find.__name__} '{q}' failed: {e}", flush=True)
    return None


# ---------- ساخت ----------

def clip_still(png, seconds, out):
    ff("-loop", "1", "-i", png, "-t", f"{seconds:.3f}", "-vf", f"scale={W}:{H},setsar=1", "-tune", "stillimage", *ENC, "-an", out)


def clip_over(video, png, seconds, out):
    ff("-stream_loop", "-1", "-i", video, "-loop", "1", "-i", png, "-t", f"{seconds:.3f}", "-filter_complex",
       f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
       f"eq=brightness=-0.06:saturation=0.85[bg];[bg][1:v]overlay=0:0", *ENC, "-an", out)


def visuals(timeline, n_items):
    """بخش‌های صدا را به نماها تبدیل می‌کند: سرآغاز، هر خبر (با درنگ پس از آن)، پایان."""
    shots = []
    for seg in timeline:
        key = ("story", seg["n"]) if seg["kind"] == "story" and seg["n"] < n_items else \
              ("title",) if seg["kind"] in ("head", "sting") else \
              ("end",) if seg["kind"] in ("outro", "promo", "story") else None
        if key is None:                                   # درنگ: به نمای پیشین می‌پیوندد
            if shots: shots[-1][1] += seg["dur"]
            continue
        if shots and shots[-1][0] == key:
            shots[-1][1] += seg["dur"]
        else:
            shots.append([key, seg["dur"]])
    return shots


def build():
    b = json.load(open(BULLETIN, encoding="utf-8"))
    audio, tl = os.path.join(SITE, "latest.mp3"), os.path.join(SITE, "timeline.json")
    if not (os.path.exists(audio) and os.path.exists(tl)):
        print("ساعت بی‌گفتار یا صدای رادیو آماده نیست؛ تلویزیون ساخته نمی‌شود"); return None
    os.makedirs(OUT, exist_ok=True)
    fonts()
    shots = visuals(json.load(open(tl, encoding="utf-8"))["segments"], len(b["items"]))
    total = dur(audio)
    scale = total / max(sum(s[1] for s in shots), 1)        # هم‌زمانی دقیق با صدای نهایی
    clips = []
    for i, (key, seconds) in enumerate(shots):
        seconds *= scale
        out, png = os.path.join(OUT, f"shot_{i:02d}.mp4"), os.path.join(OUT, f"shot_{i:02d}.png")
        if key[0] == "title":
            slide_title(b, png); clip_still(png, seconds, out)
        elif key[0] == "end":
            slide_end(b, png); clip_still(png, seconds, out)
        else:
            n = key[1]
            bv = broll(b["items"][n], n)
            if bv:
                slide_story(b, n, png, over_video=True)
                try:
                    clip_over(bv, png, seconds, out)
                except subprocess.CalledProcessError:
                    bv = None
            if not bv:
                slide_story(b, n, png); clip_still(png, seconds, out)
        clips.append(out)
    lst = os.path.join(OUT, "shots.txt")
    open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
    main = os.path.join(OUT, "main.mp4")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-i", audio, "-map", "0:v", "-map", "1:a",
       "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-shortest", main)
    parts = [main]
    if os.path.exists(INTRO):
        intro = os.path.join(OUT, "intro.mp4")
        ff("-i", INTRO, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
           f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0A1530,setsar=1", *ENC,
           "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", intro)
        parts.insert(0, intro)
    lst2 = os.path.join(OUT, "parts.txt")
    open(lst2, "w").write("".join(f"file '{p}'\n" for p in parts))
    wide = os.path.join(OUT, "irana-tv.mp4")
    ff("-f", "concat", "-safe", "0", "-i", lst2, *ENC, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", wide)
    tall = os.path.join(OUT, "irana-tv-tall.mp4")
    ff("-i", wide, "-filter_complex",
       "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:2,"
       "eq=brightness=-0.15[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2",
       *ENC, "-g", "50", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
       "-movflags", "+faststart", tall)                    # ویژگی‌هایی که اینستاگرام می‌پذیرد
    print(f"TV: {wide} {dur(wide):.1f}s {os.path.getsize(wide)//1024} KB · {tall}", flush=True)
    return wide


def caption(b):
    lines = [f"📺 تلویزیون ایرانا · {b['stamp']}", ""]
    for it in b["items"][:5]:
        lines.append("▪️ " + it["title"])
    lines += ["", CHANNEL]
    return "\n".join(lines)[:1000]


def send(path, cap):
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in {"chat_id": CHANNEL, "caption": cap, "supports_streaming": "true",
                 "width": str(W), "height": str(H), "duration": str(int(dur(path)))}.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"irana-tv.mp4\"\r\n"
             "Content-Type: video/mp4\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        res = {"ok": False, "error": f"{e.code} {e.read()[:300]!r}"}
    print("Telegram TV:", "ok" if res.get("ok") else str(res).replace(BOT_TOKEN, "***")[:400], flush=True)
    return res.get("ok")


if __name__ == "__main__":
    if "--send-only" in sys.argv:                       # سر ساعت: فرستادن ویدیوی ساخته‌شده
        wide = os.path.join(OUT, "irana-tv.mp4")
        if not os.path.exists(wide): print("ویدیوی تلویزیون نیست"); sys.exit(0)
        ok = BOT_TOKEN and send(wide, caption(json.load(open(BULLETIN, encoding="utf-8"))))
        sys.exit(0 if ok else 1)
    wide = build()
    if wide and BOT_TOKEN and "--no-send" not in sys.argv:
        if not send(wide, caption(json.load(open(BULLETIN, encoding="utf-8")))):
            sys.exit(1)
