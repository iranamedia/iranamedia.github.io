"""تلگرام رسمی شهریار ایران (t.me/s/OfficialRezaPahlavi) را می‌خواند و واپسین پیام‌ها را
در bulletin/prince_telegram.json می‌نویسد تا نویسنده‌ی خبرنامه همواره آن‌ها را ببیند.
(نویسنده خود به t.me نمی‌رسد؛ رایانه‌های GitHub می‌رسند.)
اجرا: python3 tools/prince_tg.py bulletin/prince_telegram.json"""
import html, json, re, sys, urllib.request

URL = "https://t.me/s/OfficialRezaPahlavi"
KEEP = 12


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (IranaMedia bulletin bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def text_of(fragment):
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return html.unescape(fragment).strip()


def posts(page):
    out = []
    for block in re.split(r'(?=<div class="tgme_widget_message_wrap)', page)[1:]:
        m = re.search(r'data-post="OfficialRezaPahlavi/(\d+)"', block)
        if not m:
            continue
        t = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_footer|<div class="tgme_widget_message_reply|$)', block, re.S)
        if not t:
            t = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        when = re.search(r'<time datetime="([^"]+)"', block)
        out.append({
            "id": int(m.group(1)),
            "url": f"https://t.me/OfficialRezaPahlavi/{m.group(1)}",
            "time": when.group(1) if when else "",
            "video": "tgme_widget_message_video" in block,
            "photo": "tgme_widget_message_photo" in block,
            "text": text_of(t.group(1)) if t else "",
        })
    return out


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "bulletin/prince_telegram.json"
    items = posts(fetch(URL))
    if not items:
        sys.exit("هیچ پیامی خوانده نشد")
    items = sorted(items, key=lambda p: p["id"], reverse=True)[:KEEP]
    json.dump({"source": URL, "posts": items}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("واپسین پیام:", items[0]["id"], items[0]["time"], items[0]["text"][:120].replace("\n", " "))
