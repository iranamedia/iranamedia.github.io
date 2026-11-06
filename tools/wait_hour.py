"""تا سر ساعتِ خبرنامه (به وقت تهران) درنگ می‌کند تا پخش درست سر ساعت ایران باشد.
ساعت از stamp خبرنامه خوانده می‌شود: «ساعت ۹ به وقت تهران، ...» ← ۹:۰۰ تهران.
اگر آن ساعت گذشته باشد یا بیش از MAX_WAIT دقیقه مانده باشد، بی‌درنگ ادامه می‌دهد.
اجرا: python3 tools/wait_hour.py bulletin/latest.json"""
import datetime, json, os, re, sys, time

TEHRAN = datetime.timezone(datetime.timedelta(hours=3, minutes=30))   # ایران تغییر ساعت تابستانی ندارد
MAX_WAIT = float(os.environ.get("MAX_WAIT", "40")) * 60

stamp = json.load(open(sys.argv[1], encoding="utf-8"))["stamp"]
m = re.search(r"ساعت\s*(\d+)", stamp.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
if not m:
    print("ساعت در stamp نیست؛ بی‌درنگ"); sys.exit(0)
now = datetime.datetime.now(TEHRAN)
target = now.replace(hour=int(m.group(1)) % 24, minute=0, second=0, microsecond=0)
if target < now - datetime.timedelta(hours=12):
    target += datetime.timedelta(days=1)                # خبرنامه‌ی ساعت ۰، نوشته‌شده در ۲۳:۳۵
wait = (target - now).total_seconds()
if wait <= 0:
    print(f"سر ساعت گذشته ({now:%H:%M} تهران)؛ بی‌درنگ")
elif wait > MAX_WAIT:
    print(f"{wait/60:.0f} دقیقه تا سر ساعت؛ بیش از اندازه، بی‌درنگ")
else:
    print(f"درنگ {wait/60:.1f} دقیقه تا {target:%H:%M} تهران", flush=True)
    time.sleep(wait)
    print("سر ساعت ایران")
