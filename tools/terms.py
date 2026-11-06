"""واژه‌های ایرانا (نام‌های جغرافیایی، نفت و گاز ایران) را در خبرنامه، پیش از رادیو، تلویزیون، تارنما و شبکه‌ها، درست می‌کند (پشتیبانِ tools/rules.md).
اجرا: python3 tools/terms.py bulletin/latest.json"""
import json, re, sys

ZW = "[\\s\u200c\u0650]*"          # فاصله، نیم‌فاصله یا کسره
TERMS = [
    (rf"خلیج{ZW}(?:ی{ZW})?فارس", "آبراه پارس"),
    (rf"دریای{ZW}عرب(?:ی|ستان)?", "دریای پارس"),
    (rf"شط{ZW}(?:ال)?{ZW}عرب", "اروندرود"),
    # کشورهای عربی آبراه پارس: تنها نام کشور («دیوان امیری قطر» ← «قطر»)
    (rf"(?:سخنگوی{ZW})?(?:دیوان{ZW}امیری|دربار|امیر|امیرنشین|شیخ‌?{ZW}نشین|سلطان‌?{ZW}نشین|پادشاهی|پادشاه|سلطان|ولیعهد|دولت|حکومت|کابینه"
     rf"|وزارت{ZW}(?:امور{ZW})?خارجه|وزیر{ZW}(?:امور{ZW})?خارجه|نخست‌?{ZW}وزیر)(?:{ZW}ی|{ZW}‌ی)?{ZW}"
     rf"(قطر|عربستان{ZW}سعودی|عربستان|بحرین|عمان|کویت|امارات(?:{ZW}متحده{ZW}عربی)?)(?![\w\u200c])", r"\1"),
    # نفت و گاز از آنِ ایران است: «نفت جمهوری اسلامی» ← «نفت ایران»
    (rf"(نفت|گاز)((?:{ZW}(?:و|،){ZW}(?:نفت|گاز))?){ZW}جمهوری{ZW}اسلامی(?:{ZW}ایران)?", r"\1\2 ایران"),
]


# «جمهوری اسلامی نفت ایران می‌فروشد»: در جمله‌ای که از جمهوری اسلامی سخن می‌گوید،
# نفت یا گازِ فروخته/صادرشده، «نفت ایران» / «گاز ایران» نامیده می‌شود.
OWNERS = "ایران|روسیه|عراق|عربستان|ونزوئلا|آمریکا|قطر|کویت|امارات|لیبی|خام|جهان|جهانی|برنت|وست|دریای|کشور|کشورهای|اوپک|سنگین|سبک|بیشتر|کمتر|خود"
TRADE_BEFORE = rf"(?:فروش|صادرات|صادراتِ|قاچاق|درآمد|درآمدهای|خریداران|خرید|محموله‌ی|محموله‌های|محموله){ZW}"
TRADE_AFTER = rf"{ZW}(?:را{ZW})?(?:می‌فروشد|می‌فروشند|فروخت|فروختند|فروخته|بفروشد|بفروشند|صادر|می‌فروخت)"


def own_trade(sentence):
    if "جمهوری اسلامی" not in sentence:
        return sentence
    sentence = re.sub(rf"({TRADE_BEFORE})(نفت|گاز)(?!{ZW}(?:{OWNERS}))(?![\w‌])", r"\1\2 ایران", sentence)
    sentence = re.sub(rf"(?<![\w‌])(نفت|گاز)(?!{ZW}(?:{OWNERS}))(?=({TRADE_AFTER}))", r"\1 ایران", sentence)
    if re.search(r"فروخت|فروش|صادر|می‌فروش|بفروش", sentence):     # «نفت را به چین فروخت»
        sentence = re.sub(rf"(?<![\w\u200c])(نفت|گاز)(?={ZW}را(?![\w\u200c]))", r"\1 ایران", sentence)
    return sentence


def fix(text):
    for pat, rep in TERMS:
        text = re.sub(pat, rep, text)
    return "".join(own_trade(p) for p in re.split(r"(?<=[.!؟?؛])", text))


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
