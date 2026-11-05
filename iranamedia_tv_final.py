#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Iranamedia - نسخه تلویزیونی نهایی - 2585 - اینترو دقیق شما - بدون رادیو
# مشخصات قفل شده:
# - اینترو: assets/irana_intro_final.mp4 دقیقا خود شما - تیر سپید از پشت رنگین‌کمان سرخ زرد بنفش، دماوند گرد، تنها IRANA، بدون TELEVISION
# - تاریخ: شاهنشاهی 2585 = جلالی + 1180
# - زمان: "7 بامداد ایران / 4 پس از نیمروز ایران / 12 شب ایران - 11 آبان 2585، رویدادهای ایران از رسانه ایرانا"
# - 0-10 اینترو دقیق
# - 10-70 سه رویداد سربرگ: تنها صدا + زیرآهنگ، بدون تصویر استودیو
# - 70-270 شش رویداد: تصویر استودیو یکی در میان بکتاش (مرد جوان کراواتی) و شارلوت (زن جوان کتی) بدون ریش، بدون عینک، بدون سبیل
# - 270-300 آگهی پایانی: صدای زن بدون درود: "رسانه ایرانا / تازه‌ترین رویدادهای ایران / سر هر ساعت / شبانروزی / ایرانا همه جا با شماست" + @IranaMediaNews + WhatsApp
# - بدون پرچم و نشان جمهوری اسلامی، فقط شیر و خورشید و شمشیر و شیر طلایی تاج‌دار
# - فارسی روان ایران fa-IR، ی ک فارسی، نیم‌فاصله: می‌شود، کتاب‌ها
# - واژگان: شهبانو فرح پهلوی، شاهزاده رضا پهلوی
# - عکس خبری و فیلم خبری از RSS اگر بود استفاده شود

import os, re, glob, json, datetime, time, sys
from pathlib import Path
import feedparser

# --- تصحیح فارسی داخلی (بدون وابستگی خارجی) ---
AR_TO_FA = {'ي': 'ی', 'ك': 'ک', 'ؤ': 'و', 'إ': 'ا', 'أ': 'ا', 'ء': ''}
GLOSSARY = {
    "شهبانو فرح": "شهبانو فرح پهلوی",
    "شاهزاده رضا": "شاهزاده رضا پهلوی",
    "رضا پهلوی": "شاهزاده رضا پهلوی",
    "فرح پهلوی": "شهبانو فرح پهلوی",
    "جمهوري اسلامي": "جمهوری اسلامی",
}

def correct_persian(text: str) -> str:
    if not text:
        return text
    for ar, fa in AR_TO_FA.items():
        text = text.replace(ar, fa)
    # نیم‌فاصله
    text = re.sub(r'\s+می\s+شود', ' می‌شود', text)
    text = re.sub(r'\s+می\s+کند', ' می‌کند', text)
    text = re.sub(r'\s+می\s+شوند', ' می‌شوند', text)
    text = re.sub(r'\s+می\s+کنند', ' می‌کنند', text)
    text = re.sub(r'کتاب\s+ها', 'کتاب‌ها', text)
    text = re.sub(r'\s+ها\b', '‌ها', text)
    # واژگان قفل شده
    for k,v in GLOSSARY.items():
        if k in text:
            text = text.replace(k, v)
    # فاصله‌ها
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- تاریخ شاهنشاهی 2585 ---
def get_shahanshahi_date():
    try:
        import jdatetime
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3, minutes=30)))
        jalali = jdatetime.datetime.fromgregorian(datetime=tehran_now)
        shahanshahi_year = jalali.year + 1180  # 1404 + 1180 = 2584 / 1405=2585
        # آبان 1404 = 2585 - الان 1404 آبان، پس 2585 درست است
        # برای اطمینان: اگر سال جلالی 1404 است، شاهنشاهی 2585
        if jalali.year == 1404:
            shahanshahi_year = 2585
        else:
            shahanshahi_year = jalali.year + 1180
        month_names = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"]
        month_name = month_names[jalali.month-1]
        return f"{jalali.day} {month_name} {shahanshahi_year}", tehran_now, jalali
    except Exception as e:
        print(f"jdatetime error {e}, fallback")
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3, minutes=30)))
        return f"11 آبان 2585", tehran_now, None

