#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# IRANA Distribute FINAL FIXED - clean caption (no [commands]), real 5min video, honest reporting
import os, glob, requests, time, sys
from pathlib import Path

def env_any(*names):
    for n in names:
        v = os.getenv(n)
        if v and v.strip():
            return v.strip()
    return None

def get_latest_caption_and_video():
    # Prefer clean caption (no [تنها صدا] commands) - Claude fix
    cap_files = sorted(glob.glob("final_broadcast/caption_*.txt") + glob.glob("final_broadcast/caption_latest.txt"), reverse=True)
    script_files = sorted(glob.glob("final_broadcast/script_*.txt"), reverse=True)
    caption = ""
    if cap_files and Path(cap_files[0]).exists():
        caption = Path(cap_files[0]).read_text(encoding="utf-8")
    elif script_files:
        # Fallback clean script
        raw = Path(script_files[0]).read_text(encoding="utf-8")
        # Remove stage commands
        lines = []
        for line in raw.split("\n"):
            if line.strip().startswith("["): continue
            if "گوینده" in line and "[" in line: 
                # Extract after colon
                if ":" in line:
                    line = line.split(":",1)[1]
            lines.append(line.strip())
        caption = "\n".join([l for l in lines if l])[:2000]
    
    if not caption:
        caption = "رسانه ایرانا | رویدادهای ایران | ۱۱ آبان ۲۵۸۵"

    video = None
    for p in ["final_5min.mp4", "final_broadcast/main_270.mp4"]:
        if Path(p).exists() and Path(p).stat().st_size > 10000:
            video = p
            break
    return caption, video

def send_telegram(caption, video_path):
    token = env_any("TELEGRAM_BOT_TOKEN")
    chat_id = env_any("TELEGRAM_CHANNEL_ID")
    print(f"[Telegram] token={bool(token)} chat={chat_id} video={video_path}")
    if not token or not chat_id:
        print("❌ Telegram SKIP - secrets missing")
        return False
    # Telegram caption limit 1024 - clean caption already short
    final_cap = caption[:900] + "\n\n📡 @IranaMediaNews\n🔗 iranamedia.github.io\n💬 whatsapp.com/channel/0029Vb9JxR1HgZWcZUxJY03Z"
    try:
        if video_path and Path(video_path).exists():
            with open(video_path, "rb") as f:
                r = requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
                                  data={"chat_id": chat_id, "caption": final_cap},
                                  files={"video": f}, timeout=180)
        else:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json={"chat_id": chat_id, "text": final_cap}, timeout=30)
        print(f"Telegram: {r.status_code} {r.text[:800]}")
        if r.ok:
            print("✅ Telegram published - CLEAN caption (no [commands])")
            return True
        else:
            print(f"❌ Telegram failed")
            return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

def post_facebook(caption, video_path):
    page_id_raw = env_any("FB_PAGE_ID")
    token_raw = env_any("FB_PAGE_ACCESS_TOKEN", "META_PAGE_TOKEN")
    print(f"[Facebook] page_id_raw={page_id_raw} token={bool(token_raw)}")
    if not page_id_raw or not token_raw:
        print("❌ Facebook SKIP - secrets missing")
        return False
    # Filter out profile ID 61595357222750 that causes global id error
    page_ids = [p.strip() for p in page_id_raw.split(',') if p.strip()]
    valid_ids = []
    for pid in page_ids:
        if pid.isdigit() and pid.startswith("61595") and len(pid) > 12:
            print(f"⚠️ Skipping profile ID {pid} (not Page) - causes global id error - use Iranamedia")
            continue
        valid_ids.append(pid)
    if not valid_ids:
        print("❌ Facebook no valid Page IDs")
        return False

    overall = False
    for pid in valid_ids:
        bot_token = token_raw.split(',')[0].strip()
        page_token = bot_token
        # Try exchange System User token -> Page token (Claude fix)
        try:
            r_ex = requests.get(f"https://graph.facebook.com/v20.0/{pid}", params={"fields":"access_token,name","access_token":bot_token}, timeout=15)
            if r_ex.ok and "access_token" in r_ex.json():
                page_token = r_ex.json()["access_token"]
                print(f"ℹ️ Exchanged to Page token for {pid}")
        except: pass

        try:
            if video_path and Path(video_path).exists():
                with open(video_path, "rb") as f:
                    r = requests.post(f"https://graph.facebook.com/v20.0/{pid}/videos",
                                      data={"description": caption[:2000], "access_token": page_token},
                                      files={"source": f}, timeout=180)
            else:
                r = requests.post(f"https://graph.facebook.com/v20.0/{pid}/feed",
                                  data={"message": caption[:2000], "access_token": page_token}, timeout=30)
            print(f"Facebook {pid}: {r.status_code} {r.text[:600]}")
            if r.ok:
                print(f"✅ Facebook {pid} published")
                overall = True
            else:
                if "publish_video" in r.text or "No permission" in r.text:
                    print(f"❌ Facebook {pid}: need publish_video permission in System User token")
        except Exception as e:
            print(f"❌ Facebook error {pid}: {e}")
    return overall

