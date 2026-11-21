"""نگاره‌ی رویداد برای سرنمای سیما، به این ترتیب:
۱. عکسی که رسانه برای ایرانامن‌بات فرستاده و با خبر نخست می‌خواند (assets/events، فهرست در bulletin/bot_inbox.json)
۲. عکس کانال‌های تلگرامی هه‌نگاو، کُردپا، ۱۵۰۰ تصویر و هرانا که با خبر نخست می‌خواند (bulletin/events.json)؛
   چهره‌ها همیشه تار می‌شوند (اگر چهره‌یاب در دسترس نباشد، این عکس‌ها به کار نمی‌روند)
۳. نقشه‌ی ایران با نشان جای رویداد (assets/geo/iran.json)
خروجی: (Image یا تابعِ (پهنا، بلندا، رنگ) ← Image، یادکرد سرچشمه) یا (None, "")."""
import datetime, json, math, os, re, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS = os.path.join(HERE, "bulletin", "events.json")
BOT = os.path.join(HERE, "bulletin", "bot_inbox.json")
EV_DIR = os.path.join(HERE, "assets", "events")
GEO = os.path.join(HERE, "assets", "geo", "iran.json")
MAX_AGE_H = 36

STOP = set("""این آن که از به با در را برای است بود شد شده شدند می‌شود های ها یک پس تا هم نیز اما یا چه کرد کردند کرده
دارد داشت گفت گفته گزارش خبر روز روزهای سال ماه امروز دیروز پیش هر همه دیگر خود وی او آنها ایشان باید نمی بر بی
جمهوری اسلامی ایران ایرانی رژیم حکومت مردم شهر استان شهرستان کشور خبرگزاری همچنین مقامات شرکت امنیتی دریافت علیه
هدف قرار گرفت داد دادند کردن شدن کند کنند کنید شود شوند گرفته گرفتند داده اند است، بوده باشد نیست هست بین درباره
پیرامون سوی سپس اکنون هنوز تنها بیش کمتر بیشتر چند چندین برخی آبان آذر دی بهمن اسفند فروردین اردیبهشت خرداد
تیر مرداد شهریور مهر شنبه یکشنبه دوشنبه سه‌شنبه چهارشنبه پنجشنبه جمعه بامداد شامگاه ساعت امسال پارسال گذشته آینده
اعلام اعلام‌کرد نوشت افزود گفتگو گفتگوی تاکید تأکید منابع رسانه رسانه‌ها انتشار منتشر""".split())
PLACE_STOP = set("""قوم شهریار قدس سده گلستان بهارستان سهند الوند پیشین سنگر ولایت شهرستان استان هرات دیر بنک بنگ کشف شال
ماهان مهاجران پادگان اهرم انار کیان مهران صدرا ابریشم نور ساسان تیران بهار ایمان کمال مرکز آزادی امام انقلاب
ایران کشت اجباری صفا سیمین خوشاب قیر عین لار کوار گرمی رودبار دوشا
عمان کویت عراق ترکیه افغانستان پاکستان قطر بحرین مصر لبنان سوریه اسرائیل روسیه چین هند آمریکا اروپا ژاپن یمن
عربستان امارات دبی بغداد کابل باکو ایروان مسکو لندن پاریس برلین واشینگتن نجف کربلا بصره اربیل سلیمانیه""".split())


def _norm(s):
    return (s or "").replace("ي", "ی").replace("ك", "ک").replace("‌", " ")


L = "\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC\u06C0\u0622"   # تنها حرف‌ها (بی «،» و نشانه‌ها)


def tokens(s):
    return {w for w in re.findall(f"[{L}]{{3,}}", _norm(s)) if w not in STOP}


_geo = None


def geo():
    global _geo
    if _geo is None:
        _geo = json.load(open(GEO, encoding="utf-8")) if os.path.exists(GEO) else {}
    return _geo


def places_in(text):
    """نام جاهای ایران در نوشته، به ترتیب آمدن. شهرهای بزرگ‌تر از ۱۵هزار همه‌جا؛ کوچک‌ترها تنها پس از
    «شهر، شهرستان، روستای، بخش، استان، در، مردم». واژه‌های دوپهلو (مانند قدس، بهارستان، شهریار) کنار می‌روند."""
    text = " " + _norm(text) + " "
    hits = []
    for name, (lon, lat, pop) in sorted(geo().get("places", {}).items(), key=lambda kv: -len(kv[0])):
        n = _norm(name)
        if n in PLACE_STOP or len(n) < 3:
            continue
        pre = "" if (pop == 0 or pop >= 15000) else r"(?:شهر|شهرستان|روستای|روستا|بخش|استان|در|مردم)\s+"
        m = re.search(pre + f"(?<![{L}])" + re.escape(n) + f"(?![{L}])", text)
        if m and not any(n in h for _, h in hits):
            hits.append((m.end() - len(n), n))
    return [n for _, n in sorted(hits)]


def _age_h(iso):
    try:
        t = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600
    except Exception:
        return 1e9


