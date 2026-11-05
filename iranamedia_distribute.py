#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Iranamedia Distribute - سازگار با Secrets موجود شما
import os, glob, datetime, requests, json
from pathlib import Path

def env_any(*names):
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return None

def get_latest_script():
    files = sorted(glob.glob("final_broadcast/script_*.txt"), reverse=True)
    if not files:
        return None, "درود، 11 آبان 2585، رویدادهای ایران از رسانه ایرانا"
    txt = Path(files[0]).read_text(encoding="utf-8")[:3000]
    return files[0], txt

def get_latest_video():
    for pattern in ["final_broadcast/broadcast_*.mp4", "final_5min.mp4", "assets/irana_intro_final.mp4", "irana_intro_final.mp4"]:
        files = sorted(glob.glob(pattern), reverse=True)
        if files and Path(files[0]).exists() and Path(files[0]).stat().st_size > 1000:
            return files[0]
    return None

def send_telegram(text, video_path=None):
    token = env_any("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
    chat_id = env_any("TELEGRAM_CHANNEL_ID", "TELEGRAM_CHANNEL_ID_ID", "TELEGRAM_CHAT_ID")
    print(f"[Telegram] token={bool(token)} chat_id={chat_id}")
    if not token or not chat_id:
        print("Telegram secrets missing - SKIP")
        return False
    caption = text[:1000] + "\n\n@IranaMediaNews\nhttps://whatsapp.com/channel/0029Vb9JxR1HgZWcZUxJY03Z\nhttps://iranamedia.github.io"
    try:
        if video_path:
            with open(video_path, "rb") as f:
                r = requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
                                   data={"chat_id": chat_id, "caption": caption},
                                   files={"video": f}, timeout=90)
        else:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json={"chat_id": chat_id, "text": caption}, timeout=30)
        print(f"Telegram response: {r.status_code} {r.text[:500]}")
        return r.ok
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def post_facebook(text, video_path=None):
    page_id = env_any("FB_PAGE_ID", "META_PAGE_ID")
    token = env_any("FB_PAGE_ACCESS_TOKEN", "META_PAGE_TOKEN", "META_PAGE_ACCESS_TOKEN")
    print(f"[Facebook] page_id={bool(page_id)} token={bool(token)}")
    if not page_id or not token:
        print("FB secrets missing - SKIP (META_PAGE_TOKEN داری ولی FB_PAGE_ID لازم است)")
        return False
    try:
        if video_path:
            with open(video_path, "rb") as f:
                r = requests.post(f"https://graph.facebook.com/v20.0/{page_id}/videos",
                                  data={"description": text[:2000], "access_token": token},
                                  files={"source": f}, timeout=120)
        else:
            r = requests.post(f"https://graph.facebook.com/v20.0/{page_id}/feed",
                              data={"message": text[:2000], "access_token": token}, timeout=30)
        print(f"Facebook: {r.status_code} {r.text[:300]}")
        return r.ok
    except Exception as e:
        print(f"Facebook error: {e}")
        return False

def upload_youtube(text, video_path=None):
    tehran_hour = (datetime.datetime.utcnow() + datetime.timedelta(hours=3, minutes=30)).hour
    # برای تست، هر ساعت اجازه بده - بعدا می‌توانی به 0,4,8,12,16,20 محدود کنی
    # if tehran_hour not in [0,4,8,12,16,20]:
    #     print(f"YouTube skip hour {tehran_hour}")
    #     return False
    client_id = env_any("YOUTUBE_CLIENT_ID", "YT_CLIENT_ID")
    client_secret = env_any("YOUTUBE_CLIENT_SECRET", "YT_CLIENT_SECRET")
    refresh_token = env_any("YOUTUBE_REFRESH_TOKEN", "YT_REFRESH_TOKEN")
    print(f"[YouTube] client_id={bool(client_id)} secret={bool(client_secret)} refresh={bool(refresh_token)} video={video_path}")
    if not all([client_id, client_secret, refresh_token, video_path]):
        print("YouTube secrets missing or no video - SKIP")
        return False
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from googleapiclient.http import MediaFileUpload
        creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
                            client_id=client_id, client_secret=client_secret)
        youtube = build("youtube", "v3", credentials=creds)
        title = (text.split("\n")[0][:90] if text else "رویدادهای ایران") + " | IRANA"
        body = {
            "snippet": {
                "title": title[:100],
                "description": text[:4000] + "\n\n@IranaMediaNews\nhttps://iranamedia.github.io",
                "tags": ["ایران", "Iran", "IRANA", "خبر"],
                "categoryId": "25"
            },
            "status": {"privacyStatus": "public"}
        }
        media = MediaFileUpload(video_path, resumable=True, mimetype="video/mp4")
        req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = req.execute()
        print(f"YouTube uploaded ID: {resp.get('id')}")
        return True
    except Exception as e:
        print(f"YouTube error: {e}")
        return False

if __name__ == "__main__":
    sf, txt = get_latest_script()
    vf = get_latest_video()
    print(f"Script: {sf}")
    print(f"Video: {vf}")
    send_telegram(txt, vf)
    post_facebook(txt, vf)
    upload_youtube(txt, vf)
    print("Distribution done")