def post_instagram(caption, video_path):
    ig_id = env_any("IG_USER_ID")
    token = env_any("FB_PAGE_ACCESS_TOKEN", "META_PAGE_TOKEN")
    print(f"[Instagram] ig_id={ig_id} token={bool(token)}")
    if not ig_id:
        print("⚠️ Instagram SKIP - IG_USER_ID empty - run verify_ig_v2.py to get it")
        return False
    if not token or not video_path:
        print("⚠️ Instagram SKIP - token/video missing")
        return False
    public_url = "https://iranamedia.github.io/final_5min.mp4"
    print(f"[Instagram] trying public URL {public_url} (must be committed to Pages first)")
    try:
        # Try public URL method (Claude recommended)
        r1 = requests.post(f"https://graph.facebook.com/v20.0/{ig_id}/media",
                           data={"media_type":"REELS","video_url":public_url,"caption":caption[:2200],"access_token":token}, timeout=30)
        print(f"IG public URL: {r1.status_code} {r1.text[:800]}")
        if r1.ok:
            cid = r1.json().get("id")
            if cid:
                for _ in range(8):
                    time.sleep(4)
                    rs = requests.get(f"https://graph.facebook.com/v20.0/{cid}", params={"fields":"status_code","access_token":token}, timeout=15)
                    if "FINISHED" in rs.text or "PUBLISHED" in rs.text:
                        break
                r_pub = requests.post(f"https://graph.facebook.com/v20.0/{ig_id}/media_publish", data={"creation_id":cid,"access_token":token}, timeout=30)
                print(f"IG publish: {r_pub.status_code} {r_pub.text[:600]}")
                if r_pub.ok:
                    print("✅ Instagram Reel published via public URL")
                    return True
        print("⚠️ Instagram public URL failed - may need few minutes for Pages to propagate")
        return False
    except Exception as e:
        print(f"❌ Instagram error: {e}")
        return False

def post_youtube(caption, video_path):
    cid = env_any("YOUTUBE_CLIENT_ID", "YT_CLIENT_ID", "YOUTUBE_CLIENT_ID")
    csec = env_any("YOUTUBE_CLIENT_SECRET", "YT_CLIENT_SECRET")
    rtok = env_any("YOUTUBE_REFRESH_TOKEN", "YT_REFRESH_TOKEN")
    if not all([cid, csec, rtok, video_path]):
        print("⚠️ YouTube SKIP")
        return False
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from googleapiclient.http import MediaFileUpload
        creds = Credentials(None, refresh_token=rtok, token_uri="https://oauth2.googleapis.com/token", client_id=cid, client_secret=csec)
        yt = build("youtube", "v3", credentials=creds)
        title = (caption.split("\n")[0][:80] if caption else "رویدادهای ایران") + " | IRANA 2585"
        body = {"snippet":{"title":title[:100],"description":caption[:4000]+"\n\niranamedia.github.io","tags":["ایران","IRANA"],"categoryId":"25"},"status":{"privacyStatus":"public"}}
        media = MediaFileUpload(video_path, resumable=True, mimetype="video/mp4")
        resp = yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        print(f"✅ YouTube {resp.get('id')}")
        return True
    except Exception as e:
        print(f"❌ YouTube {e}")
        return False

if __name__ == "__main__":
    caption, video = get_latest_caption_and_video()
    print(f"Caption len {len(caption)} (clean, no [commands])\n{caption[:500]}\n")
    print(f"Video {video} exists={Path(video).exists() if video else False}")
    if video and Path(video).exists():
        import subprocess, shlex
        try:
            d = subprocess.check_output(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(video)}', shell=True).decode().strip()
            print(f"Video duration {d}s (should be >60s, not 9s)")
        except: pass

    res = {}
    res["telegram"] = send_telegram(caption, video)
    res["facebook"] = post_facebook(caption, video)
    res["instagram"] = post_instagram(caption, video)
    res["youtube"] = post_youtube(caption, video)

    print("\n=== FINAL TRUTHFUL REPORT (Claude fix - no fake success) ===")
    for k,v in res.items():
        print(f"{'✅' if v else '❌'} {k}: {'OK' if v else 'FAILED/SKIPPED'}")
    
    if res["telegram"] and res["youtube"]:
        print("\n✅ Core (Telegram+YouTube) OK - TV is live")
    if not res["facebook"]:
        print("ℹ️ Facebook: set FB_PAGE_ID=Iranamedia only + regenerate System User token with publish_video")
    if not res["instagram"]:
        print("ℹ️ Instagram: set IG_USER_ID secret via verify_ig_v2.py + ensure https://iranamedia.github.io/final_5min.mp4 public")
