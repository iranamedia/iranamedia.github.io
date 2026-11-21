"""ویدیو و عکس‌هایی که رسانه برای ربات تلگرام ایرانا می‌فرستد را برمی‌دارد: آنچه از تلگرام شهریار ایران است
یا در نوشته‌اش نام ایشان آمده، در assets/prince؛ دیگر عکس و ویدیوها «عکس رویداد» هستند و در assets/events
(برای سرنمای خبر نخستی که با نوشته یا نام جای آن بخواند).
تنها از حساب‌های ALLOWED (شناسه‌ی تلگرام) پذیرفته می‌شود؛ پیام دیگران نادیده می‌ماند.
bulletin/bot_inbox.json واپسین شماره‌ی خوانده‌شده و فهرست فایل‌ها را نگه می‌دارد.
نام فایل: <تاریخ>_<شماره>.mp4 — اگر در نوشته‌ی پیام «از ۰:۱۵ تا ۰:۴۵» باشد، در .json کنارش نوشته می‌شود."""
import datetime, hashlib, json, os, re, subprocess, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ["TOKEN"]
STATE = os.path.join(HERE, "bulletin", "bot_inbox.json")
DIR = os.path.join(HERE, "assets", "prince")
EV_DIR = os.path.join(HERE, "assets", "events")
PRINCE = re.compile(r"شهریار\s*ایران|پهلوی|شاهزاده|رضا\s*شاه\s*دوم|رضاشاه\s*دوم|Pahlavi", re.I)


def tag(uid):
    """شناسه‌ی تلگرام فرستنده در مخزن همگانی نوشته نمی‌شود؛ تنها نشانی درهم‌شده (با کلید ربات)."""
    return hashlib.sha256(f"{uid}:{TOKEN}".encode()).hexdigest()[:24]

FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def api(method, **params):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    if not d.get("ok"):
        raise RuntimeError(d)
    return d["result"]


def seconds(s):
    p = [float(x) for x in s.translate(FA).split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0]


state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"offset": 0, "allowed": [], "files": []}
allowed = {a if isinstance(a, str) else tag(a) for a in state.get("allowed", [])}
updates = api("getUpdates", offset=state.get("offset", 0), timeout=0, allowed_updates=json.dumps(["message"]))
os.makedirs(DIR, exist_ok=True)
for u in updates:
    state["offset"] = u["update_id"] + 1
    m = u.get("message") or {}
    who = (m.get("from") or {})
    me = tag(who.get("id"))
    print("پیام", "| ویدیو" if m.get("video") else "", "| عکس" if m.get("photo") else "")
    if not allowed:                                   # نخستین فرستنده (دارنده‌ی رسانه) پذیرفته می‌شود
        allowed = {me}
    if me not in allowed:
        print("از فرستنده‌ی ناشناس؛ نادیده")
        continue
    media = m.get("video") or m.get("animation") or (m.get("document") if (m.get("document") or {}).get("mime_type", "").startswith("video") else None)
    ext = ".mp4"
    if not media and m.get("photo"):
        media, ext = m["photo"][-1], ".jpg"
    if not media:
        continue
    if media.get("file_size", 0) > 20 * 1024 * 1024:
        print("بزرگ‌تر از ۲۰ مگابایت؛ تلگرام به ربات نمی‌دهد. تکه‌ای کوتاه‌تر بفرستید.")
        api("sendMessage", chat_id=m["chat"]["id"], text="این فایل بزرگ‌تر از ۲۰ مگابایت است و ربات نمی‌تواند آن را بگیرد. لطفاً تکه‌ای کوتاه‌تر بفرستید.")
        continue
    f = api("getFile", file_id=media["file_id"])
    day = datetime.datetime.fromtimestamp(m.get("forward_date") or m["date"], datetime.timezone.utc).strftime("%Y-%m-%d")
    name = f"{day}_{m['message_id']}{ext}"
    fwd = m.get("forward_from_chat") or {}
    prince = (fwd.get("username", "").lower() == "officialrezapahlavi") or bool(PRINCE.search(m.get("caption", "") + " " + fwd.get("title", "")))
    where = DIR if prince else EV_DIR
    os.makedirs(where, exist_ok=True)
    urllib.request.urlretrieve(f"https://api.telegram.org/file/bot{TOKEN}/{f['file_path']}", os.path.join(where, name))
    meta = {"file": name, "received": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "caption": m.get("caption", ""), "from_channel": fwd.get("username", "")}
    if not prince:
        meta["kind"], meta["source"] = "event", fwd.get("title", "")
        if ext == ".mp4":                             # از ویدیوی رویداد، یک نما برای سرنما
            still = name[:-4] + ".jpg"
            try:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "2", "-i", os.path.join(where, name), "-frames:v", "1",
                                "-q:v", "3", os.path.join(where, still)], check=True, timeout=60)
                meta["still"] = still
            except Exception as e:
                print("نما گرفته نشد:", e)
    r = re.search(r"([\d۰-۹:.]+)\s*(?:تا|-|–)\s*([\d۰-۹:.]+)", m.get("caption", "") + " " + m.get("text", ""))
    if r:
        meta["start"], meta["end"] = seconds(r.group(1)), seconds(r.group(2))
    state["files"].append(meta)
    print("گرفته شد:", name, media.get("duration", ""), "ثانیه")
    api("sendMessage", chat_id=m["chat"]["id"], text=(f"گرفته شد ✅ {name} — شهریار ایران؛ در نخستین برنامه‌ی سیمای ۸ یا ۲۰ به کار می‌رود." if prince else
        f"گرفته شد ✅ {name} — عکس رویداد؛ تا ۳۶ ساعت، سرنمای خبر نخستی می‌شود که با نوشته‌ی آن بخواند. "
        "اگر از شهریار ایران است، با نوشته‌ی «شهریار ایران» دوباره بفرستید."))
state["allowed"] = sorted(allowed)
json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