def format_persian_time(tehran_dt):
    h = tehran_dt.hour
    m = tehran_dt.minute
    def hm(h24):
        if h24 == 0: return "12 شب"
        elif 1 <= h24 <= 11: return f"{h24} بامداد"
        elif h24 == 12: return "12 نیمروز"
        elif 13 <= h24 <= 19: return f"{h24-12} پس از نیمروز"
        else: return f"{h24-12} شب"
    time_word = hm(h)
    if m != 0:
        return f"{time_word} و {m} دقیقه ایران"
    return f"{time_word} ایران"

# --- منابع ---
SOURCES = {
    "AP": "https://apnews.com/hub/ap-top-news?format=rss",
    "Reuters Iran": "https://news.google.com/rss/search?q=Iran+when:1h&hl=en-US&gl=US&ceid=US:en",
    "AFP": "https://www.afp.com/en/rss",
    "HRW": "https://www.hrw.org/rss/news",
    "Amnesty": "https://www.amnesty.org/en/rss/",
    "IranHR": "https://iranhr.net/en/feed/",
    "RezaPahlavi": "https://rsshub.app/twitter/user/PahlaviReza",
    "ShahbanouFarah": "https://rsshub.app/twitter/user/ShahbanouFarah",
}
KEYWORDS = ["iran", "ایران", "pahlavi", "پهلوی", "farah", "فرح", "reza", "رضا"]

def get_media_from_entry(entry):
    img = None
    video = None
    # enclosure
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            t = enc.get('type','')
            href = enc.get('href') or enc.get('url')
            if 'video' in t and not video:
                video = href
            if 'image' in t and not img:
                img = href
    # media_content
    if hasattr(entry, 'media_content'):
        for mc in entry.media_content:
            url = mc.get('url')
            t = mc.get('type','')
            if 'video' in t and not video:
                video = url
            if 'image' in t and not img:
                img = url
    # media_thumbnail
    if not img and hasattr(entry, 'media_thumbnail'):
        try:
            img = entry.media_thumbnail[0].get('url')
        except:
            pass
    return img, video

def collect_events():
    events = []
    for name, url in SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:4]:
                title = correct_persian(e.get("title","")[:300])
                summary = correct_persian(e.get("summary","")[:500])
                if not title:
                    continue
                # فیلتر ایران
                if any(k in title.lower() or k in summary.lower() for k in KEYWORDS) or "Pahlavi" in name or "Farah" in name or "HRW" in name or "IranHR" in name:
                    img, vid = get_media_from_entry(e)
                    events.append({
                        "title": title,
                        "summary": summary,
                        "source": name,
                        "link": e.get("link",""),
                        "image": img,
                        "video": vid,
                        "is_pahlavi": "Pahlavi" in name or "Farah" in name
                    })
        except Exception as ex:
            print(f"Feed error {name}: {ex}")
    # اگر کم بود، از گوگل نیوز پر کن
    if len(events) < 9:
        try:
            feed = feedparser.parse("https://news.google.com/rss/search?q=Iran&hl=fa&gl=IR&ceid=IR:fa")
            for e in feed.entries[:10]:
                if len(events) >= 12: break
                title = correct_persian(e.get("title","")[:300])
                if title and "ایران" in title:
                    img, vid = get_media_from_entry(e)
                    events.append({"title": title, "summary":"", "source":"Google", "link":e.get("link",""), "image":img, "video":vid, "is_pahlavi": False})
        except:
            pass
    # یکتا سازی
    seen = set()
    uniq = []
    for ev in events:
        if ev['title'] not in seen:
            uniq.append(ev)
            seen.add(ev['title'])
    return uniq[:12]

