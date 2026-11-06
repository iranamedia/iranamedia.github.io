"""واژه‌های ایرانا (نام‌های جغرافیایی، نفت و گاز ایران) را در خبرنامه، پیش از رادیو، تلویزیون، تارنما و شبکه‌ها، درست می‌کند (پشتیبانِ tools/rules.md).
اجرا: python3 tools/terms.py bulletin/latest.json"""
import json, re, sys

ZW = "[\\s\u200c\u0650]*"          # فاصله، نیم‌فاصله یا کسره
TERMS = [
    (rf"خلیج{ZW}(?:ی{ZW})?فارس", "آبراه پارس"),
    (rf"دریای{ZW}عرب(?:ی|ستان)?", "دریای پارس"),
    (rf"شط{ZW}(?:ال)?{ZW}عرب", "اروندرود"),
    # نفت و گاز از آنِ ایران است: «نفت جمهوری اسلامی» ← «نفت ایران»
    (rf"(نفت|گاز)((?:{ZW}(?:و|،){ZW}(?:نفت|گاز))?){ZW}جمهوری{ZW}اسلامی(?:{ZW}ایران)?", r"\1\2 ایران"),
]


def fix(text):
    for pat, rep in TERMS:
        text = re.sub(pat, rep, text)
    return text


if __name__ == "__main__":
    path = sys.argv[1]
    b = json.load(open(path, encoding="utf-8"))
    before = json.dumps(b, ensure_ascii=False)
    b["stamp"] = fix(b["stamp"])
    for it in b.get("items", []):
        it["title"], it["body"] = fix(it["title"]), fix(it.get("body", ""))
    for src in b.get("sources", []):
        if "name" in src: src["name"] = fix(src["name"])
    after = json.dumps(b, ensure_ascii=False, indent=1)
    open(path, "w", encoding="utf-8").write(after)
    print("واژه‌ها درست شد" if after.replace("\n", "").replace(" ", "") != before.replace(" ", "") else "واژه‌ها درست بود")