def _score(lead_text, lead_places, text):
    sp = len(set(lead_places) & set(places_in(text)))
    sw = len(tokens(lead_text) & tokens(text))
    return sp, sw


# ---------- چهره‌ها: همیشه تار ----------

def blur_faces(im):
    """همه‌ی چهره‌ها را تار می‌کند؛ اگر چهره‌یاب نیست، None (عکس به کار نمی‌رود)."""
    try:
        import cv2, numpy as np
    except Exception:
        return None
    from PIL import Image, ImageFilter, ImageDraw
    arr = np.asarray(im.convert("RGB"))
    model = os.path.join(HERE, "assets", "models", "face_yunet.onnx")
    if not (hasattr(cv2, "FaceDetectorYN") and os.path.exists(model)):
        return None
    boxes = []
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    for scale in (1.0, 2.0):                          # بزرگ‌نمایی برای چهره‌های کوچک در عکس‌های شلوغ
        src = cv2.resize(bgr, None, fx=scale, fy=scale) if scale != 1 else bgr
        if max(src.shape[:2]) > 3000:
            continue
        det = cv2.FaceDetectorYN.create(model, "", (src.shape[1], src.shape[0]), 0.55, 0.3, 5000)
        _, faces = det.detect(src)
        for f in (faces if faces is not None else []):
            x, y, w, h = (float(v) / scale for v in f[:4])
            boxes.append((x, y, w, h))
    try:                                              # گذر دوم (اگر در این OpenCV هست)
        g = cv2.equalizeHist(cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY))
        for name in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
            hp = os.path.join(cv2.data.haarcascades, name)
            c = cv2.CascadeClassifier(hp) if os.path.exists(hp) else None
            if c is not None and not c.empty():
                boxes += [tuple(map(float, b)) for b in c.detectMultiScale(g, 1.08, 5, minSize=(20, 20))]
    except Exception:
        pass
    if not boxes:
        return im
    out = im.convert("RGB").copy()
    strong = out.filter(ImageFilter.GaussianBlur(max(8, out.width // 60)))
    mask = Image.new("L", out.size, 0)
    d = ImageDraw.Draw(mask)
    for (x, y, w, h) in boxes:
        m = 0.35
        d.ellipse((x - w * m, y - h * m * 1.2, x + w * (1 + m), y + h * (1 + m * 1.4)), fill=255)
    out.paste(strong, (0, 0), mask.filter(ImageFilter.GaussianBlur(6)))
    print(f"نگاره‌ی رویداد: {len(boxes)} چهره تار شد", flush=True)
    return out


# ---------- سرچشمه‌ها ----------

def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (IranaMedia)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _tg_image(post):
    from PIL import Image
    import io
    urls = [post.get("img")] if post.get("img") else []
    try:                                              # نشانی تازه از برگه‌ی خود پست (نشانی‌های کهنه از کار می‌افتند)
        page = _fetch(f"https://t.me/{post['channel']}/{post['id']}?embed=1&mode=tme").decode("utf-8", "replace")
        urls = re.findall(r"background-image:url\('([^']+)'\)", page)[:1] + urls
    except Exception:
        pass
    for u in urls:
        try:
            return Image.open(io.BytesIO(_fetch(u))).convert("RGB")
        except Exception:
            continue
    return None


def bot_candidates():
    if not os.path.exists(BOT):
        return []
    out = []
    for f in json.load(open(BOT, encoding="utf-8")).get("files", []):
        if f.get("kind") != "event" or _age_h(f.get("received", "")) > MAX_AGE_H:
            continue
        p = os.path.join(EV_DIR, f.get("still") or f["file"])
        if os.path.exists(p) and p.lower().endswith((".jpg", ".jpeg", ".png")):
            out.append({"path": p, "text": f.get("caption", ""), "time": f.get("received", ""),
                        "source": f.get("source", "")})
    return out


def channel_candidates():
    if not os.path.exists(EVENTS):
        return []
    return [p for p in json.load(open(EVENTS, encoding="utf-8")).get("posts", [])
            if _age_h(p.get("time", "")) <= MAX_AGE_H]


def pick(item, label=""):
    from PIL import Image
    lead = item.get("title", "") + " " + item.get("body", "")[:400]
    lead_places = places_in(item.get("title", "") + " " + item.get("body", "")[:200])
    best = None
    for c in bot_candidates():                        # ۱. ربات (گزینش خود رسانه): آستانه‌ی پایین‌تر
        sp, sw = _score(lead, lead_places, c["text"])
        s = sp * 6 + sw
        bare = not c["text"].strip() and _age_h(c["time"]) <= 12    # بی‌نوشته: تنها تا ۱۲ ساعت، برای خبر نخست همان هنگام
        if (sp or sw >= 3 or bare) and (best is None or (s, c["time"]) > best[0]):
            best = ((s, c["time"]), c)
    if best:
        c = best[1]
        print("نگاره‌ی رویداد از ربات:", os.path.basename(c["path"]), flush=True)
        return Image.open(c["path"]).convert("RGB"), ("عکس: " + c["source"]) if c["source"] else ""
    ranked = []
    for c in channel_candidates():                   # ۲. کانال‌های رویداد
        sp, sw = _score(lead, lead_places, c.get("text", ""))
        if (sp and sp * 6 + sw >= 9) or sw >= 9:
            ranked.append(((sp * 6 + sw, c.get("time", "")), c))
    for _, c in sorted(ranked, key=lambda r: r[0], reverse=True)[:3]:
        im = _tg_image(c)
        if im is None or min(im.size) < 300:
            continue
        safe = blur_faces(im)
        if safe is None:
            print("چهره‌یاب نیست؛ عکس کانال به کار نرفت", flush=True)
            break
        print("نگاره‌ی رویداد از", c["channel"], c["id"], flush=True)
        return safe, "عکس: " + c.get("source", c["channel"])
    if lead_places:                                   # ۳. نقشه‌ی جای رویداد
        name = lead_places[0]
        if not (name == "تهران" and label == "خبر نخست"):
            lon, lat, _ = geo()["places"].get(name) or next(v for k, v in geo()["places"].items() if _norm(k) == name)
            print("نقشه‌ی رویداد:", name, flush=True)
            return (lambda w, h, col: draw_map(name, lon, lat, w, h, col)), ""
    return None, ""


# ---------- نقشه ----------

def draw_map(name, lon, lat, w, h, col):
    """نقشه‌ی ایران (مرز زرین، استان‌ها کم‌رنگ، همسایگان تیره) و نشان درخشان جای رویداد."""
    from PIL import Image, ImageDraw, ImageFilter
    import sys
    import numpy as np
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import tv
    S = 2
    W2, H2 = w * S, h * S
    G = geo()
    k = math.cos(math.radians(32.5))
    xs = [p[0] * k for r in G["outline"] for p in r]
    ys = [-p[1] for r in G["outline"] for p in r]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    if w <= h * 1.0:                                   # قاب ایستاده‌تر (سرنمای خوابیده: نیمه‌ی چپ)
        box_w, box_h, cx, cy = W2 * 0.80, H2 * 0.74, W2 * 0.44, H2 * 0.55
    else:                                              # قاب پهن‌تر (سرنمای ایستاده: بالا)
        box_w, box_h, cx, cy = W2 * 0.90, H2 * 0.74, W2 * 0.50, H2 * 0.57
    sc = min(box_w / bw, box_h / bh)
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

    def P(lo, la):
        return (cx + (lo * k - mx) * sc, cy + (-la - my) * sc)

    im = Image.new("RGB", (W2, H2), tv.BG)
    d = ImageDraw.Draw(im)
    for r in G.get("neighbours", []):
        pts = [P(*p) for p in r]
        d.polygon(pts, fill=(14, 26, 56), outline=(30, 48, 92))
    glow = Image.new("RGB", (W2, H2), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in G["outline"]:
        gd.line([P(*p) for p in r] + [P(*r[0])], fill=tv.GOLD, width=10 * S)
    glow = glow.filter(ImageFilter.GaussianBlur(14 * S))
    im = Image.fromarray(np.clip(np.asarray(im).astype(np.float32) + np.asarray(glow).astype(np.float32) * 0.35, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for r in G["outline"]:
        d.polygon([P(*p) for p in r], fill=(34, 62, 122))
    for r in G.get("provinces", []):
        d.line([P(*p) for p in r] + [P(*r[0])], fill=(70, 102, 170), width=max(1, S))
    for r in G["outline"]:
        d.line([P(*p) for p in r] + [P(*r[0])], fill=tv.GOLD, width=3 * S, joint="curve")
    x, y = P(lon, lat)
    halo = Image.new("L", (W2, H2), 0)
    hd = ImageDraw.Draw(halo)
    for rr, a in ((70, 70), (46, 120), (28, 190)):
        hd.ellipse((x - rr * S, y - rr * S, x + rr * S, y + rr * S), fill=a)
    halo = halo.filter(ImageFilter.GaussianBlur(10 * S))
    im.paste(Image.new("RGB", (W2, H2), col), (0, 0), halo)
    d = ImageDraw.Draw(im)
    d.ellipse((x - 14 * S, y - 14 * S, x + 14 * S, y + 14 * S), fill=(255, 255, 255), outline=col, width=5 * S)
    f = tv.font("Black", 40 * S)
    tw_ = tv.tw(d, name, f)
    pad = 14 * S
    right = x - 28 * S if x - 28 * S - tw_ - 2 * pad > 10 * S else x + 28 * S + tw_ + 2 * pad
    top = y - f.size * 0.75
    d.rounded_rectangle((right - tw_ - 2 * pad, top, right, top + f.size * 1.5), radius=12 * S, fill=(8, 14, 34), outline=col, width=3 * S)
    tv.at_right(d, right - pad, top + f.size * 0.12, name, f, (255, 255, 255))
    return im.resize((w, h), Image.LANCZOS)
