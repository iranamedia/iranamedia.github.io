"""همه‌ی تاریخ‌های خبرها بر پایه‌ی گاهنامه‌ی ایرانی: ماه‌های ایرانی و سال شاهنشاهی (سال خورشیدی + ۱۱۸۰).

نمونه‌ها:
  «خیزش ژانویه‌ی ۲۰۲۶ میلادی»   → «خیزش دی‌ماه ۲۵۸۴»
  «۲۵ اوت»                      → «۳ شهریور»
  «در ماه اکتبر»                 → «در مهرماه»
  «در ۱۰ روز نخست نوامبر»        → «از ۱۰ تا ۱۹ آبان»
  «در ده ماه نخست ۲۰۲۶»          → «از ۱۱ دی ۲۵۸۴ تا ۹ آبان ۲۵۸۵»
  «سال ۱۹۷۹ میلادی»              → «سال ۲۵۳۸»
  «خرداد ۱۴۰۴»                   → «خرداد ۲۵۸۴»
ماه یا سال میلادیِ بی‌روز به ماه یا سال ایرانی‌ای برگردانده می‌شود که بیشترِ آن را دربر دارد.
نویسنده باید خود تاریخ ایرانی درست را بنویسد؛ این تنها پشتیبان است."""
import datetime
import re

FA = "۰۱۲۳۴۵۶۷۸۹"
JM = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
GM = [  # نام‌های ماه میلادی در فارسی
    r"ژانویه", r"فوریه", r"مارس", r"آوریل", r"(?:ماه\s+)?(?:مه|مِه|مِی)(?=[\s‌]*[\d۰-۹])|ماه\s+(?:مه|می|مِی)|(?<=[\d۰-۹] )(?:مه|مِه|می|مِی)(?![\w\u200c])",
    r"ژوئن", r"ژوئیه|جولای", r"اوت|آگوست", r"سپتامبر", r"اکتبر", r"نوامبر", r"دسامبر"]
WORDS = {"یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10,
         "یازده": 11, "دوازده": 12, "پانزده": 15, "بیست": 20}
D = r"[0-9۰-۹]"
NUM = rf"(?:{D}{{1,2}}|{'|'.join(sorted(WORDS, key=len, reverse=True))})"
YEAR = rf"(?:19|20|۱۹|۲۰){D}{D}"
END = r"(?![\w‌])"
Z = "[\\s‌]*"                                 # فاصله یا نیم‌فاصله
MILADI = rf"(?:{Z}میلادی)?"
GMONTH = "(" + "|".join(f"(?:{g})" for g in GM) + rf")(?:{Z}ی|ِ)?"


def mah(name):
    """«دی» → «دی‌ماه»، «مهر» → «مهرماه»"""
    return name + ("" if name[-1] in "ادذرزژو" else "\u200c") + "ماه"


JB = r"(?<![\w\u200c])"                           # آغاز واژه (نه «آزادی»)


def fa(n):
    return "".join(FA[int(c)] if c.isdigit() else c for c in str(n))


def num(s):
    s = s.strip()
    if s in WORDS:
        return WORDS[s]
    return int("".join(str(FA.index(c)) if c in FA else c for c in s))


GNAMES = [["ژانویه"], ["فوریه"], ["مارس"], ["آوریل"], ["مه", "مِه", "می", "مِی"], ["ژوئن"], ["ژوئیه", "جولای"],
          ["اوت", "آگوست"], ["سپتامبر"], ["اکتبر"], ["نوامبر"], ["دسامبر"]]


def g_month(name):
    name = re.sub(r"^ماه[\s\u200c]+", "", name.strip())
    for i, names in enumerate(GNAMES):
        if name in names:
            return i + 1
    raise ValueError(name)


