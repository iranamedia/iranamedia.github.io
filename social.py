"""پخش خبرنامه‌ی رسانه ایرانا در شبکه‌های اجتماعی.

از صدای ساخته‌شده‌ی رادیو (_site/latest.mp3) و خبرنامه (bulletin/latest.json) یک ویدیوی
عمودی ۱۰۸۰×۱۹۲۰ می‌سازد (نشان، نام، ساعت و تاریخ، سه تیتر مهم، موج صدا) و آن را در
فیسبوک، اینستاگرام (ریلز)، یوتیوب و ایکس منتشر می‌کند.

هر شبکه تنها هنگامی پخش می‌شود که کلیدهایش در GitHub Secrets باشد؛ نبودِ کلید = رد شدن بی‌خطا.
  فیسبوک:   META_PAGE_ID, META_PAGE_TOKEN
  اینستاگرام: IG_USER_ID (+ META_PAGE_TOKEN)
  یوتیوب:   YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
  ایکس:     X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET

اجرا: python3 social.py [--card-only] [--video-only]
"""
import base64, hashlib, hmac, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, uuid

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "assets", "fonts")
LOGO = os.path.join(HERE, "site", "logo.jpg")
AUDIO = os.environ.get("AUDIO", os.path.join(HERE, "_site", "latest.mp3"))
BULLETIN = os.environ.get("BULLETIN", os.path.join(HERE, "bulletin", "latest.json"))
OUT = os.environ.get("SOCIAL_DIR", os.path.join(HERE, "_social"))
GRAPH = "https://graph.facebook.com/" + os.environ.get("META_API_VERSION", "v23.0")
CHANNEL = "t.me/IranaMediaNews"
APP = "iranamedia.github.io"
TAGS = "#ایران #رسانه_ایرانا #آزادی_ایران"

W, H = 1080, 1920
NIGHT, LAPIS, LAPIS2 = (10, 21, 48), (18, 36, 90), (26, 49, 114)
GOLD, GOLD_DEEP, IVORY, MIST = (224, 180, 82), (169, 125, 34), (245, 236, 214), (188, 198, 223)
WAVE = (110, 1570, 860, 170)          # x, y, پهنا، بلندی موج صدا (عمودی)
WIDE = (1920, 1080)                   # ویدیوی افقی برای یوتیوب: همه‌ی پنجره را می‌پوشاند
WAVE_W = (260, 892, 1400, 96)         # موج صدا در ویدیوی افقی

SECRETS = [os.environ.get(k, "") for k in ("META_PAGE_TOKEN", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN",
                                            "X_API_SECRET", "X_ACCESS_SECRET", "X_ACCESS_TOKEN")]


def clean(msg):
    msg = str(msg)
    for s in SECRETS:
        if s: msg = msg.replace(s, "***")
    return msg


# ---------- ویدیو ----------

def font(weight, size):
    for name in (f"Vazirmatn-{weight}.ttf", "Vazirmatn-Bold.ttf"):
        p = os.path.join(FONTS, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
    return ImageFont.truetype("DejaVuSans-Bold.ttf", size, layout_engine=ImageFont.Layout.RAQM)


def rtl(d, xy_right, y, text, f, fill, anchor="ra"):
    d.text((xy_right, y), text, font=f, fill=fill, anchor=anchor, direction="rtl", language="fa")


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f, direction="rtl", language="fa") <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def background(W=W, H=H):
    img = Image.new("RGB", (W, H), NIGHT)
    px = img.load()
    cx, cy = W / 2, -H * 0.08
    for y in range(H):
        for x in range(0, W, 2):
            r = min(1.0, (((x - cx) / (W * 1.1)) ** 2 + ((y - cy) / (H * 0.75)) ** 2) ** 0.5)
            if r < 0.4:   a, b, t = LAPIS2, LAPIS, r / 0.4
            else:         a, b, t = LAPIS, NIGHT, (r - 0.4) / 0.6
            c = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
            px[x, y] = c
            if x + 1 < W: px[x + 1, y] = c
    d = ImageDraw.Draw(img, "RGBA")
    # نقش گره‌ی کم‌رنگ
    for gy in range(0, H, 96):
        for gx in range(0, W, 96):
            c = (gx + 48, gy + 48)
            d.polygon([(c[0], c[1] - 34), (c[0] + 11, c[1] - 11), (c[0] + 34, c[1]), (c[0] + 11, c[1] + 11),
                       (c[0], c[1] + 34), (c[0] - 11, c[1] + 11), (c[0] - 34, c[1]), (c[0] - 11, c[1] - 11)],
                      outline=GOLD + (16,))
    d.rectangle([24, 24, W - 25, H - 25], outline=GOLD + (90,), width=2)
    return img


