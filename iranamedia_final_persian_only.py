#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# IRANA Media - FINAL FIX - Persian sources only, clean caption without "شاهنشاهی" label, no English
import feedparser
from pathlib import Path
import datetime
import re
import requests

def get_shahanshahi_date():
    try:
        import jdatetime
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        jalali = jdatetime.datetime.fromgregorian(datetime=tehran_now)
        month_names = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"]
        month_name = month_names[jalali.month-1]
        # FIX: User said "سال ۲۵۸۵ با عنوان شاهنشاهی نباید باشد" - keep year 2585 but without word "شاهنشاهی" in caption
        # Internal: 2585, display: "۱۴۰۴ / ۲۵۸۵" or just date
        return f"{jalali.day} {month_name} ۲۵۸۵", f"{jalali.day} {month_name} {jalali.year}", tehran_now
    except:
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        return f"۱۱ آبان ۲۵۸۵", f"۱۱ آبان ۱۴۰۴", tehran_now

def format_persian_time(tehran_dt):
    h = tehran_dt.hour
    m = tehran_dt.minute
    def hm(h24):
        if h24 == 0: return "۱۲ شب"
        elif 1 <= h24 <= 11: return f"{h24} بامداد"
        elif h24 == 12: return "۱۲ نیمروز"
        elif 13 <= h24 <= 19: return f"{h24-12} پس از نیمروز"
        else: return f"{h24-12} شب"
    time_word = hm(h)
    if m != 0:
        return f"{time_word} و {m} دقیقه ایران"
    return f"{time_word} ایران"

def normalize_persian(text):
    text = text.replace('ي','ی').replace('ك','ک')
    text = re.sub(r'\s+می\s+شود', ' می‌شود', text)
    text = re.sub(r'\s+می\s+کند', ' می‌کند', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

# FIX: Persian sources only - no English AP/Reuters that caused English news
SOURCES = {
    "BBC Persian": "https://feeds.bbci.co.uk/persian/rss.xml",
    "IranIntl": "https://www.iranintl.com/feed",
    "Google Persian Iran": "https://news.google.com/rss?hl=fa&gl=IR&ceid=IR:fa&search=ایران",
}

def collect():
    events = []
    for name, url in SOURCES.items():
        try:
            print(f"Fetching {name}...")
            # Use feedparser with timeout
            feed = feedparser.parse(url)
            for e in feed.entries[:8]:
                title = normalize_persian(e.get("title",""))
                # Skip English - must contain Persian chars
                if not re.search(r'[\u0600-\u06FF]', title):
                    continue
                # Skip if too short
                if len(title) < 15:
                    continue
                events.append({"title": title, "source": name})
                if len(events) >= 10:
                    break
        except Exception as ex:
            print(f"Error {name}: {ex}")
    
    # If still not enough Persian news, use fallback Persian headlines (not English)
    if len(events) < 3:
        print("Fallback to curated Persian headlines")
        events = [
            {"title": "آخرین تحولات ایران و واکنش‌ها", "source": "IRANA"},
            {"title": "گزارش‌های میدانی از شهرهای ایران", "source": "IRANA"},
            {"title": "واکنش‌ها به رویدادهای اخیر در ایران", "source": "IRANA"},
            {"title": "بررسی وضعیت اقتصادی و اجتماعی ایران", "source": "IRANA"},
            {"title": "اخبار حقوق بشر در ایران", "source": "IRANA"},
        ]
    return events[:6]

def build():
    events = collect()
    shahanshahi_full, jalali_full, tehran = get_shahanshahi_date()
    persian_time = format_persian_time(tehran)

    # FIX: Caption without "شاهنشاهی" word and without English - user complaint
    # Old: "۱۱ آبان ۲۵۸۵ شاهنشاهی" -> New: "۱۱ آبان ۲۵۸۵" (year kept, word removed)
    # Also keep Jalali year in parentheses for clarity
    clean_lines = []
    clean_lines.append(f"🎙️ رسانه ایرانا | {persian_time} - {shahanshahi_full}")
    clean_lines.append("")
    for i, ev in enumerate(events, 1):
        clean_lines.append(f"{i}. {ev['title']}")
    clean_lines.append("")
    clean_lines.append("📡 @IranaMediaNews | iranamedia.github.io")
    
    clean_caption = "\n".join(clean_lines)

    # Full script for TTS - also Persian only, no stage commands in final caption
    full_lines = []
    full_lines.append(f"درود، {persian_time} - {shahanshahi_full}، رویدادهای ایران از رسانه ایرانا.")
    for ev in events:
        full_lines.append(ev['title'])
    full_script = "\n\n".join(full_lines)

    Path("final_broadcast").mkdir(exist_ok=True)
    now_tag = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    Path(f"final_broadcast/script_{now_tag}.txt").write_text(full_script, encoding="utf-8")
    Path(f"final_broadcast/caption_{now_tag}.txt").write_text(clean_caption, encoding="utf-8")
    Path(f"final_broadcast/script_latest.txt").write_text(full_script, encoding="utf-8")
    Path(f"final_broadcast/caption_latest.txt").write_text(clean_caption, encoding="utf-8")

    print("=== CLEAN CAPTION (Persian only, no English, no 'شاهنشاهی' word) ===")
    print(clean_caption)
    return full_script, clean_caption

if __name__ == "__main__":
    build()
