"""کانال‌های تلگرامی رویدادها (هه‌نگاو، کُردپا، ۱۵۰۰ تصویر، هرانا) را هر ساعت می‌خواند و پست‌های دارای عکس یا ویدیو
از ۳۶ ساعت گذشته را (تنها نشانی و نوشته، نه خود عکس) در bulletin/events.json می‌گذارد.
سیما هنگام ساختن سرنما، اگر پستی با خبر نخست بخواند، عکس آن را می‌گیرد و چهره‌ها را تار می‌کند (tools/event_photo.py).
اجرا: python3 tools/event_tg.py bulletin/events.json"""
import datetime, html, json, re, sys, urllib.request

CHANNELS = {                                          # نام کانال در تلگرام ← نامی که در یادکرد عکس می‌آید
    "Hengaw_Org": "هه‌نگاو",
    "kurdpaagency": "کُردپا",
    "Tasvir_1500": "۱۵۰۰ تصویر",
    "hranews": "هرانا",
}
KEEP_H = 36


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (IranaMedia bulletin bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def text_of(fragment):
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def posts(ch, page):
    out = []
    for block in re.split(r'(?=<div class="tgme_widget_message_wrap)', page)[1:]:
        m = re.search(r'data-post="[^/"]+/(\d+)"', block)
        img = re.search(r'class="tgme_widget_message_(?:photo_wrap|video_thumb)[^"]*"[^>]*background-image:url\(\'([^\']+)\'\)', block)
        if not (m and img):
            continue
        t = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        when = re.search(r'<time datetime="([^"]+)"', block)
        out.append({"channel": ch, "source": CHANNELS[ch], "id": int(m.group(1)),
                    "url": f"https://t.me/{ch}/{m.group(1)}", "time": when.group(1) if when else "",
                    "img": img.group(1), "text": (text_of(t.group(1)) if t else "")[:700]})
    return out


def fresh(p):
    try:
        t = datetime.datetime.fromisoformat(p["time"].replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() < KEEP_H * 3600
    except Exception:
        return False


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "bulletin/events.json"
    try:
        old = json.load(open(path, encoding="utf-8")).get("posts", [])
    except Exception:
        old = []
    seen = {(p["channel"], p["id"]): p for p in old if fresh(p)}
    for ch in CHANNELS:
        try:
            got = posts(ch, fetch(f"https://t.me/s/{ch}"))
        except Exception as e:
            print(ch, "خوانده نشد:", e)
            continue
        got = [p for p in got if fresh(p)]
        for p in got:
            seen[(ch, p["id"])] = p
        print(ch, ":", len(got), "پست تازه‌ی دارای عکس")
    items = sorted(seen.values(), key=lambda p: p["time"], reverse=True)
    json.dump({"note": "نشانی عکس‌های رویداد؛ چهره‌ها هنگام کاربرد تار می‌شوند", "posts": items},
              open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