def to_jalali(gy, gm, gd):
    """گاهشمار میلادی → خورشیدی (روش سنجیده‌ی رایج)."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    jm = 1 + days // 31 if days < 186 else 7 + (days - 186) // 30
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return jy, jm, jd


def shah(jy):
    return jy + 1180


def today():
    return datetime.date.today()


def guess_year(m, d=15):
    """سال یک تاریخ بی‌سال: نزدیک‌ترین، نه بیش از یک ماه در آینده."""
    t = today()
    y = t.year
    try:
        if datetime.date(y, m, min(d, 28)) > t + datetime.timedelta(days=31):
            y -= 1
    except ValueError:
        pass
    return y


def last_day(y, m):
    return (datetime.date(y + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1)).day


def jdate(y, m, d, with_year):
    jy, jm, jd = to_jalali(y, m, d)
    return f"{fa(jd)} {JM[jm - 1]}" + (f" {fa(shah(jy))}" if with_year else "")


def jrange(a, b, with_year):
    """دو تاریخ میلادی → «از … تا …» ایرانی."""
    ja, jb = to_jalali(*a), to_jalali(*b)
    if with_year and ja[0] != jb[0]:
        return f"از {jdate(*a, True)} تا {jdate(*b, True)}"
    y = f" {fa(shah(jb[0]))}" if with_year else ""
    if ja[1] == jb[1]:
        return f"از {fa(ja[2])} تا {fa(jb[2])} {JM[jb[1] - 1]}{y}"
    return f"از {fa(ja[2])} {JM[ja[1] - 1]} تا {fa(jb[2])} {JM[jb[1] - 1]}{y}"


def month_name(gm):
    return JM[to_jalali(2001, gm, 15)[1] - 1]        # ماه ایرانی‌ای که بیشترِ ماه میلادی را دارد


def fix_dates(t):
    # «آبان‌ماه (نوامبر)» ← پرانتز میلادی کنار تاریخ ایرانی بیرون می‌رود
    t = re.sub(rf"{Z}\({Z}{GMONTH}(?:{Z}{YEAR})?{MILADI}{Z}\)", "", t)

    # «در ۱۰ روز نخست نوامبر ۲۰۲۶»
    def first_days(m):
        n, gm = num(m.group(1)), g_month(m.group(2))
        y = num(m.group(3)) if m.group(3) else guess_year(gm)
        return jrange((y, gm, 1), (y, gm, min(n, last_day(y, gm))), bool(m.group(3)))
    t = re.sub(rf"(?:در{Z})?({NUM}){Z}روز{Z}(?:نخست|اول){Z}(?:ماه{Z})?{GMONTH}(?:{Z}({YEAR}))?{MILADI}{END}", first_days, t)

    # «در ده ماه نخست (سال) ۲۰۲۶»
    def first_months(m):
        n, y = num(m.group(1)), num(m.group(2))
        return jrange((y, 1, 1), (y, n, last_day(y, n)), True)
    t = re.sub(rf"(?:در{Z})?({NUM}){Z}ماه{Z}(?:نخست|اول){Z}(?:سال{Z})?({YEAR}){MILADI}{END}", first_months, t)

    # «سه‌ماهه‌ی چهارم سال ۲۰۲۶»
    QN = {"نخست": 1, "اول": 1, "دوم": 2, "سوم": 3, "چهارم": 4}

    def quarter(m):
        q, y = QN[m.group(1)], num(m.group(2))
        return jrange((y, 3 * q - 2, 1), (y, 3 * q, last_day(y, 3 * q)), True)
    t = re.sub(rf"(?:در{Z})?سه{Z}ماهه(?:{Z}ی|ِ)?{Z}(نخست|اول|دوم|سوم|چهارم){Z}(?:سال{Z})?({YEAR}){MILADI}{END}", quarter, t)

    # «در سال ۲۰۲۶» (سال جاری یا پیشین، برای آمار): بازه‌ی درست
    def stat_year(m):
        y, now = num(m.group(1)), today().year
        if y == now:
            return f"از {jdate(y, 1, 1, True)} تاکنون"
        if y == now - 1:
            return jrange((y, 1, 1), (y, 12, 31), True)
        return m.group(0)
    t = re.sub(rf"در{Z}سال{Z}({YEAR}){MILADI}{END}", stat_year, t)

    # «آغاز سال ۲۰۲۶» و «پایان سال ۲۰۲۶»
    t = re.sub(rf"(?:آغاز|ابتدای|اول){Z}سال{Z}({YEAR}){MILADI}{END}", lambda m: jdate(num(m.group(1)), 1, 1, True), t)
    t = re.sub(rf"(?:پایان|انتهای|آخر){Z}سال{Z}({YEAR}){MILADI}{END}", lambda m: jdate(num(m.group(1)), 12, 31, True), t)

    # «آغاز اوت»، «پایان اوت (۲۰۲۶)»
    def edge(m):
        gm = g_month(m.group(2))
        y = num(m.group(3)) if m.group(3) else guess_year(gm)
        d = 1 if m.group(1) in ("آغاز", "ابتدای", "اول") else last_day(y, gm)
        return jdate(y, gm, d, bool(m.group(3)))
    t = re.sub(rf"(آغاز|ابتدای|اول|پایان|انتهای|آخر){Z}(?:ماه{Z})?{GMONTH}(?:{Z}({YEAR}))?{MILADI}{END}", edge, t)

    # «۱۱ و ۱۲ اکتبر (۲۰۲۶)»، «۲۵ اوت»
    def days(m):
        gm = g_month(m.group(4))
        d1 = num(m.group(1))
        y = num(m.group(5)) if m.group(5) else guess_year(gm, d1)
        wy = bool(m.group(5))
        if m.group(3):
            d2 = num(m.group(3))
            a, b = to_jalali(y, gm, d1), to_jalali(y, gm, d2)
            sep = m.group(2)
            if a[1] == b[1]:
                return f"{fa(a[2])}{sep}{fa(b[2])} {JM[b[1] - 1]}" + (f" {fa(shah(b[0]))}" if wy else "")
            return f"{jdate(y, gm, d1, False)}{sep}{jdate(y, gm, d2, wy)}"
        return jdate(y, gm, d1, wy)
    t = re.sub(rf"(?<![\d۰-۹])({D}{{1,2}})(?:({Z}(?:و|تا|-|–){Z})({D}{{1,2}}))?{Z}{GMONTH}(?:{Z}({YEAR}))?{MILADI}{END}", days, t)

    # «ژانویه‌ی ۲۰۲۶ میلادی» ← «دی‌ماه ۲۵۸۴»
    def month_year(m):
        gm, y = g_month(m.group(1)), num(m.group(2))
        jy, jm, _ = to_jalali(y, gm, 15)
        return f"{mah(JM[jm - 1])} {fa(shah(jy))}"
    t = re.sub(rf"(?:ماه{Z})?{GMONTH}{Z}(?:سال{Z})?({YEAR}){MILADI}{END}", month_year, t)

    # «در ماه اکتبر» ← «در مهرماه»
    t = re.sub(rf"(?:ماه{Z})?{GMONTH}{MILADI}{END}", lambda m: mah(month_name(g_month(m.group(1)))), t)

    # «دی‌ماه ۲۰۲۶ میلادی» (ماه ایرانی با سال میلادی)
    def jm_gyear(m):
        jm, y = JM.index(m.group(1)) + 1, num(m.group(2))
        for jy in (y - 622, y - 621):                # کدام سال ایرانی، این ماهش در سال میلادی y است
            for gm in range(1, 13):
                if to_jalali(y, gm, 15)[:2] == (jy, jm):
                    return f"{mah(m.group(1))} {fa(shah(jy))}"
        return m.group(0)
    t = re.sub(rf"{JB}({'|'.join(JM)})(?:{Z}ماه)?{Z}(?:سال{Z})?({YEAR}){MILADI}{END}", jm_gyear, t)

    # سال خورشیدی (۱۴۰۴) ← سال شاهنشاهی (۲۵۸۴)
    SOLAR = rf"(?:13|14|۱۳|۱۴){D}{D}"
    t = re.sub(rf"({JB}(?:{'|'.join(JM)})(?:{Z}ماه)?{Z}(?:سال{Z})?|سال{Z})({SOLAR})(?:{Z}(?:هجری{Z})?(?:خورشیدی|شمسی))?{END}",
               lambda m: m.group(1) + fa(num(m.group(2)) + 1180), t)
    t = re.sub(rf"(?<![\d۰-۹])({SOLAR}){Z}(?:هجری{Z})?(?:خورشیدی|شمسی){END}", lambda m: fa(num(m.group(1)) + 1180), t)

    # سال میلادی تنها: «سال ۱۹۷۹ میلادی»، «از سال ۲۰۲۰» ← سال ایرانی‌ای که بیشترِ آن را دارد
    t = re.sub(rf"(سال{Z})({YEAR}){MILADI}{END}", lambda m: m.group(1) + fa(shah(to_jalali(num(m.group(2)), 7, 1)[0])), t)
    t = re.sub(rf"(?<![\d۰-۹])({YEAR}){Z}میلادی{END}", lambda m: fa(shah(to_jalali(num(m.group(1)), 7, 1)[0])), t)
    return t


if __name__ == "__main__":
    import sys
    for line in sys.stdin:
        print(fix_dates(line.rstrip("\n")))
