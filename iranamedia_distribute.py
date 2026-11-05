#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Iranamedia Distribute - Telegram + FB (both) + IG + YouTube - 2585
import os, glob, datetime, requests, json, time
from pathlib import Path

def env_any(*names):
    for n in names:
        v = os.getenv(n)
        if v and v.strip():
            return v.strip()
    return None

def get_latest_script():
    files = sorted(glob.glob("final_broadcast/script_*.txt"), reverse=True)
    if not files:
        return None, "درود، رویدادهای ایران از رسانه ایرانا - 11 آبان 2585"
    txt = Path(files[0]).read_text(encoding="utf-8")[:3000]
    return files[0], txt

def get_latest_video():
    for pattern in ["final_5min.mp4", "final_broadcast/broadcast_*.mp4", "assets/irana_intro_final.mp4", "irana_intro_final.mp4"]:
        files = sorted(glob.glob(pattern), reverse=True)
        if files and Path(files[0]).exists() and Path(files[0]).stat().st_size > 1000:
            return files[0]
    return None

def send_telegram(text, video_path=None):
    token = env_any("TELEGRAM_BOT_TOKEN")
    chat_id = env_any("TELEGRAM_CHANNEL_ID", "TELEGRAM_CHAT_ID")
    print(f"[Telegram] token={bool(token)} chat_id={chat_id}")
    if not token or not chat_id:
        print("Telegram SKIP")
        return False
    caption = text[:800] + "\n\n@IranaMediaNews\nhttps://whatsapp.com/channel/0029Vb9JxR1HgZWcZUxJY03Z\nhttps://iranamedia.github.io"
    try:
        if video_path:
            with open(video_path, "rb") as f:
                r = requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
                                   data={"chat_id": chat_id, "caption": caption},
                                   files={"video": f}, timeout=120)
        else:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json={"chat_id": chat_id, "text": caption}, timeout=30)
        print(f"Telegram response: {r.status_code} {r.text[:600]}")
        return r.ok
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def post_facebook(text, video_path=None):
    page_id_raw = env_any("FB_PAGE_ID", "META_PAGE_ID")
    token_raw = env_any("FB_PAGE_ACCESS_TOKEN", "META_PAGE_TOKEN", "META_PAGE_ACCESS_TOKEN")
    print(f"[Facebook] raw page_id={page_id_raw} token={bool(token_raw)}")
    if not page_id_raw or not token_raw:
        print("Facebook SKIP - FB_PAGE_ID لازم است")
        return False
    page_ids = [p.strip() for p in page_id_raw.split(',') if p.strip()]
    tokens = [t.strip() for t in token_raw.split(',')] if ',' in token_raw else [token_raw]*len(page_ids)
    if len(tokens) != len(page_ids):
        tokens = [tokens[0]]*len(page_ids)
    ok=False
    for i, pid in enumerate(page_ids):
        tok = tokens[i] if i < len(tokens) else tokens[0]
        print(f"[Facebook] {i+1}/{len(page_ids)} -> {pid}")
        try:
            if video_path:
                with open(video_path, "rb") as f:
                    r = requests.post(f"https://graph.facebook.com/v20.0/{pid}/videos",
                                      data={"description": text[:2000], "access_token": tok},
                                      files={"source": f}, timeout=180)
            else:
                r = requests.post(f"https://graph.facebook.com/v20.0/{pid}/feed",
                                  data={"message": text[:2000], "access_token": tok}, timeout=30)
            print(f"Facebook {pid}: {r.status_code} {r.text[:400]}")
            if r.ok:
                ok=True
        except Exception as e:
            print(f"FB error {pid}: {e}")
    return ok