def card(b, path):
    img = background()
    d = ImageDraw.Draw(img, "RGBA")
    # نشان
    logo = Image.open(LOGO).convert("RGB")
    logo = ImageOps.fit(logo, (300, 300))
    mask = Image.new("L", (300, 300), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 299, 299], 64, fill=255)
    lx, ly = (W - 300) // 2, 110
    d.rounded_rectangle([lx - 12, ly - 12, lx + 311, ly + 311], 74, outline=GOLD, width=5)
    img.paste(logo, (lx, ly), mask)
    # نام
    y = ly + 300 + 40
    d.text((W // 2, y), "رسانه ایرانا", font=font("Black", 120), fill=GOLD, anchor="ma", direction="rtl", language="fa")
    y += 190
    d.text((W // 2, y), "I R A N A M E D I A", font=font("Medium", 34), fill=MIST, anchor="ma")
    y += 70
    d.line([(160, y), (W // 2 - 30, y)], fill=GOLD + (200,), width=2)
    d.line([(W // 2 + 30, y), (W - 160, y)], fill=GOLD + (200,), width=2)
    d.polygon([(W // 2, y - 14), (W // 2 + 14, y), (W // 2, y + 14), (W // 2 - 14, y)], fill=GOLD)
    y += 50
    # ساعت و تاریخ
    fs = font("Bold", 42)
    stamp = b["stamp"]
    sw = d.textlength(stamp, font=fs, direction="rtl", language="fa")
    if sw > W - 220:
        fs = font("Bold", 36); sw = d.textlength(stamp, font=fs, direction="rtl", language="fa")
    px0, px1 = (W - sw) / 2 - 56, (W + sw) / 2 + 36
    d.rounded_rectangle([px0, y, px1, y + 84], 42, fill=NIGHT + (200,), outline=GOLD + (120,), width=2)
    d.ellipse([px1 - 40, y + 33, px1 - 22, y + 51], fill=(226, 72, 61))
    d.text(((px0 + px1 - 40) / 2 + 4, y + 42), stamp, font=fs, fill=GOLD, anchor="mm", direction="rtl", language="fa")
    y += 140
    # تیترها (میانه‌چین، با حاشیه‌ی برابر دو سو)
    d.text((W // 2, y), "تیترهای مهم", font=font("Black", 40), fill=GOLD, anchor="ma", direction="rtl", language="fa")
    y += 80
    limit = WAVE[1] - 60
    for size in (52, 48, 44, 40, 36):             # بزرگ‌ترین اندازه‌ای که هر سه تیتر کامل جا شوند
        fh, lh = font("Bold", size), int(size * 1.55)
        blocks = [wrap(d, it["title"], fh, W - 200) for it in b["items"][:3]]
        if y + sum(len(bl) * lh + 50 for bl in blocks) <= limit: break
    for n, bl in enumerate(blocks):
        if y + lh > limit: break
        for ln in bl:
            if y + lh > limit: break
            d.text((W // 2, y), ln, font=fh, fill=IVORY, anchor="ma", direction="rtl", language="fa")
            y += lh
        if n < len(blocks) - 1:
            cy = y + 20
            d.polygon([(W // 2, cy - 9), (W // 2 + 9, cy), (W // 2, cy + 9), (W // 2 - 9, cy)], fill=GOLD)
        y += 50
    # پایین
    d.rounded_rectangle([WAVE[0] - 20, WAVE[1] - 20, WAVE[0] + WAVE[2] + 20, WAVE[1] + WAVE[3] + 20], 28,
                        fill=NIGHT + (150,), outline=GOLD + (60,), width=2)
    d.text((W // 2, H - 120), f"{CHANNEL}   ·   {APP}", font=font("Medium", 34), fill=MIST, anchor="ma")
    img.save(path)
    return path


def card_wide(b, path):
    """کارت افقی ۱۹۲۰×۱۰۸۰: همه‌ی تصویر پوشیده و نوشته‌ها میانه‌چین."""
    w, h = WIDE
    img = background(w, h)
    d = ImageDraw.Draw(img, "RGBA")
    ls = 190
    logo = ImageOps.fit(Image.open(LOGO).convert("RGB"), (ls, ls))
    mask = Image.new("L", (ls, ls), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ls - 1, ls - 1], 46, fill=255)
    lx, ly = (w - ls) // 2, 36
    d.rounded_rectangle([lx - 10, ly - 10, lx + ls + 9, ly + ls + 9], 54, outline=GOLD, width=4)
    img.paste(logo, (lx, ly), mask)
    y = ly + ls + 22
    d.text((w // 2, y), "رسانه ایرانا", font=font("Black", 92), fill=GOLD, anchor="ma", direction="rtl", language="fa")
    y += 130
    fs = font("Bold", 38)
    stamp = b["stamp"]
    sw = d.textlength(stamp, font=fs, direction="rtl", language="fa")
    px0, px1 = (w - sw) / 2 - 56, (w + sw) / 2 + 36
    d.rounded_rectangle([px0, y, px1, y + 66], 33, fill=NIGHT + (200,), outline=GOLD + (120,), width=2)
    d.ellipse([px1 - 38, y + 24, px1 - 22, y + 40], fill=(226, 72, 61))
    d.text(((px0 + px1 - 40) / 2 + 4, y + 34), stamp, font=fs, fill=GOLD, anchor="mm", direction="rtl", language="fa")
    y += 66 + 26
    limit = WAVE_W[1] - 28
    for size in (60, 56, 52, 48, 44, 40, 36):
        fh, lh = font("Bold", size), int(size * 1.5)
        blocks = [wrap(d, it["title"], fh, w - 320) for it in b["items"][:3]]
        if y + sum(len(bl) * lh + 28 for bl in blocks) <= limit: break
    for n, bl in enumerate(blocks):
        if y + lh > limit: break
        for ln in bl:
            if y + lh > limit: break
            d.text((w // 2, y), ln, font=fh, fill=IVORY, anchor="ma", direction="rtl", language="fa")
            y += lh
        y += 28
    x0, y0, ww, hh = WAVE_W
    d.rounded_rectangle([x0 - 20, y0 - 14, x0 + ww + 20, y0 + hh + 14], 26, fill=NIGHT + (150,), outline=GOLD + (60,), width=2)
    d.text((w // 2, h - 82), f"{CHANNEL}   ·   {APP}", font=font("Medium", 28), fill=MIST, anchor="ma")
    img.save(path)
    return path


def video(cardpng, audio, out, wave=WAVE):
    x, y, w, h = wave
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", "24", "-i", cardpng, "-i", audio,
        "-filter_complex",
        f"[1:a]aformat=channel_layouts=mono,showwaves=s={w}x{h}:mode=cline:rate=24:scale=sqrt:colors=#e0b452ff:draw=full,format=rgba[wv];"
        f"[0:v][wv]overlay={x}:{y}:shortest=1:format=rgb,format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "30", "-r", "24", "-g", "48",
        "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", out], check=True)
    return out


# ---------- متن پست‌ها ----------

def caption(b, limit=2000, tags=True):
    head = f"🎙 رسانه ایرانا\n{b['stamp']}\n\n"
    tail = f"\n\n🔊 تلگرام: {CHANNEL}\n📱 اپ: {APP}" + (f"\n\n{TAGS}" if tags else "")
    lines, size = [], len(head) + len(tail)
    for it in b["items"]:
        l = "▪️ " + it["title"]
        if size + len(l) + 1 > limit: break
        lines.append(l); size += len(l) + 1
    return head + "\n".join(lines) + tail


def x_text(b):
    t = f"🎙 رسانه ایرانا\n{b['stamp']}\n"
    for it in b["items"][:3]:
        l = "\n▪️ " + it["title"]
        if len(t) + len(l) > 272: break
        t += l
    return t


# ---------- HTTP ----------

def http(method, url, data=None, headers=None, timeout=600):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, dict(r.headers), body
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url.split('?')[0]} → {e.code} {e.read()[:500]!r}")


def jcall(method, url, params=None, data=None, headers=None):
    if params: url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    _, _, body = http(method, url, data, headers)
    return json.loads(body or b"{}")


def multipart(fields, files):
    bd = uuid.uuid4().hex
    out = b""
    for k, v in fields.items():
        out += f"--{bd}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for k, (name, data, ctype) in files.items():
        out += (f"--{bd}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode() + data + b"\r\n"
    out += f"--{bd}--\r\n".encode()
    return out, f"multipart/form-data; boundary={bd}"


# ---------- فیسبوک ----------

def facebook(b, mp4):
    page, tok = os.environ.get("META_PAGE_ID"), os.environ.get("META_PAGE_TOKEN")
    if not (page and tok): return "skip"
    data, ctype = multipart({"access_token": tok, "title": f"رسانه ایرانا · {b['stamp']}",
                             "description": caption(b)},
                            {"source": ("irana.mp4", open(mp4, "rb").read(), "video/mp4")})
    r = jcall("POST", f"{GRAPH.replace('graph.', 'graph-video.')}/{page}/videos", data=data,
              headers={"Content-Type": ctype})
    return f"video {r.get('id')}"


# ---------- اینستاگرام (ریلز، بارگذاری مستقیم) ----------

def instagram(b, mp4):
    ig, tok = os.environ.get("IG_USER_ID"), os.environ.get("META_PAGE_TOKEN")
    if not (ig and tok): return "skip"
    c = jcall("POST", f"{GRAPH}/{ig}/media", params={
        "media_type": "REELS", "upload_type": "resumable", "share_to_feed": "true",
        "caption": caption(b, 2000), "access_token": tok})
    cid, uri = c["id"], c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH.rsplit('/', 1)[1]}/{c['id']}"
    data = open(mp4, "rb").read()
    http("POST", uri, data, {"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(data))})
    for _ in range(90):                               # تا ۱۵ دقیقه برای پردازش
        s = jcall("GET", f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": tok})
        if s.get("status_code") == "FINISHED": break
        if s.get("status_code") in ("ERROR", "EXPIRED"): raise RuntimeError(f"Instagram processing: {s}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram processing timed out")
    r = jcall("POST", f"{GRAPH}/{ig}/media_publish", params={"creation_id": cid, "access_token": tok})
    return f"reel {r.get('id')}"


# ---------- یوتیوب ----------

def youtube(b, mp4):
    cid, sec, ref = (os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and sec and ref): return "skip"
    tok = jcall("POST", "https://oauth2.googleapis.com/token", data=urllib.parse.urlencode({
        "client_id": cid, "client_secret": sec, "refresh_token": ref, "grant_type": "refresh_token"}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})["access_token"]
    SECRETS.append(tok)
    size = os.path.getsize(mp4)
    meta = {"snippet": {"title": f"رسانه ایرانا | {b['stamp']}"[:100],
                        "description": caption(b, 4500).replace("<", "‹").replace(">", "›"),
                        "categoryId": "25", "defaultLanguage": "fa", "defaultAudioLanguage": "fa",
                        "tags": ["ایران", "رسانه ایرانا", "Iranamedia", "خبر"]},
            "status": {"privacyStatus": os.environ.get("YT_PRIVACY", "public"), "selfDeclaredMadeForKids": False}}
    _, hdr, _ = http("POST", "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                     json.dumps(meta).encode(),
                     {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                      "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    loc = hdr.get("Location") or hdr.get("location")
    _, _, body = http("PUT", loc, open(mp4, "rb").read(), {"Content-Type": "video/mp4"})
    return f"video {json.loads(body).get('id')}"


# ---------- ایکس (OAuth 1.0a) ----------

def _q(s): return urllib.parse.quote(str(s), safe="~")


def x_auth(method, url, query=None):
    ck, cs, at, ts = (os.environ[k] for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))
    o = {"oauth_consumer_key": ck, "oauth_nonce": uuid.uuid4().hex, "oauth_signature_method": "HMAC-SHA1",
         "oauth_timestamp": str(int(time.time())), "oauth_token": at, "oauth_version": "1.0"}
    allp = {**o, **(query or {})}
    base = "&".join([method.upper(), _q(url), _q("&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(allp.items())))])
    o["oauth_signature"] = base64.b64encode(hmac.new(f"{_q(cs)}&{_q(ts)}".encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(o.items()))


def x_call(method, url, query=None, body=None, ctype="application/json"):
    full = url + ("?" + urllib.parse.urlencode(query) if query else "")
    hdr = {"Authorization": x_auth(method, url, query)}
    if body is not None: hdr["Content-Type"] = ctype
    _, _, out = http(method, full, body, hdr)
    return json.loads(out or b"{}")


def x_upload(mp4):
    API = "https://api.x.com/2/media/upload"
    data = open(mp4, "rb").read()
    init = x_call("POST", f"{API}/initialize", body=json.dumps(
        {"media_type": "video/mp4", "total_bytes": len(data), "media_category": "tweet_video"}).encode())
    mid = init["data"]["id"]
    for i in range(0, len(data), 4 * 1024 * 1024):
        body, ctype = multipart({"segment_index": i // (4 * 1024 * 1024)},
                                {"media": ("irana.mp4", data[i:i + 4 * 1024 * 1024], "application/octet-stream")})
        x_call("POST", f"{API}/{mid}/append", body=body, ctype=ctype)
    info = x_call("POST", f"{API}/{mid}/finalize").get("data", {}).get("processing_info")
    while info and info.get("state") in ("pending", "in_progress"):
        time.sleep(max(2, info.get("check_after_secs", 5)))
        info = x_call("GET", API, query={"command": "STATUS", "media_id": mid}).get("data", {}).get("processing_info")
    if info and info.get("state") == "failed": raise RuntimeError(f"X media: {info}")
    return mid


def x_post(b, mp4, clip):
    if not all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")):
        return "skip"
    text, errs = x_text(b), []
    for media in (mp4, clip, None):                   # ویدیوی کامل، سپس برش کوتاه، سپس تنها متن
        try:
            payload = {"text": text}
            if media: payload["media"] = {"media_ids": [x_upload(media)]}
            r = x_call("POST", "https://api.x.com/2/tweets", body=json.dumps(payload).encode())
            return f"post {r.get('data', {}).get('id')}" + ("" if media == mp4 else " (fallback)") + \
                   (f" [earlier: {'; '.join(errs)}]" if errs else "")
        except Exception as e:
            errs.append(clean(e)[:200])
    raise RuntimeError("; ".join(errs))


# ---------- اجرا ----------

def main():
    b = json.load(open(BULLETIN, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    png = card(b, os.path.join(OUT, "card.png"))
    wide_png = card_wide(b, os.path.join(OUT, "card-wide.png"))
    if "--card-only" in sys.argv: print(png, wide_png); return
    mp4 = video(png, AUDIO, os.path.join(OUT, "irana.mp4"))
    mp4w = video(wide_png, AUDIO, os.path.join(OUT, "irana-wide.mp4"), WAVE_W)   # یوتیوب: افقی، تمام‌صفحه
    clip = os.path.join(OUT, "irana-clip.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-t", "139", "-c", "copy", clip], check=True)
    print("video", os.path.getsize(mp4) // 1024, "KB")
    if "--video-only" in sys.argv: return
    failed = []
    for name, fn in (("Facebook", lambda: facebook(b, mp4)), ("Instagram", lambda: instagram(b, mp4)),
                     ("YouTube", lambda: youtube(b, mp4w)), ("X", lambda: x_post(b, mp4, clip))):
        try:
            print(f"{name}: {fn()}", flush=True)
        except Exception as e:
            msg = clean(e).replace("\n", " ")[:900]
            print(f"::error title={name}::{msg}", flush=True)
            failed.append(name)
    if failed: sys.exit(1)


if __name__ == "__main__":
    main()
