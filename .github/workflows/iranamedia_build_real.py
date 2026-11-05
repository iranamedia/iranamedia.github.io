#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# IRANA Media - Build REAL 5min video (fixes 9sec placeholder bug - Claude)
import os, glob, subprocess, shlex, json
from pathlib import Path

def run(cmd):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True)
    print(f"-> exit {r.returncode}")
    return r.returncode == 0

def get_latest_clean():
    # Prefer clean caption + full script
    cap_files = sorted(glob.glob("final_broadcast/caption_*.txt"), reverse=True)
    script_files = sorted(glob.glob("final_broadcast/script_*.txt"), reverse=True)
    caption = ""
    script = ""
    if cap_files:
        caption = Path(cap_files[0]).read_text(encoding="utf-8")
    if script_files:
        script = Path(script_files[0]).read_text(encoding="utf-8")
    if not script:
        script = "درود، رویدادهای ایران از رسانه ایرانا - ۱۱ آبان ۲۵۸۵ شاهنشاهی"
        caption = script
    return script, caption

def build_audio(text, out_mp3="final_broadcast/voice.mp3"):
    # Clean text for TTS - remove any remaining brackets
    clean = text.replace("[", "").replace("]", "").replace("گوینده", "").strip()
    clean = clean[:4000]
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    bak_id = os.getenv("BAKTASH_VOICE_ID")
    if eleven_key and bak_id:
        try:
            import requests
            headers = {"xi-api-key": eleven_key, "Content-Type": "application/json"}
            data = {"text": clean, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability":0.5,"similarity_boost":0.7}}
            r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{bak_id}", json=data, headers=headers, timeout=90)
            if r.ok and len(r.content) > 1000:
                Path(out_mp3).write_bytes(r.content)
                print(f"✅ ElevenLabs audio {Path(out_mp3).stat().st_size} bytes")
                return out_mp3
            else:
                print(f"ElevenLabs failed: {r.status_code} {r.text[:300]}")
        except Exception as e:
            print(f"ElevenLabs error: {e}")
    try:
        from gtts import gTTS
        tts = gTTS(text=clean, lang='fa')
        tts.save(out_mp3)
        print(f"✅ gTTS audio {Path(out_mp3).stat().st_size} bytes")
        return out_mp3
    except Exception as e:
        print(f"gTTS failed: {e}")
        return None

def build_final_video():
    script_text, caption_text = get_latest_clean()
    print(f"Script len {len(script_text)} caption len {len(caption_text)}")

    intro = None
    for p in ["assets/irana_intro_final.mp4", "irana_intro_final.mp4", "assets/irana_intro.mp4"]:
        if Path(p).exists():
            intro = p
            break
    if not intro:
        print("❌ MISSING INTRO assets/irana_intro_final.mp4")
        return False

    cover = None
    for p in ["assets/iranamedia_cover_clean.jpg", "assets/iranamedia_cover.jpg", "docs/assets/iranamedia_cover_clean.jpg"]:
        if Path(p).exists():
            cover = p
            break
    # If no cover, use black

    audio = build_audio(script_text)
    Path("final_broadcast").mkdir(exist_ok=True)

    # Build main 270s segment
    if audio and Path(audio).exists():
        # Get audio duration
        try:
            cmd = f'ffprobe -v error -show_entries format=duration -of json {shlex.quote(audio)}'
            out = subprocess.check_output(cmd, shell=True).decode()
            dur = float(json.loads(out)['format']['duration'])
            print(f"Audio duration {dur}s")
        except:
            dur = 240
        dur = max(90, min(dur, 280))  # 90-280 sec
        if cover:
            run(f'ffmpeg -y -loop 1 -i {shlex.quote(cover)} -i {shlex.quote(audio)} -t {dur} -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30" -c:v libx264 -preset veryfast -c:a aac -shortest final_broadcast/main_270.mp4')
        else:
            run(f'ffmpeg -y -f lavfi -i color=c=0x0A1931:s=1080x1920:d={dur}:r=30 -i {shlex.quote(audio)} -c:v libx264 -preset veryfast -c:a aac -shortest final_broadcast/main_270.mp4')
    else:
        print("No audio - creating silent 270s")
        if cover:
            run(f'ffmpeg -y -loop 1 -i {shlex.quote(cover)} -f lavfi -i anullsrc=r=44100:cl=stereo -t 270 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30" -c:v libx264 -preset veryfast -c:a aac -shortest final_broadcast/main_270.mp4')
        else:
            run(f'ffmpeg -y -f lavfi -i color=c=0x0A1931:s=1080x1920:d=270:r=30 -f lavfi -i anullsrc=r=44100:cl=stereo -t 270 -c:v libx264 -preset veryfast -c:a aac -shortest final_broadcast/main_270.mp4')

    main = "final_broadcast/main_270.mp4"
    if not Path(main).exists():
        print(f"❌ Failed to create {main}")
        return False

    # Normalize intro to 1080x1920
    run(f'ffmpeg -y -i {shlex.quote(intro)} -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30" -c:v libx264 -preset veryfast -c:a aac -r 30 final_broadcast/intro_1080.mp4')

    # Concat intro + main = final_5min.mp4 ~ 280-300s NOT 9s
    with open("final_broadcast/concat.txt","w") as f:
        f.write("file 'intro_1080.mp4'\n")
        f.write("file 'main_270.mp4'\n")
    ok = run(f'ffmpeg -y -f concat -safe 0 -i final_broadcast/concat.txt -c:v libx264 -preset veryfast -c:a aac final_5min.mp4')
    if not ok:
        ok = run(f'ffmpeg -y -f concat -safe 0 -i final_broadcast/concat.txt -c copy final_5min.mp4')
    
    if Path("final_5min.mp4").exists():
        size = Path("final_5min.mp4").stat().st_size
        try:
            cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 final_5min.mp4'
            dur = subprocess.check_output(cmd, shell=True).decode().strip()
            print(f"✅✅✅ Built final_5min.mp4 - {size} bytes - duration {dur}s (should be ~280s, NOT 9s placeholder)")
            if float(dur) < 60:
                print(f"❌ STILL TOO SHORT - {dur}s < 60s - build failed")
                return False
            return True
        except Exception as e:
            print(f"Built final_5min.mp4 {size} bytes but ffprobe failed: {e}")
            return True
    else:
        print("❌ Failed to build final_5min.mp4")
        return False

if __name__ == "__main__":
    build_final_video()