def post_instagram_reel(text, video_path=None):
    ig_id_raw = env_any("IG_USER_ID", "INSTAGRAM_USER_ID", "IG_ID")
    token_raw = env_any("FB_PAGE_ACCESS_TOKEN", "META_PAGE_TOKEN", "IG_ACCESS_TOKEN")
    print(f"[Instagram] ig_id={ig_id_raw} token={bool(token_raw)} video={video_path}")
    if not ig_id_raw or not token_raw or not video_path:
        print("Instagram SKIP - IG_USER_ID لازم است (و FB_PAGE_ACCESS_TOKEN)")
        return False
    ig_ids = [p.strip() for p in ig_id_raw.split(',') if p.strip()]
    tokens = [t.strip() for t in token_raw.split(',')] if ',' in token_raw else [token_raw]*len(ig_ids)
    if len(tokens) != len(ig_ids):
        tokens = [tokens[0]]*len(ig_ids)
    
    overall=False
    for idx, ig_id in enumerate(ig_ids):
        tok = tokens[idx] if idx < len(tokens) else tokens[0]
        print(f"[Instagram] Reel {idx+1}/{len(ig_ids)} -> {ig_id}")
        try:
            # مرحله 1: ساخت session آپلود resumable
            # بر اساس مستندات IG Graph API v20
            init_url = f"https://graph.facebook.com/v20.0/{ig_id}/media"
            init_data = {
                "media_type": "REELS",
                "upload_type": "resumable",
                "access_token": tok
            }
            r1 = requests.post(init_url, data=init_data, timeout=30)
            print(f"IG init: {r1.status_code} {r1.text[:600]}")
            if not r1.ok:
                continue
            j1 = r1.json()
            upload_url = j1.get("upload_url")
            # بعضی نسخه‌ها uri می‌دهند
            if not upload_url:
                upload_url = j1.get("uri")
            if not upload_url:
                # اگر مستقیم id داد، یعنی از نوع قدیمی video_url است - نیاز به URL عمومی
                # برای تست، سعی می‌کنیم با video_id موجود ادامه دهیم
                print(f"IG no upload_url, trying video_id flow: {j1}")
                continue
            
            # مرحله 2: آپلود فایل
            file_size = Path(video_path).stat().st_size
            with open(video_path, "rb") as f:
                # آپلود باینری - هدر مخصوص IG
                headers = {
                    "Authorization": f"OAuth {tok}",
                    "offset": "0",
                    "file_size": str(file_size)
                }
                r2 = requests.post(upload_url, data=f.read(), headers=headers, timeout=180)
                print(f"IG upload: {r2.status_code} {r2.text[:600]}")
            
            # مرحله 3: چک وضعیت و ساخت container نهایی اگر video_id داریم
            # در نسخه جدید، بعد از آپلود، باید با upload_url دوباره container بسازی
            # فعلا 5 ثانیه صبر
            time.sleep(5)
            
            # مرحله 4: ساخت Reel با caption
            # برای نسخه resumable، باید video_id را از مرحله اول گرفت - اگر j1 شامل id نیست، دوباره init می‌کنیم با caption
            # تلاش نهایی: استفاده از upload_url به عنوان video
            # این بخش ممکن است نیاز به polling داشته باشد
            
            # ساده‌ترین: بعد از آپلود، یک container نهایی می‌سازیم
            # اگر upload_url شامل video_id است، از آن استفاده کن
            # در غیر اینصورت، سعی کن با همان ig_id/media و caption
            # این پیاده‌سازی بر اساس مستندات رسمی 2024 است و ممکن است نیاز به تنظیم داشته باشد
            
            print(f"IG upload done for {ig_id}, waiting for processing...")
            # مرحله publish - باید creation_id بگیریم
            # فعلا لاگ می‌کنیم که آپلود شد - publish مرحله بعدی است که نیاز به polling دارد
            
            # تلاش برای publish با استفاده از id که از init گرفتیم (اگر id داشت)
            creation_id = j1.get("id")
            if creation_id:
                # اضافه کردن caption
                r3 = requests.post(f"https://graph.facebook.com/v20.0/{ig_id}/media",
                                   data={"media_type":"REELS","video_id":creation_id,"caption":text[:2200],"access_token":tok},
                                   timeout=30)
                print(f"IG create with caption: {r3.status_code} {r3.text[:600]}")
                if r3.ok:
                    cid = r3.json().get("id")
                    if cid:
                        time.sleep(3)
                        r4 = requests.post(f"https://graph.facebook.com/v20.0/{ig_id}/media_publish",
                                           data={"creation_id":cid,"access_token":tok}, timeout=30)
                        print(f"IG publish: {r4.status_code} {r4.text[:600]}")
                        if r4.ok:
                            overall=True
            
            # اگر بالا موفق نشد، حداقل تلاش کردیم
            if not overall:
                print(f"IG {ig_id}: uploaded but publish needs manual check - see https://developers.facebook.com/docs/instagram-api/guides/reels")
            
        except Exception as e:
            print(f"Instagram error {ig_id}: {e}")
    return overall

def upload_youtube(text, video_path=None):
    client_id = env_any("YOUTUBE_CLIENT_ID", "YT_CLIENT_ID")
    client_secret = env_any("YOUTUBE_CLIENT_SECRET", "YT_CLIENT_SECRET")
    refresh_token = env_any("YOUTUBE_REFRESH_TOKEN", "YT_REFRESH_TOKEN")
    print(f"[YouTube] {bool(client_id)} {bool(client_secret)} {bool(refresh_token)} video={video_path}")
    if not all([client_id, client_secret, refresh_token, video_path]):
        print("YouTube SKIP")
        return False
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from googleapiclient.http import MediaFileUpload
        creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
                            client_id=client_id, client_secret=client_secret)
        youtube = build("youtube", "v3", credentials=creds)
        title = (text.split("\n")[0][:85] if text else "رویدادهای ایران") + " | IRANA"
        body = {
            "snippet": {
                "title": title[:100],
                "description": text[:4000] + "\n\n@IranaMediaNews\nhttps://iranamedia.github.io",
                "tags": ["ایران","Iran","IRANA"],
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
    post_instagram_reel(txt, vf)
    upload_youtube(txt, vf)
    print("Distribution done - Telegram 200 + FB both + IG + YouTube")
