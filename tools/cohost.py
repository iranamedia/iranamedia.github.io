"""گوینده‌ی همراه بکتاش در هر بخش گفتاری: یکی در میان فیروزه و شارلوت.
(با دو بخش در شبانروز، ۸ بامداد فیروزه و ۲۰ شارلوت.) فیروزه تنها هنگامی می‌آید که آوای او ساخته شده
(bulletin/voices.json) و عکسش (assets/presenter_firoozeh.jpg) باشد؛ وگرنه شارلوت."""
import datetime, json, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES = os.path.join(HERE, "bulletin", "voices.json")
MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
HOURS = sorted(int(x) % 24 for x in os.environ.get("VOICE_HOURS", "8,20").split(",") if x.strip())
ROTA = ["firoozeh", "charlotte"]


def slot(stamp):
    s = (stamp or "").translate(DIG)
    h = re.search(r"ساعت\s*(\d+)", s)
    d = re.search(r"(\d+)\s*(" + "|".join(MONTHS) + r")\s*(?:ماه\s*)?(?:سال\s*)?(\d{4})", s)
    if not (h and d):
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=3, minutes=30)
        return now.toordinal() * len(HOURS) + sum(1 for x in HOURS if x <= now.hour) - 1
    hour, day, m, year = int(h.group(1)) % 24, int(d.group(1)), MONTHS.index(d.group(2)) + 1, int(d.group(3))
    doy = (m - 1) * 31 + day if m <= 6 else 186 + (m - 7) * 30 + day
    return (year * 366 + doy) * len(HOURS) + max(0, sum(1 for x in HOURS if x <= hour) - 1)


def voice_id(name):
    try:
        return json.load(open(VOICES, encoding="utf-8")).get(name, "")
    except Exception:
        return ""


def current(b=None):
    if b is None:
        try:
            b = json.load(open(os.path.join(HERE, "bulletin", "latest.json"), encoding="utf-8"))
        except Exception:
            b = {}
    name = ROTA[slot(b.get("stamp", "")) % len(ROTA)]
    if name == "firoozeh" and not (voice_id("firoozeh") and os.path.exists(os.path.join(HERE, "assets", "presenter_firoozeh.jpg"))):
        name = "charlotte"
    return name


def asset(voice, b=None):
    """نام عکس‌ها و نقاب‌های گوینده در assets: «woman» (شارلوت) یا «firoozeh»."""
    return "firoozeh" if voice == "woman" and current(b) == "firoozeh" else voice


if __name__ == "__main__":
    for st in ("ساعت ۸ به وقت تهران، جمعه ۶ آذر سال ۲۵۸۵", "ساعت ۲۰ به وقت تهران، جمعه ۶ آذر سال ۲۵۸۵",
               "ساعت ۸ به وقت تهران، شنبه ۷ آذر سال ۲۵۸۵", "ساعت ۲۰ به وقت تهران، شنبه ۷ آذر سال ۲۵۸۵"):
        print(st, "→", ROTA[slot(st) % 2])
    print("اکنون:", current())