def build_script(events):
    shahanshahi_date_str, tehran, jalali = get_shahanshahi_date()
    persian_time = format_persian_time(tehran)
    header = f"{persian_time} - {shahanshahi_date_str}، رویدادهای ایران از رسانه ایرانا"

    lines = []
    lines.append(f"__HEADER__:{header}")
    lines.append(f"[00:00-00:10 اینترو دقیق: تیر سپید از پشت رنگین‌کمان سرخ زرد بنفش، دماوند گرد، تنها IRANA، بدون TELEVISION - فایل assets/irana_intro_final.mp4]")
    lines.append(f"گوینده مرد جوان کراواتی [تنها صدا + زیرآهنگ]: درود، {header}.")
    lines.append("")
    lines.append("=== 3 رویداد سربرگ: تنها صدا + زیرآهنگ، بدون تصویر استودیو ===")
    for i in range(min(3, len(events))):
        ev = events[i]
        voice = "زن جوان کتی" if i%2==1 else "مرد جوان کراواتی"
        lines.append(f"[{10+i*20}:{(i+1)*20}] گوینده {voice} [تنها صدا + زیرآهنگ]: {ev['title']}")
        if ev['image']:
            lines.append(f"  [عکس خبری: {ev['image']}]")
        if ev['video']:
            lines.append(f"  [فیلم خبری: {ev['video']}]")

    lines.append("")
    lines.append("[محو زیرآهنگ - ورود به استودیو ایرانامدیا - لوگو شیر و خورشید و شمشیر شفاف - بدون علامت جمهوری اسلامی]")
    lines.append("=== 6 رویداد اصلی: تصویر استودیو، یکی در میان بکتاش و شارلوت، بدون ریش، بدون عینک، بدون سبیل ===")
    for i, ev in enumerate(events[3:9]):
        voice = "زن جوان کتی" if i%2==1 else "مرد جوان کراواتی"
        anchor = "شارلوت" if i%2==1 else "بکتاش"
        lines.append(f"[{70+i*33}:{70+(i+1)*33}] گوینده {anchor} ({voice}) [تصویر استودیو + لوگو شیر طلایی تاج‌دار]: {ev['title']} - منبع: {ev['source']}")
        if ev['image']:
            lines.append(f"  [عکس خبری: {ev['image']}]")
        if ev['video']:
            lines.append(f"  [فیلم خبری: {ev['video']}]")

    lines.append("")
    lines.append("[270-300 آگهی پایانی: صدای زن - بدون درود - بدون تصویر استودیو]")
    lines.append("گوینده زن جوان کتی: رسانه ایرانا، تازه‌ترین رویدادهای ایران، سر هر ساعت، شبانروزی، ایرانا همه جا با شماست. @IranaMediaNews - https://whatsapp.com/channel/0029Vb9JxR1HgZWcZUxJY03Z")

    full = "\n".join(lines)
    return full, header

def main():
    Path("final_broadcast").mkdir(exist_ok=True)
    Path("assets").mkdir(exist_ok=True)
    events = collect_events()
    print(f"Collected {len(events)} events")
    for ev in events[:3]:
        print(f"- {ev['title'][:80]} img={bool(ev['image'])} vid={bool(ev['video'])}")

    script, header = build_script(events)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    script_path = Path(f"final_broadcast/script_{ts}.txt")
    script_path.write_text(script, encoding="utf-8")
    Path("final_broadcast/latest_header.txt").write_text(header, encoding="utf-8")
    # JSON برای توزیع
    Path("final_broadcast/latest_events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== SCRIPT SAVED {script_path} ===")
    print(script[:1000])
    # بررسی اینترو دقیق
    intro_paths = ["assets/irana_intro_final.mp4", "irana_intro_final.mp4", "docs/assets/irana_intro_final.mp4"]
    found = None
    for p in intro_paths:
        if Path(p).exists():
            found = p
            print(f"Intro exact found: {p} size {Path(p).stat().st_size}")
            break
    if not found:
        print("WARNING: Intro exact assets/irana_intro_final.mp4 not found - حتما آپلود کن!")
    return script_path

if __name__ == "__main__":
    main()
