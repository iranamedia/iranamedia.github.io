"""هیچ خبری بیش از ۲۴ ساعت در صدر خبرنامه نمی‌ماند؛ باید به‌روز یا بازنویسی شود.

خبر صدر و زمانی که به صدر آمده در lead.json تارنما نگه داشته می‌شود (https://iranamedia.github.io/lead.json).
اگر همان تیتر بیش از LEAD_MAX_HOURS (پیش‌فرض ۲۴) ساعت در صدر مانده باشد، یک پله پایین می‌رود
و تیترش در فهرست «بازنشسته» می‌ماند تا دوباره به صدر برنگردد. تیتر تازه (بازنویسی با رویداد تازه) دوباره به صدر می‌تواند بیاید.
اجرا: python3 tools/lead_age.py bulletin/latest.json _site/lead.json"""
import datetime, json, os, sys, urllib.request

MAX_HOURS = float(os.environ.get("LEAD_MAX_HOURS", "24"))
URL = os.environ.get("LEAD_URL", "https://iranamedia.github.io/lead.json")
KEEP_RETIRED_HOURS = 96


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def parse(t):
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
    except Exception:
        return None


def previous():
    try:
        with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "IranaMedia/1.0"}), timeout=15) as r:
            return json.load(r)
    except Exception as e:
        print("lead.json پیشین در دسترس نیست:", e)
        return {}


def main(path, out):
    b = json.load(open(path, encoding="utf-8"))
    items = b.get("items", [])
    prev = previous()
    t = now()
    retired = {k: v for k, v in (prev.get("retired") or {}).items()
               if (parse(v) and (t - parse(v)).total_seconds() < KEEP_RETIRED_HOURS * 3600)}
    # خبرهای بازنشسته به صدر برنمی‌گردند
    if items and items[0].get("title") in retired and len(items) > 1:
        k = next((i for i, it in enumerate(items) if it.get("title") not in retired), None)
        if k:
            items.insert(0, items.pop(k))
            print("خبر کهنه به صدر برنگشت:", items[1]["title"])
    if items:
        title = items[0].get("title", "")
        since = parse(prev.get("since", "")) if prev.get("title") == title else None
        since = since or t
        hours = (t - since).total_seconds() / 3600
        if hours > MAX_HOURS and len(items) > 1:
            retired[title] = t.isoformat()
            items.insert(1, items.pop(0))
            print(f"خبر صدر {hours:.0f} ساعت در صدر بود؛ یک پله پایین رفت:", title)
            title, since = items[0].get("title", ""), t
        b["items"] = items
        json.dump(b, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        json.dump({"title": title, "since": since.isoformat(), "retired": retired},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("صدر:", title, "از", since.isoformat())


if __name__ == "__main__":
    main(*sys.argv[1:3])
