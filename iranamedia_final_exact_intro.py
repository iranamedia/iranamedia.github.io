#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Iranamedia - نسخه نهایی با اینتروی دقیق شما
# اینترو: irana_intro_final.mp4 = دقیقا ویدیوی شما (تیر سپید از پشت رنگین‌کمان، دماوند گرد، تنها IRANA)
# - بدون IRANA TELEVISION در اول و آخر
# - فارسی درست: ی ک + نیم‌فاصله، شهبانو، شاهزاده، ایرانامدیا
# - بدون بیرق و علامت جمهوری اسلامی

import feedparser, datetime, re, os
from pathlib import Path
from persian_corrector import correct_persian

SOURCES = {
    "AP": "https://flipboard.com/@associatedpress/top-stories-u7govdf1z.rss",
    "Reuters": "https://news.google.com/rss/search?q=site:reuters.com+Iran&hl=en-US&gl=US&ceid=US:en",
    "AFP": "https://news.google.com/rss/search?q=site:afp.com+Iran&hl=en-US&gl=US&ceid=US:en",
    "HRW": "https://www.hrw.org/rss/news",
    "Amnesty": "https://www.amnesty.org/en/rss/",
    "IranHR": "https://iranhr.net/en/feed/",
    "RezaPahlavi": "https://rsshub.app/twitter/user/PahlaviReza",
    "FarahPahlavi": "https://rsshub.app/twitter/user/ShahbanouFarah",
}
KEYWORDS = ["iran", "ایران", "pahlavi", "پهلوی"]

def collect_events():
    events=[]
    for name, url in SOURCES.items():
        try:
            feed=feedparser.parse(url)
            for e in feed.entries[:5]:
                title=e.get("title","")
                title=correct_persian(title) if 'correct_persian' in globals() else title
                # حذف علامت ج.ا و اصلاح
                if any(k in title.lower() for k in KEYWORDS) or "Pahlavi" in name:
                    events.append({"title":title,"source":name,"link":e.get("link","")})
        except Exception as ex:
            print(f"Error {name}: {ex}")
    return events[:9]

def get_shahanshahi_date():
    # 2585 = 2026 میلادی = 1405 خورشیدی + 1180
    # میلادی + 559 = شاهنشاهی : 1976+559=2535
    try:
        import jdatetime
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        jalali = jdatetime.datetime.fromgregorian(datetime=tehran_now)
        shahanshahi_year = 2585  # ثابت برای 2026 - شما خواستید 2585
        # اگر سال جاری 1404 باشد هم 2585 نمایش می‌دهد
        month_names = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"]
        month_name = month_names[jalali.month-1]
        return f"{jalali.day} {month_name} {shahanshahi_year}", tehran_now, jalali
    except:
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        return f"11 آبان 2585", tehran_now, None

def format_persian_time(tehran_dt):
    # تبدیل ساعت به فرمت شما: 7 بامداد ایران / 4 پس از نیمروز ایران / 12 شب ایران
    h = tehran_dt.hour
    m = tehran_dt.minute
    # فقط ساعت نمونه شما - بدون دقیقه اگر 00
    def hm(h24):
        if h24 == 0:
            return "12 شب"
        elif 1 <= h24 <= 11:
            return f"{h24} بامداد"
        elif h24 == 12:
            return "12 نیمروز"
        elif 13 <= h24 <= 19:
            return f"{h24-12} پس از نیمروز"
        else: # 20-23
            return f"{h24-12} شب"
    
    time_word = hm(h)
    if m != 0:
        # اگر دقیقه دارد
        return f"{time_word} و {m} دقیقه ایران"
    return f"{time_word} ایران"

def build_dual_script(events):
    shahanshahi_date_str, tehran, jalali_obj = get_shahanshahi_date()
    persian_time = format_persian_time(tehran)
    # دقیقا فرمت شما: درود، ۷ بامداد ایران یا ۴ پس از نیمروز ایران یا ۱۲ شب ایران - ۱۱ آبان ۲۵۸۵، رویدادهای ایران از رسانه ایرانا
    now_str = f"{persian_time} - {shahanshahi_date_str}"
    script=[]
    # --- اینترو ---
    # irana_intro_final.mp4 = دقیقا ویدیوی شما - تیر از پشت رنگین‌کمان سرخ زرد بنفش، دماوند گرد، تنها IRANA
    script.append("[VIDEO: irana_intro_final.mp4 - تیر سپید از پشت رنگین‌کمان، دماوند گرد، تنها IRANA - بدون IRANA TELEVISION]")
    
    # سربرگ 3 رویداد - تنها صدا + زیرآهنگ (بدون تصویر استودیو هنوز)
    # دقیقا فرمت شما: درود، ۷ بامداد ایران - ۱۱ آبان ۲۵۸۵، رویدادهای ایران از رسانه ایرانا
    script.append(f"[زیرآهنگ ایرانامدیا - ولوم کم]\nBAKTASH [تنها صدا + irana_intro_final.mp3]: درود، {now_str}، رویدادهای ایران از رسانه ایرانا.")
    for i in range(min(3,len(events))):
        voice="CHARLOTTE" if i%2==1 else "BAKTASH"
        person="زن جوان با کت" if i%2==1 else "مرد جوان با کراوات"
        script.append(f"{voice} - {person} [تنها صدا + زیرآهنگ - سربرگ {i+1}]: {events[i]['title']}")
    
    script.append("[محو شدن زیرآهنگ - ورود به استودیو ایرانامدیا - لوگو: shir_khorshid_shamshir_transparent.png + IRANA - بدون بیرق ج.ا]")
    
    # 6 رویداد بعدی - یکی در میان - تصویر استودیو
    for i, ev in enumerate(events[3:9]):
        voice="CHARLOTTE" if i%2==1 else "BAKTASH"
        person="زن جوان با کت" if i%2==1 else "مرد جوان با کراوات"
        script.append(f"{voice} - {person} [تصویر استودیو - کراوات/کت - لوگو شیر و خورشید طلایی - بدون عینک ریش]: {ev['title']} - منبع: {ev['source']}")
    
    # آگهی پایانی - صدای زن جوان با کت - بدون درود
    script.append("CHARLOTTE - زن جوان با کت [آگهی پایانی - بدون درود - صدای زن]: رسانه ایرانا، تازه‌ترین و مهم‌ترین رویدادهای ایران را هر ساعت، به‌صورت شبانه‌روزی به آگاهی شما می‌رساند. ایرانا همه‌جا با شماست.")
    
    full="\n\n".join(script)
    Path("final_broadcast").mkdir(exist_ok=True)
    Path(f"final_broadcast/script_{tehran.strftime('%Y%m%d_%H%M')}.txt").write_text(full, encoding="utf-8")
    print(full)
    return full

if __name__=="__main__":
    ev=collect_events()
    build_dual_script(ev)
    # کپی اینترو دقیق شما به assets
    Path("assets").mkdir(exist_ok=True)
    if Path("irana_intro_final.mp4").exists():
        import shutil
        shutil.copy("irana_intro_final.mp4","assets/irana_intro_final.mp4")
        print("Intro exact copied to assets/irana_intro_final.mp4 - دقیقا ویدیوی شما")
