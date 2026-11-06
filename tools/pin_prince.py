"""رویدادهای شهریار ایران (شاهزاده رضا پهلوی) رویداد نخست است و نخست می‌ماند،
تا جایی که کهنه نشود یا رویداد ارجدار دیگری نباشد.

- خبر شهریار ایران به جای نخست می‌رود.
- اگر خبرنامه خبری از ایشان ندارد، واپسین خبرشان (bulletin/prince.json) نخست می‌ماند،
  مگر آنکه کهنه شده باشد (بیش از PRINCE_MAX_HOURS ساعت، پیش‌فرض ۴۸).
- رویداد ارجدارتر: اگر نویسنده خبری را با "lead": true نشان داده باشد، آن خبر نخست می‌آید
  و خبر شهریار ایران دوم.
اجرا: python3 tools/pin_prince.py bulletin/latest.json bulletin/prince.json"""
import datetime, json, os, re, sys

PRINCE = re.compile(r"شهریار\s*ایران|رضا\s*پهلوی|شاهزاده")
FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
MAX_HOURS = float(os.environ.get("PRINCE_MAX_HOURS", "48"))


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
    mine = [it for it in items if is_prince(it)]
    if not mine and os.path.exists(prince_path):
        saved = json.load(open(prince_path, encoding="utf-8"))
        pinned, src, age = saved.get("item"), saved.get("source"), age_hours(saved)
        if pinned and pinned.get("title") and age <= MAX_HOURS:
            mine = [pinned]
            if src and src.get("url") and all(x.get("url") != src["url"] for x in b.get("sources", [])):
                b.setdefault("sources", []).insert(0, src)
            print(f"خبر شهریار ایران ({age:.0f} ساعت پیش) در جای نخست ماند")
        elif pinned:
            print(f"خبر شهریار ایران کهنه شده ({age:.0f} ساعت)؛ دیگر نخست نمی‌ماند")
    lead = [it for it in items if it.get("lead") and not is_prince(it)][:1]
    rest = [it for it in items if not is_prince(it) and it not in lead]
    m = re.search(r"ساعت\s*(\d+)", b.get("stamp", "").translate(FA))
    cap = 5 if m and int(m.group(1)) in (8, 20) else 10
    b["items"] = (lead + mine + rest)[:cap]
    for it in b["items"]:
        it.pop("lead", None)
    json.dump(b, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("نخستین خبر:", b["items"][0]["title"] if b["items"] else "-")


if __name__ == "__main__":
    main(*sys.argv[1:3])
