"""رویدادهای شهریار ایران (شاهزاده رضا پهلوی) همیشه نخست می‌آید و نخست می‌ماند.

- اگر خبرنامه خبری از شهریار ایران دارد، آن خبر به جای نخست می‌رود.
- اگر ندارد، واپسین خبر شهریار ایران (bulletin/prince.json) در جای نخست می‌نشیند،
  تا خبر تازه‌تری از ایشان جایش را بگیرد.
اجرا: python3 tools/pin_prince.py bulletin/latest.json bulletin/prince.json"""
import json, os, re, sys

PRINCE = re.compile(r"شهریار\s*ایران|رضا\s*پهلوی|شاهزاده")
FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def is_prince(it):
    return bool(PRINCE.search(it.get("title", "")))


def main(path, prince_path):
    b = json.load(open(path, encoding="utf-8"))
    items = b.get("items", [])
    mine = [it for it in items if is_prince(it)]
    rest = [it for it in items if not is_prince(it)]
    if not mine and os.path.exists(prince_path):
        saved = json.load(open(prince_path, encoding="utf-8"))
        pinned, src = saved.get("item"), saved.get("source")
        if pinned and pinned.get("title") and not any(pinned["title"] == it["title"] for it in items):
            mine = [pinned]
            if src and src.get("url") and all(x.get("url") != src["url"] for x in b.get("sources", [])):
                b.setdefault("sources", []).insert(0, src)
            print("خبر شهریار ایران از خبرنامه‌ی پیشین در جای نخست ماند")
    m = re.search(r"ساعت\s*(\d+)", b.get("stamp", "").translate(FA))
    cap = 5 if m and int(m.group(1)) in (8, 20) else 10
    b["items"] = (mine + rest)[:cap]
    json.dump(b, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("نخستین خبر:", b["items"][0]["title"] if b["items"] else "-")


if __name__ == "__main__":
    main(*sys.argv[1:3])
