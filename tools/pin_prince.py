"""رویدادهای شهریار ایران (شاهزاده رضا پهلوی) رویداد نخست است و نخست می‌ماند،
تا جایی که کهنه نشود یا رویداد ارجدار دیگری نباشد.

- خبر شهریار ایران به جای نخست می‌رود.
- اگر خبرنامه خبری از ایشان ندارد، واپسین خبرشان (bulletin/prince.json) نخست می‌ماند،
  تا "hours" ساعت پس از رویداد: ۱۲ برای رویداد ارجدار، ۶ برای خبر روزانه (ارزیابی نویسنده؛ پیش‌فرض ۱۲).
  پس از آن خبر ایشان دیگر نخست نیست (اگر در خبرنامه بماند، جای دوم یا پایین‌تر).
- رویداد ارجدارتر: اگر نویسنده خبری را با "lead": true نشان داده باشد، آن خبر نخست می‌آید
  و خبر شهریار ایران دوم.
اجرا: python3 tools/pin_prince.py bulletin/latest.json bulletin/prince.json"""
import datetime, json, os, re, sys
VOICED = (8, 20)    # ساعت‌های گفتاری تهران (رادیو و تلویزیون): ۵ خبر

PRINCE = re.compile(r"شهریار\s*ایران|رضا\s*پهلوی|شاهزاده\s*رضا|رضا\s*شاه\s*دوم|رضاشاه\s*دوم")   # شهریار ایران، شاهزاده رضا پهلوی، رضاشاه دوم
FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
DEFAULT_HOURS = 12


def window(saved):
    """چند ساعت خبر شهریار ایران نخست می‌ماند: ۱۲ یا ۶، به ارزیابی رسانه (prince.json → "hours")."""
    try:
        h = float(saved.get("hours", DEFAULT_HOURS))
    except (TypeError, ValueError):
        h = DEFAULT_HOURS
    return 6.0 if h <= 6 else 12.0


def is_prince(it):
    return bool(PRINCE.search(it.get("title", "")))


def age_hours(saved):
    try:
        t = datetime.datetime.fromisoformat(saved["time"].replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600
    except Exception:
        return float("inf")                            # بی‌زمان = کهنه


def main(path, prince_path):
    b = json.load(open(path, encoding="utf-8"))
    items = b.get("items", [])
    saved = json.load(open(prince_path, encoding="utf-8")) if os.path.exists(prince_path) else {}
    old = saved.get("item", {}).get("title")
    m = re.search(r"ساعت\s*(\d+)", b.get("stamp", "").translate(FA))
    tv = bool(m) and int(m.group(1)) % 24 in VOICED
    # هر پیام یا رویداد شهریار ایران دست‌کم در یک برنامه‌ی سیما (۸ یا ۲۰) نخست می‌آید:
    # اگر از رویداد تا این بخش هنوز بخش سیمایی نبوده (کمتر از ۱۲ ساعت؛ ۱۲.۵ با زمان پیش از پخش)، نخست است، حتی پیش از "lead"
    tv_first = tv and bool(old) and not saved.get("stale") and age_hours(saved) <= 12.5
    limit = max(window(saved), 12.5) if tv_first else window(saved)
    expired = None
    if old and not saved.get("stale") and age_hours(saved) > limit:
        # زمان صدر گذشت: خبر می‌تواند بماند، ولی دیگر نخست نیست
        expired = next((it for it in items if it.get("title") == old), None)
        if expired:
            items = [it for it in items if it is not expired]
            print(f"خبر شهریار ایران {age_hours(saved):.0f} ساعت پیش بود (مرز {window(saved):.0f})؛ دیگر نخست نیست:", old)
    if old and saved.get("stale"):
        # "stale": true به خواست رسانه: دیگر در خبرنامه نمی‌آید
        n = len(items)
        items = [it for it in items if it.get("title") != old]
        old_url = (saved.get("source") or {}).get("url")
        if n != len(items):
            b["sources"] = [x for x in b.get("sources", []) if x.get("url") != old_url]
            print("خبر کهنه‌ی شهریار ایران برداشته شد:", old)
        b["items"] = items
    mine = [it for it in items if is_prince(it)]
    if saved.get("pin_until") and saved.get("item", {}).get("title"):
        try:
            until = datetime.datetime.fromisoformat(saved["pin_until"].replace("Z", "+00:00"))
        except ValueError:
            until = None
        if until and datetime.datetime.now(datetime.timezone.utc) < until:
            # رویداد برگزیده‌ی رسانه: تا pin_until در همه‌ی بخش‌ها نخست، حتی پیش از "lead"
            pinned = saved["item"]
            others = [it for it in items if it.get("title") != pinned["title"]]
            src = saved.get("source")
            if src and src.get("url") and all(x.get("url") != src["url"] for x in b.get("sources", [])):
                b.setdefault("sources", []).insert(0, src)
            rank = int(saved.get("pin_rank", 1) or 1)      # ۱: نخست؛ ۲: دوم (پس از مهم‌ترین خبر دیگر)
            m = re.search(r"ساعت\s*(\d+)", b.get("stamp", "").translate(FA))
            cap = 5 if m and int(m.group(1)) % 24 in VOICED else 10
            rest = [it for it in others if is_prince(it)] + [it for it in others if not is_prince(it)]
            if rank >= 2:
                top = ([it for it in others if it.get("lead") and not is_prince(it)] or [it for it in others if not is_prince(it)])[:1]
                rest = [it for it in rest if it not in top]
                b["items"] = (top + [pinned] + rest)[:cap]
            else:
                for it in others:
                    it.pop("lead", None)
                b["items"] = ([pinned] + rest)[:cap]
            json.dump(b, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("رویداد برگزیده تا", saved["pin_until"], "جای", rank, ":", pinned["title"])
            return
    titles = {it.get("title") for it in mine}
    if os.path.exists(prince_path) and saved.get("item", {}).get("title") not in titles:
        # تازه‌ترین رویداد ایشان (prince.json) در خبرنامه نیست: نخست می‌آید؛ خبرهای پیشین ایشان پس از آن
        pinned, src, age = saved.get("item"), saved.get("source"), age_hours(saved)
        if pinned and pinned.get("title") and age <= limit and not saved.get("stale"):
            mine = [pinned] + mine
            if src and src.get("url") and all(x.get("url") != src["url"] for x in b.get("sources", [])):
                b.setdefault("sources", []).insert(0, src)
            print(f"خبر شهریار ایران ({age:.0f} ساعت پیش) در جای نخست ماند")
        elif pinned:
            print(f"خبر شهریار ایران کهنه شده ({age:.0f} ساعت)؛ دیگر نخست نمی‌ماند")
    lead = [it for it in items if it.get("lead") and not is_prince(it)][:1]
    rest = [it for it in items if not is_prince(it) and it not in lead]
    if expired:
        rest.insert(1 if rest else 0, expired)
    cap = 5 if tv else 10
    if tv_first and mine:
        print("نخستین برنامه‌ی سیما پس از رویداد شهریار ایران: نخست")
        b["items"] = (mine + lead + rest)[:cap]
    else:
        b["items"] = (lead + mine + rest)[:cap]
    for it in b["items"]:
        it.pop("lead", None)
    json.dump(b, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("نخستین خبر:", b["items"][0]["title"] if b["items"] else "-")


if __name__ == "__main__":
    main(*sys.argv[1:3])
