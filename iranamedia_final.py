
# iranamedia_final.py - نسخه نهایی
# ویژگی‌ها:
# - نوشتار فارسی درست (ی ک + نیم‌فاصله)
# - واژگان ثابت: شهریار ایران، شهبانو، شاهزاده، ایرانامدیا
# - گوینده مرد جوان با کراوات، زن جوان با کت، بدون ریش و عینک
# - بدون علامت جمهوری اسلامی
# - 3 رویداد نخست: سربرگ + صدا + زیرآهنگ، بقیه یکی در میان

import feedparser
from pathlib import Path
import datetime
import re

def get_shahanshahi_date():
    # 2585 = 2026 میلادی = 1405 خورشیدی + 1180
    import datetime
    try:
        import jdatetime
        tehran_shahanshahi_date_str, tehran = get_shahanshahi_date()
    time_str = tehran.strftime("%H:%M")
    now = f"{time_str} به وقت تهران - {shahanshahi_date_str}"
    script = []
    
    # سربرگ 3 رویداد - تنها صدا + زیرآهنگ
    script.append(f"[زیرآهنگ ایرانامدیا - ولوم کم]\nگوینده مرد جوان با کراوات [تنها صدا]: سلام، چکیده رویدادهای ایران، ساعت {now}، از رسانه ایرانامدیا.")
    for i in range(min(3, len(events))):
        voice = "زن جوان با کت" if i%2==1 else "مرد جوان با کراوات"
        script.append(f"گوینده {voice} [تنها صدا + زیرآهنگ - سربرگ]: {events[i]['title']}")
    
    script.append("[محو شدن زیرآهنگ - ورود به استودیو ایرانامدیا - بدون علامت جمهوری اسلامی]")
    
    for i, ev in enumerate(events[3:9]): # 6 رویداد بعدی
        voice = "زن جوان با کت" if i%2==1 else "مرد جوان با کراوات"
        script.append(f"گوینده {voice} [تصویر استودیو - کراوات/کت]: {ev['title']} - منبع: {ev['source']}")
    
    full_script = "\n\n".join(script)
    Path("final_broadcast").mkdir(exist_ok=True)
    Path(f"final_broadcast/script_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt").write_text(full_script, encoding="utf-8")
    print(full_script)
    return full_script

if __name__ == "__main__":
    collect_and_build()
