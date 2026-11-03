#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Iranamedia - نسخه نهایی بدون وابستگی خارجی - اینترو دقیق شما
import feedparser, datetime, re
from pathlib import Path

def correct_persian(text):
    if not text: return text
    text = text.replace('ي','ی').replace('ك','ک').replace('ؤ','و')
    text = re.sub(r'\s+می\s+شود',' می‌شود', text)
    text = re.sub(r'\s+می\s+کند',' می‌کند', text)
    text = re.sub(r'کتاب ها','کتاب‌ها', text)
    return text.strip()

SOURCES = {
    "AP": "https://flipboard.com/@associatedpress/top-stories-u7govdf1z.rss",
    "Reuters": "https://news.google.com/rss/search?q=site:reuters.com+Iran&hl=en-US&gl=US&ceid=US:en",
    "HRW": "https://www.hrw.org/rss/news",
    "RezaPahlavi": "https://rsshub.app/twitter/user/PahlaviReza",
}
KEYWORDS = ["iran","ایران","pahlavi","پهلوی"]

def collect_events():
    events=[]
    for name, url in SOURCES.items():
        try:
            feed=feedparser.parse(url)
            for e in feed.entries[:5]:
                title=correct_persian(e.get("title",""))
                if any(k in title.lower() for k in KEYWORDS) or "Pahlavi" in name:
                    events.append({"title":title,"source":name})
        except Exception as ex:
            print(f"Error {name}: {ex}")
    return events[:9]

def get_shahanshahi_date():
    try:
        import jdatetime
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        jalali = jdatetime.datetime.fromgregorian(datetime=tehran_now)
        month_names = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"]
        return f"{jalali.day} {month_names[jalali.month-1]} 2585", tehran_now
    except:
        tehran_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3,minutes=30)))
        return f"11 آبان 2585", tehran_now

def format_persian_time(tehran_dt):
    h=tehran_dt.hour
    def hm(h24):
        if h24==0: return "12 شب"
        elif 1<=h24<=11: return f"{h24} بامداد"
        elif h24==12: return "12 نیمروز"
        elif 13<=h24<=19: return f"{h24-12} پس از نیمروز"
        else: return f"{h24-12} شب"
    return f"{hm(h)} ایران"

def build_dual_script(events):
    shahanshahi_date_str, tehran = get_shahanshahi_date()
    persian_time = format_persian_time(tehran)
    now_str = f"{persian_time} - {shahanshahi_date_str}"
    script=[]
    script.append("[VIDEO: irana_intro_final.mp4 - تير سپيد از پشت رنگين‌کمان، دماوند گرد، تنها IRANA]")
    script.append(f"[زيرآهنگ] BAKTASH [تنها صدا]: درود، {now_str}، رويدادهاي ايران از رسانه ايرانا.")
    for i in range(min(3,len(events))):
        voice="CHARLOTTE" if i%2==1 else "BAKTASH"
        script.append(f"{voice} - سربرگ {i+1}: {events[i]['title']}")
    script.append("[محو شدن زيرآهنگ - ورود به استوديو - لوگو شير و خورشيد طلايي]")
    for i, ev in enumerate(events[3:9]):
        voice="CHARLOTTE" if i%2==1 else "BAKTASH"
        script.append(f"{voice} - استوديو: {ev['title']} - منبع: {ev['source']}")
    script.append("CHARLOTTE [آگهي پاياني - بدون درود]: رسانه ايرانا، تازه‌ترين و مهم‌ترين رويدادهاي ايران را هر ساعت، به‌صورت شبانه‌روزي به آگاهي شما مي‌رساند. ايرانا همه‌جا با شماست.")
    full="\n\n".join(script)
    Path("final_broadcast").mkdir(exist_ok=True)
    Path(f"final_broadcast/script_{tehran.strftime('%Y%m%d_%H%M')}.txt").write_text(full, encoding="utf-8")
    print(full)
    return full

if __name__=="__main__":
    ev=collect_events()
    build_dual_script(ev)
