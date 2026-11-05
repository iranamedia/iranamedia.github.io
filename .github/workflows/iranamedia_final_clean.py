#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# IRANA Media - Final script builder 2585 - Clean version (no stage commands in output)
import feedparser
from pathlib import Path
import datetime
import re

def get_shahanshahi_date():
    try:
        import jdatetime
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        jalali = jdatetime.datetime.fromgregorian(datetime=tehran_now)
        month_names = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"]
        month_name = month_names[jalali.month-1]
        return f"{jalali.day} {month_name} 2585", tehran_now
    except:
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        return f"11 آبان 2585", tehran_now

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

AR_TO_FA = {'ي': 'ی', 'ك': 'ک'}
def normalize_persian(text):
    for ar, fa in AR_TO_FA.items():
        text = text.replace(ar, fa)
    text = re.sub(r'\s+می\s+شود', ' می‌شود', text)
    text = re.sub(r'\s+می\s+کند', ' می‌کند', text)
    return text.strip()

SOURCES = {
    "AP": "https://flipboard.com/@associatedpress/top-stories-u7govdf1z.rss",
    "Reuters": "https://news.google.com/rss/search?q=site:reuters.com+Iran&hl=en-US&gl=US&ceid=US:en",
    "HRW": "https://www.hrw.org/rss/news",
}

KEYWORDS = ["iran", "ایران", "pahlavi", "پهلوی", "تهران", "tehran"]

def collect_and_build():
    events = []
    for name, url in SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:10]:
                title = normalize_persian(e.get("title",""))
                if any(k in title.lower() or k in title for k in KEYWORDS):
                    events.append({"title": title, "source": name, "link": e.get("link","")})
        except Exception as ex:
            print(f"Error {name}: {ex}")
    
    # Fallback if no Iran news found
    if len(events) < 3:
        events.extend([
            {"title": "تازه‌ترین تحولات ایران", "source": "IRANA", "link": ""},
            {"title": "ادامه پوشش رویدادهای ایران", "source": "IRANA", "link": ""},
            {"title": "گزارش لحظه به لحظه از ایران", "source": "IRANA", "link": ""},
        ])

    shahanshahi_date_str, tehran = get_shahanshahi_date()
    persian_time = format_persian_time(tehran)
    
    # --- Build FULL script for TTS (with stage directions for internal use) ---
    full_lines = []
    full_lines.append(f"درود، {persian_time} - {shahanshahi_date_str}، رویدادهای ایران از رسانه ایرانا.")
    for ev in events[:6]:
        full_lines.append(ev['title'])
    
    full_script_text = "\n\n".join(full_lines)
    
    # --- Build CLEAN caption for posting (NO [تنها صدا] commands) ---
    clean_caption_lines = []
    clean_caption_lines.append(f"🎙️ رسانه ایرانا | {persian_time} - {shahanshahi_date_str} (۲۵۸۵ شاهنشاهی)")
    clean_caption_lines.append("")
    for i, ev in enumerate(events[:6], 1):
        clean_caption_lines.append(f"{i}. {ev['title']}")
    clean_caption_lines.append("")
    clean_caption_lines.append("📡 @IranaMediaNews | iranamedia.github.io")
    clean_caption = "\n".join(clean_caption_lines)

    Path("final_broadcast").mkdir(exist_ok=True)
    now_tag = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    Path(f"final_broadcast/script_{now_tag}.txt").write_text(full_script_text, encoding="utf-8")
    Path(f"final_broadcast/caption_{now_tag}.txt").write_text(clean_caption, encoding="utf-8")
    Path(f"final_broadcast/script_latest.txt").write_text(full_script_text, encoding="utf-8")
    Path(f"final_broadcast/caption_latest.txt").write_text(clean_caption, encoding="utf-8")
    
    print("=== FULL (for TTS) ===")
    print(full_script_text[:1000])
    print("\n=== CLEAN CAPTION (for Telegram/YouTube/FB/IG - NO commands) ===")
    print(clean_caption)
    return full_script_text, clean_caption

if __name__ == "__main__":
    collect_and_build()
