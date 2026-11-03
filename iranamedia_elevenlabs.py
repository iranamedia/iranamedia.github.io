# iranamedia_elevenlabs.py - نسخه حرفه‌ای با ElevenLabs
# صداها: بکتاش (مرد) + شارلوت/شارلین (زن) - فارسی روان ایران، نه دری
# رسانه ایرانا - Iranamedia - Current Events - رویدادهای ایران
# آگهی: صدای زن، بدون درود
# نوشتار درست، بدون علامت جمهوری اسلامی

import feedparser
import re
from pathlib import Path
import datetime
import os
import requests
import time

# --- تنظیمات ElevenLabs ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# این IDها را از elevenlabs.io > My Voices > بکتاش و Charlotte/Charlene کپی کن
VOICE_BAKTASH = os.getenv("VOICE_BAKTASH_ID", "baktash_voice_id_here")  # مرد جوان با کراوات
VOICE_CHARLOTTE = os.getenv("VOICE_CHARLOTTE_ID", "charlotte_voice_id_here")  # زن جوان با کت + آگهی

# --- تصحیح فارسی ---
AR_TO_FA = {'ي': 'ی', 'ك': 'ک'}
def normalize_persian(text):
    for ar, fa in AR_TO_FA.items():
        text = text.replace(ar, fa)
    text = re.sub(r'\s+می\s+شود', ' می‌شود', text)
    text = re.sub(r'\s+می\s+کند', ' می‌کند', text)
    text = text.replace('شهبانو فرح', 'شهبانو فرح پهلوی')
    text = text.replace('شاهزاده رضا', 'شاهزاده رضا پهلوی')
    # درود فقط برای خبر، نه برای آگهی
    return text.strip()

SOURCES = {
    "AP": "https://flipboard.com/@associatedpress/top-stories-u7govdf1z.rss",
    "Reuters": "https://news.google.com/rss/search?q=site:reuters.com+Iran&hl=en-US&gl=US&ceid=US:en",
    "HRW": "https://www.hrw.org/rss/news",
    "RezaPahlavi": "https://rsshub.app/twitter/user/PahlaviReza",
    "FarahPahlavi": "https://rsshub.app/twitter/user/ShahbanouFarah",
}
KEYWORDS = ["iran", "ایران", "pahlavi", "پهلوی"]

def collect_events():
    events = []
    for name, url in SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:3]:
                title = normalize_persian(e.get("title",""))[:150]
                if any(k in title.lower() for k in KEYWORDS) or "Pahlavi" in name:
                    events.append({"title": title, "source": name})
        except:
            pass
    return events[:9]

def tts_elevenlabs(text, voice_id, output_path):
    if not ELEVENLABS_API_KEY or "voice_id_here" in voice_id:
        print(f"SKIP ElevenLabs (no key/ID) -> would say: {text[:60]}")
        # فایل خالی برای تست
        Path(output_path).write_bytes(b"")
        return False
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # فارسی روان ایران را خوب می‌خواند
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.35,
            "use_speaker_boost": True
        }
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code == 200:
        Path(output_path).write_bytes(r.content)
        print(f"OK {output_path} - {text[:50]}")
        return True
    else:
        print(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
        return False

def build_broadcast():
    events = collect_events()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3, minutes=30)))
    now_str = now.strftime("%H:%M به وقت تهران - %d %B")
    
    Path("output").mkdir(exist_ok=True)
    
    # --- بخش خبری - با درود - صدای بکتاش ---
    intro_text = f"درود، رویدادهای ایران، ساعت {now_str}، از رسانه ایرانا، Iranamedia."
    tts_elevenlabs(intro_text, VOICE_BAKTASH, "output/00_intro_baktash_tie.mp3")
    time.sleep(1)
    
    # ۳ سربرگ نخست - یکی در میان بکتاش / شارلوت
    for i in range(min(3, len(events))):
        voice = VOICE_CHARLOTTE if i % 2 == 1 else VOICE_BAKTASH
        tts_elevenlabs(events[i]['title'], voice, f"output/0{i+1}_header.mp3")
        time.sleep(1)
    
    # بقیه
    for idx, ev in enumerate(events[3:]):
        voice = VOICE_CHARLOTTE if idx % 2 == 1 else VOICE_BAKTASH
        tts_elevenlabs(ev['title'], voice, f"output/{4+idx}_body.mp3")
        time.sleep(1)
    
    # --- آگهی پایانی - صدای زن شارلوت/شارلین - بدون درود ---
    ad_text = "رسانه ایرانا، تازه‌ترین رویدادهای ایران، سر هر ساعت، شبانروزی، ایرانا همه جا با شماست"
    tts_elevenlabs(ad_text, VOICE_CHARLOTTE, "output/99_outro_ad_charlotte.mp3")
    
    # متن برای سایت و تلگرام
    full_text = f"Current Events - رویدادهای ایران\nرسانه ایرانا - Iranamedia\n{now_str}\n\n" + "\n\n".join([e['title'] for e in events]) + f"\n\n---\n{ad_text}\n@IranaMediaNews\nWhatsapp: https://whatsapp.com/channel/0029Vb9JxR1HgZWcZUxJY03Z"
    Path("output/final_post.txt").write_text(full_text, encoding="utf-8")
    
    # ارسال به تلگرام
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    if bot_token and channel_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": channel_id, "text": full_text})
    
    print("Build done - بکتاش + شارلوت/شارلین - فارسی روان ایران")

if __name__ == "__main__":
    build_broadcast()
