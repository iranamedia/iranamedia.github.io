"""پیام‌ها و رویدادهای شهریار ایران از تلگرام، اِکس و اینستاگرام ایشان را می‌خواند و در
bulletin/prince_feeds.json می‌نویسد تا نویسنده‌ی خبرنامه همواره آن‌ها را ببیند.
(نویسنده خود به این‌ها نمی‌رسد؛ رایانه‌های GitHub می‌رسند.) هر منبعی که در دسترس نباشد،
بی آنکه دیگران را بایستاند، کنار گذاشته و در "errors" نوشته می‌شود.

- تلگرام: t.me/s/OfficialRezaPahlavi
- اینستاگرام: Business Discovery در Graph API، با کلید صفحه‌ی ایرانا (META_PAGE_TOKEN، IG_USER_ID)
- اِکس: X API با کلیدهای X_* اگر باشند؛ وگرنه نمای همگانی syndication
اجرا: python3 tools/prince_feeds.py bulletin/prince_feeds.json"""
import json, os, re, sys, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from prince_tg import posts as tg_posts, fetch  # noqa: E402

KEEP = 10
X_USER = "PahlaviReza"
IG_USERS = [u for u in os.environ.get("PRINCE_IG", "officialrezapahlavi").split(",") if u]
UA = {"User-Agent": "Mozilla/5.0 (IranaMedia bulletin bot)"}


def get_json(url, headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(headers or {})}), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        body = re.sub(r"access_token=[^&\s\"]+", "access_token=***", body)
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from None


def telegram():
    out = []
    for p in tg_posts(fetch("https://t.me/s/OfficialRezaPahlavi")):
        out.append({"platform": "telegram", **p})
    return out


def instagram():
    ig, tok = os.environ.get("IG_USER_ID"), os.environ.get("META_PAGE_TOKEN")
    if not (ig and tok):
        raise RuntimeError("IG_USER_ID یا META_PAGE_TOKEN نیست")
    ver = os.environ.get("META_API_VERSION", "v23.0")
    last = None
    for user in IG_USERS:
        fields = f"business_discovery.username({user}){{username,media.limit({KEEP}){{caption,timestamp,permalink,media_type}}}}"
        url = f"https://graph.facebook.com/{ver}/{ig}?" + urllib.parse.urlencode({"fields": fields, "access_token": tok})
        try:
            d = get_json(url)["business_discovery"]
        except Exception as e:
            last = f"{user}: {e}"
            print("  اینستاگرام", last[:300])
            continue
        return [{"platform": "instagram", "account": d.get("username"), "url": m.get("permalink"),
                 "time": m.get("timestamp", ""), "video": m.get("media_type") in ("VIDEO", "REELS"),
                 "text": (m.get("caption") or "").strip()} for m in d.get("media", {}).get("data", [])]
    raise RuntimeError(f"اینستاگرام: {str(last)[:200]}")


def x_api():
    import social                                    # امضای OAuth1 همان که برای فرستادن به اِکس به کار می‌رود
    u = social.x_call("GET", f"https://api.x.com/2/users/by/username/{X_USER}")
    uid = u["data"]["id"]
    t = social.x_call("GET", f"https://api.x.com/2/users/{uid}/tweets",
                      {"max_results": str(KEEP), "tweet.fields": "created_at,note_tweet", "exclude": "replies"})
    return [{"platform": "x", "url": f"https://x.com/{X_USER}/status/{w['id']}", "time": w.get("created_at", ""),
             "text": (w.get("note_tweet") or {}).get("text") or w.get("text", "")} for w in t.get("data", [])]


def x_public():
    page = fetch(f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{X_USER}")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S)
    if not m:
        raise RuntimeError("اِکس: نمای همگانی پاسخ نداد")
    entries = json.loads(m.group(1))["props"]["pageProps"]["timeline"]["entries"]
    out = []
    for e in entries:
        w = (e.get("content") or {}).get("tweet") or {}
        if not w or w.get("in_reply_to_status_id_str"):
            continue
        out.append({"platform": "x", "url": f"https://x.com/{X_USER}/status/{w.get('id_str')}",
                    "time": w.get("created_at", ""), "text": w.get("full_text") or w.get("text", "")})
    return out[:KEEP]


def x_rss():
    """آینه‌های همگانی اِکس (nitter و مانند آن) که RSS می‌دهند؛ نخستینی که پاسخ دهد."""
    import html as H
    last = None
    for base in os.environ.get("X_MIRRORS", "https://nitter.net,https://xcancel.com,https://nitter.poast.org,https://nitter.privacydev.net").split(","):
        try:
            page = fetch(f"{base}/{X_USER}/rss")
        except Exception as e:
            last = f"{base}: {e}"
            continue
        out = []
        for it in re.findall(r"<item>(.*?)</item>", page, re.S):
            title = re.search(r"<title>(.*?)</title>", it, re.S)
            desc = re.search(r"<description>(.*?)</description>", it, re.S)
            link = re.search(r"<link>(.*?)</link>", it, re.S)
            date = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
            text = H.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", (desc or title).group(1)))
            text = re.sub(r"<[^>]+>", " ", H.unescape(text)).strip()
            if text.startswith("RT by") or text.startswith("R to"):
                continue
            sid = re.search(r"/status/(\d+)", link.group(1) if link else "")
            out.append({"platform": "x", "url": f"https://x.com/{X_USER}/status/{sid.group(1)}" if sid else "",
                        "time": date.group(1).strip() if date else "", "text": text})
        if out:
            return out[:KEEP]
        last = f"{base}: خالی"
    raise RuntimeError(f"آینه‌های اِکس: {last}")


def x():
    if all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")):
        try:
            return x_api()
        except Exception as e:
            print("X API:", str(e)[:200])
    try:
        return x_public()
    except Exception as e:
        print("  اِکس (syndication):", str(e)[:200])
    return x_rss()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "bulletin", "prince_feeds.json")
    out, errors = {}, {}
    for name, fn in (("telegram", telegram), ("x", x), ("instagram", instagram)):
        try:
            got = fn()[:KEEP] if name != "telegram" else sorted(fn(), key=lambda p: p["id"], reverse=True)[:KEEP + 2]
            out[name] = got
            print(f"{name}: {len(got)} پیام؛ واپسین:", (got[0]["time"], got[0]["text"][:80].replace("\n", " ")) if got else "-")
        except Exception as e:
            errors[name] = str(e)[:300]
            print(f"{name}: در دسترس نیست —", errors[name])
    if not out:
        sys.exit("هیچ منبعی خوانده نشد")
    old = {}
    if os.path.exists(path):                          # منبعی که این بار نرسید، داده‌ی پیشینش می‌ماند
        try:
            old = json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    for k in errors:
        if old.get(k):
            out[k] = old[k]
    out["errors"] = errors
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
