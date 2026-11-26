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
LOGO = os.path.join(HERE, "assets", "irana_logo_transparent.png")   # نشان ایرانا
FLAG = os.path.join(HERE, "assets", "flag_lion_sun.png")             # درفش شیر و خورشید، دست راست نشان ایرانا


def mark(size):
    """نشان ایرانا و، دست راست آن، درفش شیر و خورشید (یک تصویر شفاف؛ بلندی = size)."""
    lg = Image.open(LOGO).convert("RGBA").resize((size, size), Image.LANCZOS)
    if not os.path.exists(FLAG):
        return lg
    fh = int(size * 0.62); fw = int(fh * 16 / 9); gap = max(8, size // 9); bd = max(2, size // 40)
    fl = Image.open(FLAG).convert("RGB").resize((fw, fh), Image.LANCZOS)
    out = Image.new("RGBA", (size + gap + fw + 2 * bd + 6, size), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    y = (size - fh) // 2
    ImageDraw.Draw(sh).rectangle((size + gap + 4, y + 4, size + gap + fw + 2 * bd + 4, y + fh + 2 * bd + 4), fill=(0, 0, 0, 120))
    from PIL import ImageFilter as _IF
    out.alpha_composite(sh.filter(_IF.GaussianBlur(max(2, size // 30))))
    ImageDraw.Draw(out).rectangle((size + gap, y, size + gap + fw + 2 * bd - 1, y + fh + 2 * bd - 1), fill=(255, 255, 255, 255))
    out.paste(fl, (size + gap + bd, y + bd))
    out.alpha_composite(lg, (0, 0))
    return out
PRESENTER = {"man": os.path.join(HERE, "assets", "presenter_man.jpg"),        # گوینده‌ها در استودیو
             "woman": os.path.join(HERE, "assets", "presenter_woman.jpg")}
# نوشته‌های انگلیسی درون عکس‌ها (نام، «NEWS NOW»، ساعت ساختگی) نباید دیده شود:
# فقط بخش بالای عکس به کار می‌رود (نوار پایینِ عکس بیرون می‌ماند) و نوشته‌های پس‌زمینه مات می‌شوند.
PHOTO_KEEP = 0.86
PHOTO_BLUR = {"woman": [(0.66, 0.22, 0.92, 0.50), (0.0, 0.42, 0.34, 0.58), (0.90, 0.22, 1.0, 0.50)],
              "man": [], "firoozeh": [(0.0, 0.0, 0.22, 0.80)]}       # فیروزه: نمایشگرهای کنار چپ
sys.path.insert(0, os.path.join(HERE, "tools"))
import cohost                                         # گوینده‌ی همراه بکتاش: یکی در میان فیروزه و شارلوت
_AN = {}


def AN(voice):
    """نام عکس و نقاب گوینده در assets برای این بخش (woman ← firoozeh در بخش‌های فیروزه)."""
    if voice not in _AN:
        _AN[voice] = cohost.asset(voice)
    return _AN[voice]
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "@IranaMediaNews")
PEXELS = os.environ.get("PEXELS_API_KEY", "")
PIXABAY = os.environ.get("PIXABAY_API_KEY", "")
TALK_DIR = os.environ.get("TALK_DIR", os.path.join(HERE, "_talk"))   # چهره‌های گویا (tools/talk_shot.py)
ON_CAM_MAX = float(os.environ.get("ON_CAM_MAX", "7"))
PRINCE = re.compile(r"شهریار\s*ایران|رضا\s*پهلوی|شاهزاده\s*رضا|رضا\s*شاه\s*دوم|رضاشاه\s*دوم")   # شهریار ایران
TWO_SHOT = 4.0          # پس از آرم آغاز: نمای استودیو با هر دو گوینده (ثانیه)
BROLL_SOURCE = {"name": "Pexels"}

W, H = 1920, 1080
BG, BAR = (10, 21, 48), (18, 36, 90)
GOLD, WHITE, MIST = (224, 180, 82), (245, 236, 214), (188, 198, 223)
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
# همه‌ی نماها با یک برچسب رنگ (bt709، tv) ساخته می‌شوند. فیلم‌های Pixabay برچسب رنگ دارند و نماهای دیگر نه؛
# این ناهمسانی در میانه‌ی ویدیو فیلتر محو آغاز (xfade) را از نو راه می‌انداخت و ویدیو پس از نخستین فیلم
# نمادین بریده می‌شد (بخش‌های ۲۰ شنبه و ۸ یکشنبه، زیر ۲ دقیقه).
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-r", "25",
       "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


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
    F.update(big=font("Black", 120), name=font("Black", 62), title=font("Black", 52), head=font("Bold", 74), lower=font("Bold", 60),
             list=font("Bold", 50), meta=font("Medium", 40), small=font("Medium", 32))


def tw(d, text, f):
    return d.textlength(text, font=f, direction="rtl", language="fa")


def at_right(d, x, y, text, f, fill):
    d.text((x, y), text, font=f, fill=fill, anchor="ra", direction="rtl", language="fa")


def at_left(d, x, y, text, f, fill):
    d.text((x, y), text, font=f, fill=fill, anchor="la", direction="rtl", language="fa")


def centered(d, y, text, f, fill):
    d.text((W / 2, y), text, font=f, fill=fill, anchor="ma", direction="rtl", language="fa")


def centered3d(d, y, text, f, fill, depth=5):
    """نوشته‌ی برجسته (سه‌بعدی): چند لایه‌ی تیره در زیر و کنار، سپس رویه‌ی روشن."""
    for k in range(depth, 0, -1):
        shade = tuple(int(c * (0.18 + 0.1 * (depth - k) / depth)) for c in fill[:3])
        d.text((W / 2 + k, y + k), text, font=f, fill=shade, anchor="ma", direction="rtl", language="fa")
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
        mk = mark(108)
        img.alpha_composite(mk, (x - mk.width, 10)); x -= mk.width + 24
    at_right(d, x, 22, "رسانه ایرانا", F["name"], GOLD)
    at_left(d, 56, 40, b["stamp"], F["meta"], WHITE)
    d.rectangle([0, H - 106, W, H - 100], fill=GOLD + (255,))
    d.rectangle([0, H - 100, W, H], fill=BAR + (255,))
    at_left(d, 56, H - 76, "iranamedia.github.io  ·  t.me/IranaMediaNews", F["small"], MIST)
    return img, d


def slide_title(b, path):
    img, d = frame(b)
    if os.path.exists(LOGO):
        mk = mark(220)
        img.alpha_composite(mk, ((W - mk.width) // 2, 160))
    centered3d(d, 395, "تیترهای این بخش", F["meta"], GOLD, 4)
    bottom = H - 125                                   # بالای نوار پایین
    for size in (50, 44, 38):                         # تیترها هرگز روی نوار پایین نمی‌روند
        f = font("Bold", size)
        blocks = [wrap(d, "◆ " + it["title"], f, W - 360)[:2] for it in b["items"][:3]]
        lh, gap = int(size * 1.4), int(size * 0.4)
        if 465 + sum(len(x) * lh + gap for x in blocks) <= bottom:
            break
    y = 465
    for lines in blocks:
        for line in lines:
            if y + lh > bottom: break
            centered3d(d, y, line, f, WHITE, 4); y += lh
        y += gap
    img.convert("RGB").save(path)


def slide_end(b, path):
    img, d = frame(b)
    if os.path.exists(LOGO):
        mk = mark(420)
        img.alpha_composite(mk, ((W - mk.width) // 2, 170))
    centered(d, 610, "رسانه ایرانا", F["big"], GOLD)
    centered(d, 780, "تازه‌ترین رویدادهای ایران · شبانروزی، سر هر ساعت", F["head"], WHITE)
    img.convert("RGB").save(path)


AD_VIDEO = os.path.join(HERE, "assets", "irana_ad.mp4")      # تصویر آگهی ایرانا (صدای آگهی: شارلوت، در assets/promo.mp3)
AD_LINES = ["رسانه ایرانا", "تازه‌ترین رویدادهای ایران · شبانروزی، سر هر ساعت", "ایرانا همه جا با شما، با تازه‌ترین رویدادها"]


def ad_overlay(path):
    """نوشته‌ی فارسی آگهی روی واپسین نمای ویدیوی آگهی (بالای آسمان)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([260, 40, W - 260, 330], radius=30, fill=BG + (175,))
    img.alpha_composite(layer)
    centered(d, 62, AD_LINES[0], F["name"], GOLD)
    centered(d, 150, AD_LINES[1], F["lower"], WHITE)
    centered(d, 236, AD_LINES[2], F["lower"], WHITE)
    d.rectangle([0, H - 70, W, H], fill=BAR + (230,))
    centered(d, H - 58, "iranamedia.github.io  ·  t.me/IranaMediaNews  ·  youtube.com/IRANAMEDIA", F["small"], MIST)
    img.save(path)


def clip_ad(seconds, out):
    """آگهی ایرانا: ویدیوی آگهی (بی‌صدا، چون صدای شارلوت در صدای اصلی است)، سپس واپسین نما
    با نزدیک‌شدن آهسته و نوشته‌ی فارسی آگهی تا پایان صدای آگهی."""
    png = os.path.join(OUT, "ad_text.png")
    ad_overlay(png)
    vlen = dur(AD_VIDEO)
    hold = max(seconds - vlen, 0)
    ff("-i", AD_VIDEO, "-framerate", "25", "-loop", "1", "-i", png, "-t", f"{seconds:.3f}", "-filter_complex",
       f"[0:v]fps=25,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
       f"tpad=stop_mode=clone:stop_duration={hold + 1:.3f},"
       f"zoompan=z='if(lt(in_time,{vlen:.2f}),1,min(1+0.0015*(in-{int(vlen*25)}),1.08))':"
       f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=25[v];"
       f"[1:v]format=rgba,fade=t=in:st={max(vlen - 0.6, 0):.2f}:d=0.8:alpha=1[t];"
       f"[v][t]overlay=0:0:enable='gte(t,{max(vlen - 0.6, 0):.2f})'", *ENC, "-an", out)


def lower_third(b, path, title, label):
    """قاب گوینده: نشان کوچک در گوشه (تا چهره زیر نوار نرود) + نوار تیتر پهن و پررنگ
    که نوشته‌های چاپ‌شده در پایین عکس استودیو را می‌پوشاند."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    name_w = int(tw(d, "رسانه ایرانا", F["title"]))
    mk = mark(80)
    d.rounded_rectangle([W - 40 - name_w - mk.width - 50, 30, W - 40, 122], radius=20, fill=BG + (215,))
    img.alpha_composite(mk, (W - 60 - mk.width, 36))
    at_right(d, W - 70 - mk.width, 40, "رسانه ایرانا", F["title"], GOLD)
    sw = int(tw(d, b["stamp"], F["small"]))
    d.rounded_rectangle([40, 44, 40 + sw + 48, 108], radius=18, fill=BG + (200,))
    at_left(d, 64, 56, b["stamp"], F["small"], WHITE)
    d.rectangle([0, H - 100, W, H - 94], fill=GOLD + (255,))
    d.rectangle([0, H - 94, W, H], fill=BAR + (255,))
    at_left(d, 56, H - 70, "iranamedia.github.io  ·  t.me/IranaMediaNews", F["small"], MIST)
    lines = wrap(d, title, F["lower"], W - 300)[:3]
    top = min(H - 100 - (96 + len(lines) * 84), int(H * 0.70))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rectangle([0, top, W, H - 100], fill=BG + (255,))
    ld.rectangle([0, top, W, top + 5], fill=GOLD + (255,))
    img.alpha_composite(layer)
    d = ImageDraw.Draw(img)
    at_right(d, W - 70, top + 20, label, F["small"], GOLD)
    y = top + 20 + max(52, (H - 100 - top - 20 - len(lines) * 84) // 2)
    for line in lines:
        centered3d(d, y, line, F["lower"], WHITE, 5); y += 84
    img.save(path)


def slide_story(b, n, path, over_video=False, credit=None):
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
        at_left(d, 56, 158, credit or ("تصویر نمادین · " + BROLL_SOURCE["name"]), F["small"], MIST)
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
# فقط وقتی فیلمی آشکارا هم‌موضوع خبر است؛ اگر نه، بی‌فیلم (گوینده و قاب تیتر).
# هر موضوع در هر برنامه یک بار؛ برچسب‌های فیلم باید با موضوع بخواند.
TOPICS = [
    (("نفتکش", "کشتی", "تنگه هرمز", "بندر"), "oil tanker ship", ("tanker", "ship", "vessel", "cargo", "oil")),
    (("پالایشگاه", "نفت", "بنزین", "سوخت"), "oil refinery", ("refinery", "oil", "petroleum", "industry", "pipeline")),
    (("هسته‌ای", "اتمی", "اورانیوم", "غنی‌سازی", "نیروگاه"), "nuclear power plant", ("nuclear", "reactor", "power plant", "cooling tower")),
    (("دادگاه", "حکم", "محکوم", "قوه قضاییه", "مراجع قضایی"), "judge gavel court", ("gavel", "court", "judge", "law", "justice")),
    (("زندان", "حبس", "بازداشت", "دستگیر"), "prison bars", ("prison", "jail", "bars", "handcuffs", "cell")),
    (("ریال", "تورم", "بورس", "دلار", "اقتصاد", "گرانی"), "stock market money", ("stock", "market", "money", "currency", "finance", "economy")),
]
_used = set()
_topics_used = set()


def topic(it):
    """موضوع فیلم نمادین از تیتر خبر؛ None یعنی بی‌فیلم."""
    if PRINCE.search(it["title"]):
        return None                                   # خبر شهریار ایران: بی‌فیلم نمادین
    for keys, q, tags in TOPICS:
        if any(k in it["title"] for k in keys):
            return (q, tags)
    return None


def _save(url, n):
    out = os.path.join(OUT, f"broll_{n}.mp4")
    req = urllib.request.Request(url, headers={"User-Agent": "IranaMedia/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r, open(out, "wb") as f:
        f.write(r.read())
    return out if os.path.getsize(out) >= 100_000 else None


def pixabay(q, n, tags=()):
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": PIXABAY, "q": q, "per_page": 20, "safesearch": "true"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "IranaMedia/1.0"}), timeout=25) as r:
        hits = json.load(r).get("hits", [])
    for v in hits:
        if ("pb", v["id"]) in _used or v.get("duration", 0) < 5:
            continue
        if tags and not any(t in v.get("tags", "").lower() for t in tags):
            continue                                  # برچسب‌ها با موضوع نمی‌خواند
        files = [f for f in v.get("videos", {}).values() if f.get("url") and 1280 <= (f.get("width") or 0) <= 1920
                 and (f.get("width") or 0) > (f.get("height") or 0)]
        if not files:
            continue
        out = _save(max(files, key=lambda x: x["width"])["url"], n)
        if out:
            _used.add(("pb", v["id"])); BROLL_SOURCE["name"] = "Pixabay"
            print(f"b-roll {n}: '{q}' pixabay {v['id']} [{v.get('tags', '')}]", flush=True)
            return out
    return None


def pexels(q, n, tags=()):
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
    tp = topic(it)
    if tp is None or tp[0] in _topics_used:          # بی‌ربط یا تکراری: بی‌فیلم
        return None
    q, tags = tp
    for find in ([pixabay] if PIXABAY else []) + ([pexels] if PEXELS else []):
        try:
            out = find(q, n, tags)
            if out:
                _topics_used.add(q); return out
        except Exception as e:
            print(f"{find.__name__} '{q}' failed: {e}", flush=True)
    return None


# ---------- ساخت ----------

def clip_still(png, seconds, out):
    ff("-loop", "1", "-i", png, "-t", f"{seconds:.3f}", "-vf", f"scale={W}:{H},setsar=1", "-tune", "stillimage", *ENC, "-an", out)


# رنگ لباس گوینده‌ها در هر بخش (کت، کراوات، پیراهن رنگی؛ پیراهن سفید سفید می‌ماند).
# None = رنگ خود عکس. رنگ‌ها رنگ‌مایه‌ی (hue) درجه‌اند؛ با نقاب لباس assets/presenter_*_clothes.png.
WARDROBE = {"man": [None, 345, 150, 25, 215, 280], "woman": [None, 210, 345, 150, 265, 15]}
# کت سیاه فیروزه: در هر بخش رنگی دیگر (رنگ‌آمیزی با نگه‌داشتن سایه‌روشن). None = سیاه خود عکس
WARDROBE_FIROOZEH = [(120, 22, 44), (24, 64, 140), (18, 96, 74), (96, 34, 120), None, (18, 104, 124)]
# پهنای شانه‌ها و بالای سر در عکس‌ها (پیکسل، از نقاب گوینده) برای هم‌اندازه و هم‌سر کردن گوینده‌ها در نمای دو نفره
BODY = {"man": {"shoulders": 843, "top": 78}, "firoozeh": {"shoulders": 1724, "top": 32}}


def wardrobe_index():
    """هر بخش (روز و ساعت خبرنامه) رنگ دیگری؛ هر دو گوینده هم‌زمان دگرگون می‌شوند."""
    try:
        stamp = json.load(open(BULLETIN, encoding="utf-8")).get("stamp", "")
    except Exception:
        return 0
    nums = [int(x) for x in re.findall(r"\d+", stamp.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))]
    return (sum(nums) + len(nums)) % len(WARDROBE["man"]) if nums else 0


# خبرهای سوگ (اعدام، کشته‌شدن، مرگ): گوینده بی‌لبخند. عکس جدی گوینده: assets/presenter_<man|woman>_serious.jpg
# اگر عکس جدی نباشد، در این خبرها گوینده روی صفحه نمی‌آید (تنها قاب تیتر یا فیلم نمادین).
SAD = re.compile(r"اعدام|کشته|جان[\s\u200c]*باخت|درگذشت|مرگ|قتل|به[\s\u200c]*دار|سوگ|جان[\s\u200c]*سپرد|کشتار|شهید")


def mood_of(it):
    return "serious" if SAD.search(it.get("title", "") + " " + it.get("body", "")[:300]) else ""


def photo_src(voice, mood=""):
    if mood == "serious":
        p = os.path.join(HERE, "assets", f"presenter_{AN(voice)}_serious.jpg")
        return p if os.path.exists(p) else None
    if voice == "woman" and AN("woman") == "firoozeh":
        return os.path.join(HERE, "assets", "presenter_firoozeh.jpg")
    return PRESENTER.get(voice, "")


def dressed(voice, mood=""):
    """عکس اصلی گوینده با رنگ لباس این بخش."""
    src = photo_src(voice, mood)
    tag = f"_{mood}" if mood else ""
    out = os.path.join(OUT, f"dressed_{voice}{tag}.png")
    if os.path.exists(out):
        return Image.open(out).convert("RGB")
    im = Image.open(src).convert("RGB")
    if AN(voice) == "firoozeh":
        col = WARDROBE_FIROOZEH[wardrobe_index() % len(WARDROBE_FIROOZEH)]
        pm = os.path.join(HERE, "assets", "presenter_firoozeh_person.png")
        if col is not None and os.path.exists(pm):
            import numpy as np
            from PIL import ImageFilter
            rgb = np.asarray(im).astype(np.float32)
            luma = (rgb @ np.array([0.299, 0.587, 0.114], np.float32)) / 255
            person = np.asarray(Image.open(pm).convert("L").resize(im.size)).astype(np.float32) / 255
            rows = np.arange(im.height, dtype=np.float32)[:, None] / im.height
            m = person * (rows > 0.60) * np.clip((0.30 - luma) / 0.08, 0, 1)            # کت تیره، زیر چانه
            m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255
            tint = np.array(col, np.float32)[None, None, :] * np.clip(0.42 + 2.4 * luma, 0, 1.6)[..., None]
            im = Image.fromarray(np.clip(rgb * (1 - m[..., None]) + tint * m[..., None], 0, 255).astype(np.uint8))
            print(f"لباس فیروزه: {col}", flush=True)
        os.makedirs(OUT, exist_ok=True)
        im.save(out)
        return im
    hue = WARDROBE[voice][wardrobe_index()]
    mask_p = os.path.join(HERE, "assets", f"presenter_{AN(voice)}{tag}_clothes.png")
    if hue is not None and os.path.exists(mask_p):
        import numpy as np
        hsv = np.asarray(im.convert("HSV")).astype(np.float32)
        m = np.asarray(Image.open(mask_p).convert("L").resize(im.size)).astype(np.float32) / 255
        m = m * (hsv[..., 1] > 30)                    # تنها جاهای رنگی؛ سفید و خاکستری دست نمی‌خورد
        new = hsv.copy()
        new[..., 0] = hue / 360 * 255
        new[..., 1] = np.clip(hsv[..., 1] * (1.25 if voice == "woman" else 1.1), 0, 255)
        rgb_new = np.asarray(Image.fromarray(new.astype(np.uint8), "HSV").convert("RGB")).astype(np.float32)
        rgb_old = np.asarray(im).astype(np.float32)
        im = Image.fromarray((rgb_old * (1 - m[..., None]) + rgb_new * m[..., None]).astype(np.uint8))
        print(f"لباس {voice}: رنگ‌مایه‌ی {hue}°", flush=True)
    os.makedirs(OUT, exist_ok=True)
    im.save(out)
    return im


def studio_photo(voice, mood=""):
    """عکس آماده‌ی گوینده: برش ۱۶:۹ از بخش بالای عکس + مات کردن نوشته‌های پس‌زمینه."""
    src = photo_src(voice, mood)
    if not src or not os.path.exists(src):
        return None
    out = os.path.join(OUT, f"studio_{voice}{'_' + mood if mood else ''}.png")
    if os.path.exists(out):
        return out
    from PIL import ImageFilter
    im = dressed(voice, mood)
    w, h = im.size
    for x0, y0, x1, y1 in PHOTO_BLUR.get(AN(voice), []):
        box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
        im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(18)), box)
    ch = int(h * PHOTO_KEEP); cw = min(w, ch * 16 // 9)
    im = im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, ch)).resize((W, H), Image.LANCZOS)
    im.save(out)
    return out


# ---- نمای سه‌بعدی (۲.۵ بعدی، رایگان): گوینده و استودیو دو لایه‌اند و دوربین آرام پیش می‌رود؛
# لایه‌ی نزدیک (گوینده، میز) تندتر از لایه‌ی دور (دیوار استودیو) بزرگ و جابه‌جا می‌شود و استودیو کمی مات است.
DEPTH = os.environ.get("TV_DEPTH", "1") != "0"      # سه‌بعدی، با گوینده‌های گویا (آزموده: دهان و پلک در نمای سه‌بعدی می‌جنبند)


def _crop_like_studio(im):
    w, h = im.size
    ch = int(h * PHOTO_KEEP); cw = min(w, ch * 16 // 9)
    return im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, ch)).resize((W, H), Image.LANCZOS)


def _fill(arr, hole):
    """جای خالی پشت گوینده را با رنگ‌های گرداگرد پر می‌کند (پخش نرم، بی‌نیاز به کتابخانه‌ی دیگر)."""
    import numpy as np
    known = (1 - hole)[..., None]
    out = arr.copy()
    for div in (6, 16, 48):
        sz = (max(W // div, 2), max(H // div, 2))
        a = np.asarray(Image.fromarray(np.clip(arr * known, 0, 255).astype(np.uint8)).resize(sz, Image.BOX).resize((W, H), Image.BICUBIC)).astype(np.float32)
        k = np.asarray(Image.fromarray((known[..., 0] * 255).astype(np.uint8)).resize(sz, Image.BOX).resize((W, H), Image.BICUBIC)).astype(np.float32)[..., None] / 255
        est = a / np.maximum(k, 1e-3)
        good = (k > 0.08)
        out = np.where((hole[..., None] > 0.5) & good & (known < 0.5), est, out)
        arr, known = out, np.maximum(known, good.astype(np.float32) * (hole[..., None] > 0.5))
    return out


def depth_layers(voice, mood=""):
    """(پس‌زمینه‌ی بی‌گوینده، نقاب گوینده) در همان برش عکس استودیو؛ None اگر نقاب نباشد."""
    tag = f"_{mood}" if mood else ""
    mask_src = os.path.join(HERE, "assets", f"presenter_{AN(voice)}{tag}_person.png")
    photo = studio_photo(voice, mood)
    if not (DEPTH and photo and os.path.exists(mask_src)):
        return None
    back, mask = os.path.join(OUT, f"depth_back_{voice}{tag}.png"), os.path.join(OUT, f"depth_mask_{voice}{tag}.png")
    if os.path.exists(back) and os.path.exists(mask):
        return back, mask
    import numpy as np
    from PIL import ImageFilter
    m = _crop_like_studio(Image.open(mask_src).convert("L"))
    m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2)).save(mask)          # لبه‌ی نرم
    hole = np.asarray(m.filter(ImageFilter.MaxFilter(31))).astype(np.float32) / 255
    arr = np.asarray(Image.open(photo).convert("RGB")).astype(np.float32)
    plate = Image.fromarray(np.clip(_fill(arr, (hole > 0.2).astype(np.float32)), 0, 255).astype(np.uint8))
    plate.filter(ImageFilter.GaussianBlur(2.5)).save(back)                                     # ژرفای میدان
    return back, mask


def clip_parallax(layers, png, seconds, out):
    """layers: از دور به نزدیک، هر یک {src, video, mask, zoom, drift}؛ نوار تیتر (png) رویِ همه، بی‌حرکت."""
    D = max(seconds, 0.5)
    args, fc, prev, k = [], [], None, 0
    for L in layers:
        if L.get("video"):
            args += ["-i", L["src"]]
        else:
            args += ["-framerate", "25", "-loop", "1", "-i", L["src"]]
        src = f"[{k}:v]fps=25,scale={W}:{H},setsar=1,format=rgba"; k += 1
        if L.get("mask"):
            args += ["-framerate", "25", "-loop", "1", "-i", L["mask"]]
            fc.append(f"[{k}:v]scale={W}:{H},format=gray[m{k}]")
            src = f"{src}[c{k}];[c{k}][m{k}]alphamerge"; k += 1
        z, dx = L["zoom"], L.get("drift", 0.0)
        fc.append(f"{src},tpad=stop_mode=clone:stop_duration=3,"
                  f"scale=w='2*ceil({W}*(1+{z}*t/{D:.3f})/2)':h=-2:eval=frame,"
                  f"crop={W}:{H}:x='(iw-{W})*(0.5+{dx}*(t/{D:.3f}-0.5))':y='(ih-{H})*0.42'[l{k}]")
        fc.append(f"{prev}[l{k}]overlay=0:0:format=auto[o{k}]" if prev else f"[l{k}]null[o{k}]")
        prev = f"[o{k}]"
    args += ["-framerate", "25", "-loop", "1", "-i", png]
    fc.append(f"{prev}[{k}:v]overlay=0:0,format=yuv420p[v]")
    ff(*args, "-t", f"{seconds:.3f}", "-filter_complex", ";".join(fc), "-map", "[v]", *ENC, "-an", out)


def clip_depth(fg, voice, mood, png, seconds, out, video=False):
    """گوینده (عکس یا گویا) جلوی استودیوی کمی مات، با حرکت سه‌بعدی دوربین. False اگر نشد."""
    lay = depth_layers(voice, mood)
    if not lay:
        return False
    back, mask = lay
    try:
        clip_parallax([{"src": back, "zoom": 0.025, "drift": 0.6},
                       {"src": fg, "video": video, "mask": mask, "zoom": 0.075, "drift": -0.5}], png, seconds, out)
        return True
    except subprocess.CalledProcessError:
        print("نمای سه‌بعدی نشد؛ نمای ساده", flush=True)
        return False


def clip_presenter(photo, png, seconds, out):
    """عکس استودیوی گوینده با حرکت آرام دوربین (نزدیک‌شدن آهسته)، و نوار تیتر روی آن."""
    frames = max(int(seconds * 25), 1)
    ff("-framerate", "25", "-loop", "1", "-i", photo, "-framerate", "25", "-loop", "1", "-i", png,
       "-t", f"{seconds:.3f}", "-filter_complex",
       f"[0:v]scale=2560:1440,"
       f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih*0.42-(ih/zoom*0.42)':d=1:s={W}x{H}:fps=25,"
       f"setsar=1[bg];[bg][1:v]overlay=0:0", *ENC, "-an", out)


def clip_over(video, png, seconds, out):
    ff("-stream_loop", "-1", "-i", video, "-loop", "1", "-i", png, "-t", f"{seconds:.3f}", "-filter_complex",
       f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
       f"eq=brightness=-0.06:saturation=0.85[bg];[bg][1:v]overlay=0:0", *ENC, "-an", out)


# ---- ویدیوی کوتاه (یوتیوب Shorts، اینستاگرام Reels): خبر نخست، ایستاده، کمتر از یک دقیقه ----
SHORT_MAX = 58.0


def short_overlay(b, path):
    """قاب ایستاده‌ی ۱۰۸۰×۱۹۲۰: نشان و تیتر درشت در بالا، دعوت به دنبال کردن در پایین؛ میانه برای ویدیو."""
    SW, SH = 1080, 1920
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, SW, 640], fill=(8, 16, 40, 235))
    d.rectangle([0, 632, SW, 640], fill=GOLD + (255,))
    if os.path.exists(LOGO):
        mk = mark(96)
        img.alpha_composite(mk, (SW - 54 - mk.width, 48))
    d.text((SW - 74 - (mark(96).width if os.path.exists(LOGO) else 96), 70), "رسانه ایرانا", font=font("Black", 52), fill=GOLD, anchor="ra", direction="rtl", language="fa")
    d.text((60, 82), "خبر نخست", font=font("Bold", 40), fill=(220, 225, 235), anchor="la", direction="rtl", language="fa")
    title = b["items"][0]["title"] if b.get("items") else b["stamp"]
    for size in (68, 60, 52, 46):
        f = font("Black", size)
        lines = wrap(d, title, f, SW - 120)
        if len(lines) * size * 1.45 <= 430:
            break
    y = 190 + (430 - len(lines) * size * 1.45) / 2
    for line in lines:
        for k in range(4, 0, -1):
            d.text((SW / 2 + k, y + k), line, font=f, fill=(15, 25, 55), anchor="ma", direction="rtl", language="fa")
        d.text((SW / 2, y), line, font=f, fill=WHITE, anchor="ma", direction="rtl", language="fa")
        y += size * 1.45
    d.rectangle([0, 1268, SW, SH], fill=(8, 16, 40, 235))
    d.rectangle([0, 1268, SW, 1276], fill=GOLD + (255,))
    d.text((SW / 2, 1330), b["stamp"], font=font("Bold", 38), fill=(210, 215, 228), anchor="ma", direction="rtl", language="fa")
    d.text((SW / 2, 1440), "خبرهای ایران، سر هر ساعت", font=font("Black", 56), fill=WHITE, anchor="ma", direction="rtl", language="fa")
    d.text((SW / 2, 1540), "تلگرام: IranaMediaNews", font=font("Bold", 46), fill=GOLD, anchor="ma", direction="rtl", language="fa")
    d.text((SW / 2, 1620), "iranamedia.github.io", font=font("Bold", 40), fill=(210, 215, 228), anchor="ma")
    img.save(path)
    return path


# ---------- سرنما (thumbnail) هر بخش سیما ----------
# همسان: همیشه زمینه‌ی سرمه‌ای، نشان ایرانا، نوار زرین و «سیمای ایرانا».
# گوناگون: تیتر درشت خبر نخست، عکس یا فیلم همان خبر، و رنگ و برچسب موضوع.
ACCENTS = (                                             # (الگو، برچسب، رنگ)
    (PRINCE, "شهریار ایران", (224, 180, 82)),
    (re.compile(r"اعدام|به[\s\u200c]*دار"), "اعدام", (196, 30, 45)),
    (re.compile(r"خیزش|اعتراض|تجمع|شعار|اعتصاب"), "خیزش", (232, 110, 30)),
    (re.compile(r"بازداشت|زندان|حقوق[\s\u200c]*بشر|هەنگاو|هرانا"), "حقوق بشر", (150, 60, 160)),
    (re.compile(r"جنگ|حمله|موشک|پهپاد|انفجار|نفتکش|سپاه"), "جنگ و درگیری", (200, 60, 40)),
)


def accent_of(it):
    t = it.get("title", "") + " " + it.get("body", "")
    for pat, label, col in ACCENTS:
        if pat.search(t):
            return label, col
    return "خبر نخست", (60, 120, 220)


THUMB_CREDIT = {"text": ""}


def thumb_picture(b, wide, shots, intro_len):
    """عکس سرنما، تنها از خود رویداد: عکس شهریار ایران (اگر خبر ایشان نخست است) یا نمایی از پیام ویدیویی ایشان؛
    برای خبرهای دیگر، عکس رویداد از ربات یا کانال‌های رویداد (چهره‌ها تار)، وگرنه نقشه‌ی جای رویداد (tools/event_photo.py).
    نگاره‌ی گویندگان و فیلم نمادین هرگز در سرنما نمی‌آید؛ بی‌هیچ‌کدام، سرنما تنها نوشته است."""
    it = b["items"][0]
    THUMB_CREDIT["text"] = ""
    if not PRINCE.search(it.get("title", "")):
        try:
            sys.path.insert(0, os.path.join(HERE, "tools"))
            import event_photo
            pic, THUMB_CREDIT["text"] = event_photo.pick(it, accent_of(it)[0])
            return pic
        except Exception as e:
            print("نگاره‌ی رویداد:", e, flush=True)
            return None
    photos = prince_photos()
    if photos:
        k = sum(map(ord, b.get("stamp", ""))) % len(photos)          # هر بخش، عکسی دیگر
        return Image.open(photos[k]).convert("RGB")
    clip = [sh for sh in shots if sh["key"][0] == "clip"]
    if not clip:
        return None
    sh = clip[0]
    png = os.path.join(OUT, "thumb_src.png")
    try:
        ff("-ss", f"{intro_len + sh['start'] + min(sh['seconds'] * 0.5, 3.0):.2f}", "-i", wide, "-frames:v", "1", png)
        im = Image.open(png).convert("RGB")
        return im.crop((0, int(im.height * 0.09), im.width, int(im.height * 0.63)))   # بی‌نوار تیتر و ساعت
    except Exception:
        return None


def _fit_lines(d, text, weight, width, max_lines, sizes):
    for sz in sizes:
        f = font(weight, sz)
        ls = wrap(d, text, f, width)
        if len(ls) <= max_lines:
            return f, ls
    f = font(weight, sizes[-1])
    ls = wrap(d, text, f, width)[:max_lines]
    ls[-1] = ls[-1].rstrip("،.") + "…"
    return f, ls


def make_thumbs(b, wide, shots, intro_len):
    """سرنمای خوابیده (۱۲۸۰×۷۲۰، یوتیوب/تلگرام/فیسبوک) و ایستاده (۱۰۸۰×۱۹۲۰، شورتس/ریلز)."""
    from PIL import ImageFilter
    import numpy as np
    it = b["items"][0]
    label, col = accent_of(it)
    title = it.get("title", "")
    who, _, head = title.partition(":")
    if not head.strip() or len(who) > 28:
        who, head = "", title
    pic = thumb_picture(b, wide, shots, intro_len)
    hour = re.search(r"ساعت\s*[۰-۹\d]+", b.get("stamp", ""))
    day = re.search(r"،\s*(\S+\s+[۰-۹\d]+\s+\S+)", b.get("stamp", ""))
    when = " · ".join(x for x in ((hour.group(0) if hour else ""), (day.group(1) if day else "")) if x)
    lg = Image.open(os.path.join(HERE, "assets", "irana_logo_transparent.png")).convert("RGBA")
    outs = {}
    for tag, (Wd, Hd) in (("wide", (1280, 720)), ("tall", (1080, 1920))):
        im = Image.new("RGB", (Wd, Hd), BG)
        if not pic:                                        # زمینه‌ی نوشتاری: درخشش آرام به رنگ موضوع
            yy, xx = np.mgrid[0:Hd, 0:Wd].astype(np.float32)
            cx, cy = (Wd * 0.22, Hd * 0.62) if tag == "wide" else (Wd * 0.5, Hd * 0.70)
            g = np.exp(-(((xx - cx) / (Wd * 0.55)) ** 2 + ((yy - cy) / (Hd * 0.55)) ** 2))[..., None] * 0.45
            base = np.asarray(im).astype(np.float32)
            im = Image.fromarray(np.clip(base * (1 - g) + np.array(col, np.float32) * g, 0, 255).astype(np.uint8))
        if pic:                                            # عکس: نیمه‌ی چپ (خوابیده) یا بالا (ایستاده)، آمیخته با زمینه
            pw, ph = (int(Wd * 0.50), Hd) if tag == "wide" else (Wd, int(Hd * 0.46))
            if callable(pic):                              # نقشه‌ی جای رویداد، به اندازه‌ی همین قاب
                p = pic(pw, ph, col)
            else:
                r = max(pw / pic.width, ph / pic.height)
                p = pic.resize((int(pic.width * r) + 1, int(pic.height * r) + 1), Image.LANCZOS)
                top = 0 if (PRINCE.search(title) and tag == "wide") else (p.height - ph) // 3
                p = p.crop(((p.width - pw) // 2, top, (p.width - pw) // 2 + pw, top + ph))
            m = Image.new("L", (pw, ph), 255)
            md = ImageDraw.Draw(m)
            fade = int(pw * 0.35) if tag == "wide" else int(ph * 0.30)
            for k in range(fade):
                a = int(255 * k / fade)
                if tag == "wide":
                    md.line([(pw - 1 - k, 0), (pw - 1 - k, ph)], fill=a)
                else:
                    md.line([(0, ph - 1 - k), (pw, ph - 1 - k)], fill=a)
            im.paste(p, (0, 0), m)
            if THUMB_CREDIT["text"]:                       # یادکرد سرچشمه‌ی عکس
                cd = ImageDraw.Draw(im)
                cf = font("Medium", 22 if tag == "wide" else 30)
                cw = int(tw(cd, THUMB_CREDIT["text"], cf)) + 24
                cy = (Hd - 14 - cf.size - 26) if tag == "wide" else (ph - cf.size - 26)
                cd.rounded_rectangle((14, cy, 14 + cw, cy + cf.size + 14), radius=8, fill=(6, 12, 30))
                at_right(cd, 14 + cw - 12, cy + 5, THUMB_CREDIT["text"], cf, MIST)
        if tag == "tall":                                  # سایه‌ی بالا تا نام و ساعت روی عکس خوانا باشد
            sh = Image.new("L", (Wd, 300), 0)
            sd = ImageDraw.Draw(sh)
            for k in range(300):
                sd.line([(0, k), (Wd, k)], fill=int(190 * (1 - k / 300)))
            im.paste(Image.new("RGB", (Wd, 300), BG), (0, 0), sh)
        d = ImageDraw.Draw(im)
        d.rectangle((0, Hd - 14, Wd, Hd), fill=GOLD)                       # نوار زرین ایرانا (همسان)
        d.rectangle((0, 0, Wd, 10), fill=col)                               # رنگ موضوع (گوناگون)
        L = mark(130 if tag == "wide" else 170)
        im.paste(L, (Wd - L.width - 24, 26), L)
        brand = font("Black", 40 if tag == "wide" else 50)
        at_right(d, Wd - L.width - 40, 40, "سیمای ایرانا", brand, WHITE)
        at_right(d, Wd - L.width - 40, 40 + brand.size + 10, when, font("Medium", 28 if tag == "wide" else 36), MIST)
        if not pic:                                        # بی‌عکس رویداد: تنها نوشته، پهن و درشت، در میانه
            x1, x0, top = (Wd - 50, 50, 175) if tag == "wide" else (Wd - 60, 60, 300)
        elif tag == "wide":
            x1, x0, top = Wd - 40, int(Wd * 0.40), int(Hd * 0.33)
        else:
            x1, x0, top = Wd - 60, 60, int(Hd * 0.50)
        width, bottom = x1 - x0, Hd - 40
        lf = font("Black", 34 if tag == "wide" else 46)                     # برچسب موضوع
        wf = font("Black", 52 if tag == "wide" else 72) if who else None
        above = lf.size + 50 + (int(wf.size * 1.35) if wf else 0)
        if pic:
            sizes, maxl = ((84, 76, 68, 60, 54), 4) if tag == "wide" else ((110, 100, 90, 80, 72), 4)
        else:
            sizes, maxl = ((100, 92, 84, 76, 68, 60), 4) if tag == "wide" else ((128, 116, 104, 94, 84, 76), 6)
        room = bottom - top - above
        hf, ls = None, []
        for sz in sizes:                                  # بزرگ‌ترین اندازه‌ای که همه‌ی تیتر در جا بگنجد
            f = font("Black", sz)
            w_ = wrap(d, head.strip(), f, width)
            if len(w_) <= maxl and len(w_) * int(sz * 1.28) <= room:
                hf, ls = f, w_
                break
        if hf is None:
            hf = font("Black", sizes[-1])
            n = max(1, min(maxl, room // int(hf.size * 1.28)))
            ls = wrap(d, head.strip(), hf, width)
            if len(ls) > n:
                ls = ls[:n]; ls[-1] = ls[-1].rstrip("،.") + "…"
        lh = int(hf.size * 1.28)
        y = top + (max(0, (room - len(ls) * lh) // 2) if not pic else 0)
        lw = int(tw(d, label, lf)) + 40
        d.rounded_rectangle((x1 - lw, y, x1, y + lf.size + 24), radius=12, fill=col)
        at_right(d, x1 - 20, y + 8, label, lf, WHITE if col != GOLD else BG)
        y += lf.size + 50
        if wf:
            for k in range(4, 0, -1):
                at_right(d, x1 + k, y + k, who.strip() + ":", wf, (6, 12, 30))
            at_right(d, x1, y, who.strip() + ":", wf, GOLD)
            y += int(wf.size * 1.35)
        for ln in ls:
            for k in range(5, 0, -1):
                at_right(d, x1 + k, y + k, ln, hf, (6, 12, 30))
            at_right(d, x1, y, ln, hf, WHITE)
            y += lh
        out = os.path.join(OUT, f"thumb_{tag}.jpg")
        im.save(out, quality=88)
        outs[tag] = out
    small = os.path.join(OUT, "thumb_small.jpg")                           # برای «thumbnail» تلگرام (۳۲۰ پیکسل)
    Image.open(outs["wide"]).resize((320, 180), Image.LANCZOS).save(small, quality=80)
    print("سرنما:", label, "·", title[:60], flush=True)
    return outs


def make_short(b, wide, shots, intro_len):
    """خبر نخست (و پیام ویدیویی شهریار ایران اگر هست) از ویدیوی افقی، در قاب ایستاده."""
    first = next((s for s in shots if s["key"][0] == "story" and s["key"][1] == 0), None)
    if not first:
        return None
    end = first["start"] + first["seconds"]
    for s in shots:                                   # پیام ویدیویی پس از خبر نخست هم در ویدیوی کوتاه
        if s["key"][0] == "clip" and abs(s["start"] - end) < 4:
            end = s["start"] + s["seconds"]
    ss = max(first["start"] + intro_len - 0.3, 0)
    length = min(SHORT_MAX, end - first["start"] + 0.3)
    if length < 8:
        return None
    ov = short_overlay(b, os.path.join(OUT, "short_overlay.png"))
    out = os.path.join(OUT, "irana-short.mp4")
    ff("-ss", f"{ss:.2f}", "-i", wide, "-loop", "1", "-i", ov, "-t", f"{length:.2f}", "-filter_complex",
       "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:2,"
       "eq=brightness=-0.2[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2[v];[v][1:v]overlay=0:0,format=yuv420p[o];"
       f"[0:a]afade=t=in:d=0.3,afade=t=out:st={max(length - 0.8, 0):.2f}:d=0.8[au]",
       "-map", "[o]", "-map", "[au]", *ENC, "-g", "50", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
       "-ar", "48000", "-movflags", "+faststart", out)
    print(f"ویدیوی کوتاه: {out} {dur(out):.1f}s", flush=True)
    return out


def clip_prince_video(path, ss, png, seconds, out):
    """تکه‌ای از پیام ویدیویی شهریار ایران (ویدیوی ایستاده یا خوابیده)، با پس‌زمینه‌ی مات از خود ویدیو، بی‌صدا
    (صدای آن در صدای رادیو هست)."""
    ff("-ss", f"{ss:.2f}", "-i", path, "-loop", "1", "-i", png, "-t", f"{seconds:.3f}", "-filter_complex",
       f"[0:v]fps=25,split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
       f"gblur=sigma=28,eq=brightness=-0.18[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
       f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,tpad=stop_mode=clone:stop_duration=10[v];[v][1:v]overlay=0:0",
       *ENC, "-an", out)


def visuals(timeline, n_items):
    """بخش‌های صدا را به نماها تبدیل می‌کند: سرآغاز، هر خبر (با درنگ پس از آن)، سخن پایانی، آگهی."""
    shots = []
    for seg in timeline:
        key = ("clip", seg["file"], seg.get("ss", 0)) if seg["kind"] == "clip" else \
              ("story", seg["n"], seg.get("voice", "man")) if seg["kind"] == "story" and seg["n"] < n_items else \
              ("title",) if seg["kind"] in ("head", "sting") else \
              ("outro", seg.get("voice", "man")) if seg["kind"] in ("outro", "story") else \
              ("end",) if seg["kind"] == "promo" else None
        if key is None:                                   # درنگ: به نمای پیشین می‌پیوندد
            if shots: shots[-1][1] += seg["dur"]
            continue
        if shots and shots[-1][0] == key:
            shots[-1][1] += seg["dur"]
        else:
            shots.append([key, seg["dur"]])
    return shots


def plan(b, audio, tl):
    """نماها با زمان آغازشان در صدای رادیو؛ و بخش‌هایی که گوینده روی صفحه است (on_cam)."""
    shots = visuals(json.load(open(tl, encoding="utf-8"))["segments"], len(b["items"]))
    scale = dur(audio) / max(sum(s[1] for s in shots), 1)  # هم‌زمانی دقیق با صدای نهایی
    out, t = [], 0.0
    for i, (key, seconds) in enumerate(shots):
        seconds *= scale
        voice = key[2] if key[0] == "story" else key[1] if key[0] == "outro" else "man" if key[0] == "title" else None
        on_cam, lead = 0.0, 0.0
        mood = mood_of(b["items"][key[1]]) if key[0] == "story" else ""
        if voice and photo_src(voice, mood):
            if key[0] == "story":
                on_cam = min(ON_CAM_MAX, seconds * 0.45)
            elif key[0] == "outro":
                on_cam = min(ON_CAM_MAX, seconds)
            elif all(os.path.exists(p) for p in PRESENTER.values()):   # سرآغاز: دو گوینده، سپس بکتاش
                lead = min(TWO_SHOT, seconds * 0.3)
                on_cam = max(0.0, min(ON_CAM_MAX, seconds - lead - 3))
        out.append({"i": i, "key": list(key), "start": round(t, 3), "seconds": round(seconds, 3),
                    "voice": voice, "mood": mood, "lead": round(lead, 3), "on_cam": round(on_cam, 3),
                    "talk_start": round(t + lead, 3)})
        t += seconds
    return out


def studio_two():
    """نمای دور استودیو با هر دو گوینده پشت میز (assets/studio_two.png)؛ اگر نباشد، دو نیمه کنار هم."""
    out = os.path.join(OUT, "studio_two.png")
    if os.path.exists(out):
        return out
    masks = [os.path.join(HERE, "assets", f"presenter_{AN(v)}_person.png") for v in ("man", "woman")]
    if os.path.exists(PRESENTER["man"]) and all(os.path.exists(m) for m in masks):
        from PIL import ImageEnhance, ImageFilter
        # پس‌زمینه: استودیوی بکتاش (دیوار نقشه‌ی جهان و نمایشگرها)، روشن و تیز؛
        # جای خودِ او را نمایشگر بزرگ میانی با نشان ایرانا می‌گیرد
        img = Image.open(PRESENTER["man"]).convert("RGB").resize((W, H), Image.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(1.2))
        img = ImageEnhance.Brightness(ImageEnhance.Contrast(img).enhance(1.08)).enhance(1.1).convert("RGBA")
        d = ImageDraw.Draw(img)
        sx0, sx1, sy0, sy1 = int(W * 0.355), int(W * 0.645), int(H * 0.03), int(H * 0.72)
        d.rectangle([sx0 - 10, sy0 - 10, sx1 + 10, sy1], fill=(8, 12, 24, 255))      # قاب نمایشگر
        scr = Image.new("RGBA", (sx1 - sx0, sy1 - sy0))
        sd = ImageDraw.Draw(scr)
        for yy in range(scr.height):                                              # نور آبی نمایشگر
            t = yy / scr.height
            sd.line([(0, yy), (scr.width, yy)], fill=(int(18 + 20 * (1 - t)), int(40 + 45 * (1 - t)), int(95 + 70 * (1 - t)), 255))
        if os.path.exists(LOGO):
            mk = mark(300)
            if mk.width > scr.width * 0.9:
                mk = mk.resize((int(scr.width * 0.9), int(mk.height * scr.width * 0.9 / mk.width)), Image.LANCZOS)
            scr.alpha_composite(mk, ((scr.width - mk.width) // 2, int(scr.height * 0.12)))
        img.alpha_composite(scr, (sx0, sy0))
        img.convert("RGB").filter(ImageFilter.GaussianBlur(2)).save(os.path.join(OUT, "studio_two_back.png"))
        people = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        target_h, desk_top = int(H * 0.54), int(H * 0.72)
        placed = {}
        for voice, cx, mp in (("man", int(W * 0.23), masks[0]), ("woman", int(W * 0.77), masks[1])):
            ph = dressed(voice).convert("RGBA")
            ph.putalpha(Image.open(mp).convert("L").resize(ph.size))
            fz = AN(voice) == "firoozeh"                 # فیروزه: هم‌سر و هم‌اندازه‌ی بکتاش
            ph = ph.crop((0, 0, ph.width, int(ph.height * (0.97 if fz else 0.74))))   # نوار نوشته‌ی پایین عکس بیرون
            bb = ph.getbbox()
            ph = ph.crop(bb)
            if fz and "man" in placed:
                msc, mtop = placed["man"]
                sc = msc * BODY["man"]["shoulders"] / BODY["firoozeh"]["shoulders"]      # پیکرها هم‌اندازه
                y_head = mtop + BODY["man"]["top"] * msc                                   # بالای سرها هم‌تراز
                ph = ph.resize((int(ph.width * sc), int(ph.height * sc)), Image.LANCZOS)
                y = int(y_head - (BODY["firoozeh"]["top"] - bb[1]) * sc)
            else:
                sc = target_h / ph.height
                ph = ph.resize((int(ph.width * sc), int(ph.height * sc)), Image.LANCZOS)
                y = desk_top + 40 - ph.height
            placed[voice] = (sc, y - bb[1] * sc)       # بزرگ‌نمایی و جای لبه‌ی بالای عکس
            sh = Image.new("RGBA", ph.size, (0, 0, 0, 0))
            sh.putalpha(ph.getchannel("A").point(lambda a: int(a * 0.45)))
            x = cx - ph.width // 2
            for lay in (img, people):
                lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (x + 12, y + 10))
                lay.alpha_composite(ph, (x, y))
        people.save(os.path.join(OUT, "studio_two_people.png"))
        desk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for lay in (img, desk):
            d = ImageDraw.Draw(lay)                    # میز خبر با لبه‌ی زرین
            d.polygon([(int(W * 0.06), desk_top), (int(W * 0.94), desk_top), (W, H), (0, H)], fill=(14, 26, 58, 255))
            d.rectangle([int(W * 0.06), desk_top, int(W * 0.94), desk_top + 10], fill=GOLD + (255,))
        desk.save(os.path.join(OUT, "studio_two_desk.png"))
        img.convert("RGB").save(out)
        return out
    man, woman = studio_photo("man"), studio_photo("woman")
    if not (man and woman):
        return None
    img = Image.new("RGB", (W, H), BG)
    for x, ph in ((0, man), (W // 2, woman)):
        im = Image.open(ph).convert("RGB")
        img.paste(im.crop(((W - W // 2) // 2, 0, (W - W // 2) // 2 + W // 2, H)), (x, 0))
    ImageDraw.Draw(img).rectangle([W // 2 - 3, 0, W // 2 + 3, H], fill=GOLD)
    img.save(out)
    return out


PRINCE_DIR = os.path.join(HERE, "assets", "prince")   # عکس‌های شهریار ایران که خود رسانه می‌گذارد


def prince_photos(rank=0):
    """عکس‌های تازه‌ترین روزِ پوشه‌ی assets/prince (نام با تاریخ آغاز می‌شود، مانند 2026-11-07-frankfurt.jpeg)،
    به ترتیب نام، هر کدام در قاب ۱۶:۹. فایل‌های بدونِ تاریخ تنها هنگامی به کار می‌آیند که فایل تاریخ‌دار نباشد."""
    if not os.path.isdir(PRINCE_DIR):
        return []
    pics = sorted(f for f in os.listdir(PRINCE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
    dated = [f for f in pics if re.match(r"\d{4}-\d{2}-\d{2}", f)]
    if dated:                                          # rank 0: تازه‌ترین روز (تازه‌ترین خبر ایشان)؛ rank 1: روز پیش از آن
        days = sorted({f[:10] for f in dated}, reverse=True)
        if rank >= len(days):
            return []
        day = days[rank]
        pics = [f for f in dated if f[:10] == day]
    else:
        pics = pics[-1:]
    from PIL import ImageFilter
    outs = []
    for k, name in enumerate(pics[:6]):
        out = os.path.join(OUT, f"prince_photo_{rank}_{k}.png")
        if not os.path.exists(out):
            im = Image.open(os.path.join(PRINCE_DIR, name)).convert("RGB")
            bg = im.copy()
            scale = max(W / bg.width, H / bg.height)
            bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1)).crop((0, 0, W, H))
            bg = bg.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.55))
            scale = min(W / im.width, H / im.height)
            fg = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
            bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
            bg.save(out)
            print(f"عکس شهریار ایران: {name}", flush=True)
        outs.append(out)
    return outs


def talk_clip(i):
    p = os.path.join(TALK_DIR, f"talk_{i:02d}.mp4")
    return p if os.path.exists(p) and os.path.getsize(p) > 10_000 else None


def clip_talking(video, png, seconds, out):
    """گوینده‌ی گویا (SadTalker) با نوار تیتر روی آن؛ اندازه‌ی زمان درست به اندازه‌ی گفتار."""
    ff("-i", video, "-framerate", "25", "-loop", "1", "-i", png, "-t", f"{seconds:.3f}", "-filter_complex",
       f"[0:v]fps=25,scale={W}:{H},setsar=1,tpad=stop_mode=clone:stop_duration=2[v];[v][1:v]overlay=0:0",
       *ENC, "-an", out)


def _voice_of(photo):
    m = re.search(r"studio_(man|woman)(?:_(\w+))?\.png$", photo or "")
    return (m.group(1), m.group(2) or "") if m else (None, "")


def still_presenter(photo, png, seconds, out):
    voice, mood = _voice_of(photo)
    if voice and clip_depth(photo, voice, mood, png, seconds, out):
        return
    clip_presenter(photo, png, seconds, out)


def presenter_clip(i, photo, png, seconds, out):
    talk = talk_clip(i)
    if talk:
        voice, mood = _voice_of(photo)
        if voice and clip_depth(talk, voice, mood, png, seconds, out, video=True):
            print(f"shot {i}: گوینده‌ی گویا، سه‌بعدی", flush=True); return
        try:
            clip_talking(talk, png, seconds, out); print(f"shot {i}: گوینده‌ی گویا", flush=True); return
        except subprocess.CalledProcessError:
            pass
    still_presenter(photo, png, seconds, out)


def build():
    b = json.load(open(BULLETIN, encoding="utf-8"))
    audio, tl = os.path.join(SITE, "latest.mp3"), os.path.join(SITE, "timeline.json")
    if not (os.path.exists(audio) and os.path.exists(tl)):
        print("ساعت بی‌گفتار یا صدای رادیو آماده نیست؛ تلویزیون ساخته نمی‌شود"); return None
    os.makedirs(OUT, exist_ok=True)
    fonts()
    clips = []
    shots = plan(b, audio, tl)
    for sh in shots:
        i, key, seconds, on_cam = sh["i"], tuple(sh["key"]), sh["seconds"], sh["on_cam"]
        out, png = os.path.join(OUT, f"shot_{i:02d}.mp4"), os.path.join(OUT, f"shot_{i:02d}.png")
        if key[0] == "title":
            lead, two, man = sh.get("lead", 0), studio_two(), studio_photo("man")
            if lead and two and man:                       # دو گوینده در استودیو، سپس بکتاش تیترها را می‌خواند
                lt = os.path.join(OUT, "lt_head.png")
                lower_third(b, lt, "تازه‌ترین رویدادهای ایران", "رسانه ایرانا")
                lay = [os.path.join(OUT, f"studio_two_{n}.png") for n in ("back", "people", "desk")]
                try:
                    if not (DEPTH and all(os.path.exists(x) for x in lay)):
                        raise subprocess.CalledProcessError(1, "no layers")
                    clip_parallax([{"src": lay[0], "zoom": 0.03, "drift": 0.5},       # دیوار و نمایشگر
                                   {"src": lay[1], "zoom": 0.07, "drift": -0.3},      # گوینده‌ها
                                   {"src": lay[2], "zoom": 0.12, "drift": -0.6}],     # میز (نزدیک‌ترین)
                                  lt, lead, out)
                    print("نمای دو گوینده: سه‌بعدی", flush=True)
                except subprocess.CalledProcessError:
                    clip_presenter(two, lt, lead, out)
                clips.append(out)
                if on_cam:
                    out = os.path.join(OUT, f"shot_{i:02d}m.mp4")
                    lower_third(b, lt, b["items"][0]["title"] if b["items"] else "تیترهای این بخش", "تیترهای این بخش")
                    presenter_clip(i, man, lt, on_cam, out); clips.append(out)
                out = os.path.join(OUT, f"shot_{i:02d}t.mp4")
                slide_title(b, png); clip_still(png, seconds - lead - on_cam, out)
            else:
                slide_title(b, png); clip_still(png, seconds, out)
        elif key[0] == "clip":
            path = os.path.join(HERE, "assets", "prince", key[1])
            lower_third(b, png, b["items"][0]["title"], "پیام ویدیویی شهریار ایران")
            try:
                clip_prince_video(path, float(key[2]), png, seconds, out)
                print(f"shot {i}: پیام ویدیویی شهریار ایران", flush=True)
            except subprocess.CalledProcessError:
                slide_story(b, 0, png); clip_still(png, seconds, out)
        elif key[0] == "end":
            if os.path.exists(AD_VIDEO):
                try:
                    clip_ad(seconds, out)
                except subprocess.CalledProcessError:
                    slide_end(b, png); clip_still(png, seconds, out)
            else:
                slide_end(b, png); clip_still(png, seconds, out)
        elif key[0] == "outro":
            photo = studio_photo(key[1])
            if photo:
                lower_third(b, png, "تازه‌ترین رویدادهای ایران · شبانروزی، سر هر ساعت", "رسانه ایرانا")
                if on_cam < seconds - 0.05:                 # گوینده‌ی گویا، سپس عکس با حرکت آرام
                    presenter_clip(i, photo, png, on_cam, out); clips.append(out)
                    out = os.path.join(OUT, f"shot_{i:02d}b.mp4")
                    still_presenter(photo, png, seconds - on_cam, out)
                else:
                    presenter_clip(i, photo, png, seconds, out)
            else:
                slide_end(b, png); clip_still(png, seconds, out)
        else:
            n, voice = key[1], key[2]
            photo = studio_photo(voice, sh.get("mood", "")) if on_cam else None   # خبر سوگ: گوینده‌ی جدی یا هیچ
            count = f"خبر {str(n + 1).translate(FA)} از {str(min(len(b['items']), 5)).translate(FA)}"
            bv = broll(b["items"][n], n)
            # گوینده خبر را آغاز می‌کند (گویا، اگر ساخته شده)، سپس فیلم نمادین یا قاب خبر
            on_cam = on_cam if photo else 0
            if on_cam:
                lower_third(b, png, b["items"][n]["title"], count)
                presenter_clip(i, photo, png, on_cam, out)
                clips.append(out)
                out, png = os.path.join(OUT, f"shot_{i:02d}b.mp4"), os.path.join(OUT, f"shot_{i:02d}b.png")
            rest = seconds - on_cam
            if rest > 0.05:
                if bv:
                    slide_story(b, n, png, over_video=True)
                    try:
                        clip_over(bv, png, rest, out)
                    except subprocess.CalledProcessError:
                        bv = None
                rank = sum(1 for j in range(n) if PRINCE.search(b["items"][j]["title"]))   # چندمین خبر ایشان
                pps = prince_photos(rank) if not bv and PRINCE.search(b["items"][n]["title"]) else []
                if pps:                                    # خبر شهریار ایران: عکس‌های ایشان یکی پس از دیگری، با حرکت آرام
                    slide_story(b, n, png, over_video=True, credit="عکس: حساب رسمی شهریار ایران")
                    pps = pps[:max(1, int(rest // 3))]     # هر عکس دست‌کم ۳ ثانیه
                    part = rest / len(pps)
                    for k, pp in enumerate(pps[:-1]):
                        seg = os.path.join(OUT, f"shot_{i:02d}p{k}.mp4")
                        clip_presenter(pp, png, part, seg)
                        clips.append(seg)
                    clip_presenter(pps[-1], png, rest - part * (len(pps) - 1), out)
                elif not bv:
                    slide_story(b, n, png); clip_still(png, rest, out)
            else:
                continue
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
    wide = os.path.join(OUT, "irana-tv.mp4")
    want = sum(dur(p) for p in parts) - (1.2 if len(parts) == 2 else 0)
    if len(parts) == 2:                                    # آرم آغاز آرام در استودیو محو می‌شود
        off = max(dur(parts[0]) - 1.2, 0.5)
        ff("-reinit_filter", "0", "-i", parts[0], "-reinit_filter", "0", "-i", parts[1], "-filter_complex",
           f"[0:v]settb=AVTB,fps=25[a];[1:v]settb=AVTB,fps=25[b];[a][b]xfade=transition=fade:duration=1.2:offset={off:.2f}[v];"
           f"[0:a][1:a]acrossfade=d=1.2[au]", "-map", "[v]", "-map", "[au]",
           *ENC, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", wide)
    else:
        lst2 = os.path.join(OUT, "parts.txt")
        open(lst2, "w").write("".join(f"file '{p}'\n" for p in parts))
        ff("-f", "concat", "-safe", "0", "-i", lst2, *ENC, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", wide)
    if dur(wide) < want - 1.5:                             # بریده شد: بی محو، پشت سر هم
        print(f"هشدار: ویدیو {dur(wide):.1f}s به جای {want:.1f}s؛ ساختن دوباره بی محو", flush=True)
        ins = [x for p in parts for x in ("-reinit_filter", "0", "-i", p)]
        ff(*ins, "-filter_complex", "".join(f"[{k}:v]settb=AVTB,fps=25,setsar=1[v{k}];" for k in range(len(parts)))
           + "".join(f"[v{k}][{k}:a]" for k in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[v][au]",
           "-map", "[v]", "-map", "[au]", *ENC, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", wide)
    if dur(wide) < want - 1.5:
        raise SystemExit(f"ویدیوی تلویزیون کوتاه است: {dur(wide):.1f}s به جای {want:.1f}s")
    tall = os.path.join(OUT, "irana-tv-tall.mp4")
    ff("-i", wide, "-filter_complex",
       "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:2,"
       "eq=brightness=-0.15[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2",
       *ENC, "-g", "50", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
       "-movflags", "+faststart", tall)                    # ویژگی‌هایی که اینستاگرام می‌پذیرد
    print(f"TV: {wide} {dur(wide):.1f}s {os.path.getsize(wide)//1024} KB · {tall}", flush=True)
    try:
        make_thumbs(b, wide, shots, dur(parts[0]) - 1.2 if len(parts) == 2 else 0.0)
    except Exception as ex:                                # سرنما نباید سیما را بایستاند
        print("سرنما ساخته نشد:", ex, flush=True)
    try:
        make_short(b, wide, shots, (dur(parts[0]) - 1.2) if len(parts) == 2 else 0.0)
    except Exception as e:                            # ویدیوی کوتاه نشد: برنامه‌ی اصلی می‌ماند
        print("ویدیوی کوتاه ساخته نشد:", str(e)[:200], flush=True)
    return wide


def caption(b):
    first = (b.get("items") or [{}])[0]
    if PRINCE.search(first.get("title", "")):          # زیرنویس: تیتر و خبر شهریار ایران
        body = first.get("body", "")
        body = body if len(body) <= 450 else body[:450].rsplit(" ", 1)[0] + "…"
        lines = [f"📺 {first['title']}", "", body, "", f"تلویزیون ایرانا · {b['stamp']}", ""]
        rest = b["items"][1:3]                          # روی‌هم بیش از سه تیتر نه
    else:
        lines, rest = [f"📺 تلویزیون ایرانا · {b['stamp']}", ""], b["items"][:3]
    for it in rest:
        lines.append("▪️ " + it["title"])
    lines += ["", CHANNEL]
    return "\n".join(lines)[:1000]


TV_LAST = os.path.join(HERE, "bulletin", "tv_last.json")      # واپسین برنامه‌ی سیما در هر جا (برای پیوند «برنامه‌ی پیشین»)
TG_PUBLIC = os.environ.get("TELEGRAM_CHANNEL_USERNAME", "IranaMediaNews")


def tv_last():
    try:
        return json.load(open(TV_LAST, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def tv_last_set(**kv):
    d = tv_last(); d.update({k: v for k, v in kv.items() if v})
    json.dump(d, open(TV_LAST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def send(path, cap):
    boundary = uuid.uuid4().hex
    body = b""
    prev = tv_last().get("telegram")
    rows = []
    if prev:                                               # پایان هر برنامه به برنامه‌ی پیشین سیمای ایرانا پیوند دارد
        rows.append([{"text": "▶️ برنامه‌ی پیشین سیمای ایرانا", "url": f"https://t.me/{TG_PUBLIC}/{prev}"}])
    rows.append([{"text": "📱 اپ ایرانا", "url": "https://iranamedia.github.io/irana.apk"},
                 {"text": "🌐 تارنما", "url": "https://iranamedia.github.io/"}])
    for k, v in {"chat_id": CHANNEL, "caption": cap, "supports_streaming": "true",
                 "width": str(W), "height": str(H), "duration": str(int(dur(path))),
                 "reply_markup": json.dumps({"inline_keyboard": rows}, ensure_ascii=False)}.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for name, fn in (("cover", "thumb_wide.jpg"), ("thumbnail", "thumb_small.jpg")):     # سرنمای ایرانا
        tp = os.path.join(os.path.dirname(path), fn)
        if os.path.exists(tp):
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{fn}\"\r\n"
                     "Content-Type: image/jpeg\r\n\r\n").encode() + open(tp, "rb").read() + b"\r\n"
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
    if res.get("ok"):
        mid = (res.get("result") or {}).get("message_id")
        if mid and prev:                                   # برنامه‌ی پیشین هم به این برنامه پیوند می‌یابد («برنامه‌ی پسین»)
            try:
                kb = {"inline_keyboard": [[{"text": "▶️ برنامه‌ی پیشین", "url": f"https://t.me/{TG_PUBLIC}/{tv_last().get('telegram_prev', '')}"}] if tv_last().get("telegram_prev") else [],
                                          [{"text": "⏭ برنامه‌ی پسین سیمای ایرانا", "url": f"https://t.me/{TG_PUBLIC}/{mid}"}],
                                          [{"text": "📱 اپ ایرانا", "url": "https://iranamedia.github.io/irana.apk"},
                                           {"text": "🌐 تارنما", "url": "https://iranamedia.github.io/"}]]}
                kb["inline_keyboard"] = [r for r in kb["inline_keyboard"] if r]
                q = urllib.parse.urlencode({"chat_id": CHANNEL, "message_id": prev, "reply_markup": json.dumps(kb, ensure_ascii=False)})
                urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup?{q}", timeout=30).read()
            except Exception as e:
                print("پیوند برنامه‌ی پسین نشد:", str(e)[:150], flush=True)
        tv_last_set(telegram=mid, telegram_prev=prev)
    return res.get("ok")


if __name__ == "__main__":
    if "--plan" in sys.argv:                            # بخش‌های گوینده‌دار برای ساختن هم‌زمان
        bb = json.load(open(BULLETIN, encoding="utf-8"))
        audio, tl = os.path.join(SITE, "latest.mp3"), os.path.join(SITE, "timeline.json")
        shots = plan(bb, audio, tl) if os.path.exists(audio) and os.path.exists(tl) else []
        talk = [s for s in shots if s["on_cam"] > 0.5]
        json.dump(talk, open(os.path.join(SITE, "talk_plan.json"), "w"), ensure_ascii=False)
        print(json.dumps([s["i"] for s in talk]))
        sys.exit(0)
    if "--send-only" in sys.argv:                       # سر ساعت: فرستادن ویدیوی ساخته‌شده
        wide = os.path.join(OUT, "irana-tv.mp4")
        if not os.path.exists(wide): print("ویدیوی تلویزیون نیست"); sys.exit(0)
        ok = BOT_TOKEN and send(wide, caption(json.load(open(BULLETIN, encoding="utf-8"))))
        sys.exit(0 if ok else 1)
    wide = build()
    if wide and BOT_TOKEN and "--no-send" not in sys.argv:
        if not send(wide, caption(json.load(open(BULLETIN, encoding="utf-8")))):
            sys.exit(1)
