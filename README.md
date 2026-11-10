# رسانه ایرانا

تازه‌ترین رویدادهای ایران، شبانروزی سر هر ساعت کشور.

- اپ ایرانا: https://iranamedia.github.io
- کانال تلگرام: https://t.me/IranaMediaNews

## چگونه کار می‌کند
1. نویسنده‌ی خبرنامه هر ساعت (دقیقه‌ی ۳۵ به وقت تهران) `bulletin/latest.json` را با دستورهای `tools/rules.md` می‌نویسد.
2. workflow «رسانه ایرانا» (`.github/workflows/radio.yml`) با هر خبرنامه‌ی تازه:
   - متن خبرنامه را در تلگرام می‌فرستد و تارنما را به‌روز می‌کند؛
   - در ساعت‌های گفتاری (۸، ۱۶، ۲۰ و ۲۴ تهران): رادیو با دو گوینده (`radio.py`)، سپس تلویزیون ایرانا
     (`tv.py`: ویدیوی آغاز + قاب خبری ۱۶:۹ + فیلم نمادین Pixabay) در تلگرام، یوتیوب، فیسبوک و اینستاگرام (`social.py`).

## رازها (Settings → Secrets and variables → Actions)
`ELEVENLABS_API_KEY`، `TELEGRAM_BOT_TOKEN`، `META_PAGE_TOKEN`، `IG_USER_ID`، `YT_CLIENT_ID`، `YT_CLIENT_SECRET`، `YT_REFRESH_TOKEN`؛
دلخواه: `PIXABAY_API_KEY` (فیلم نمادین)، `BAKTASH_VOICE_ID`، `CHARLOTTE_VOICE_ID`.

همه‌چیز پیش‌تر ساخته می‌شود و درست سر ساعت ایران منتشر می‌شود (`tools/wait_hour.py`).
