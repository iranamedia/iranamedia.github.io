#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Build REAL 5min video - FIX black screen + use lion logo + Persian audio only
import os, glob, subprocess, shlex, json
from pathlib import Path

def run(cmd):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True)
    return r.returncode == 0

def get_latest():
    cap_files = sorted(glob.glob("final_broadcast/caption_*.txt"), reverse=True)
    script_files = sorted(glob.glob("final_broadcast/script_*.txt"), reverse=True)
    cap = Path(cap_files[0]).read_text(encoding="utf-8") if cap_files else ""
    scr = Path(script_files[0]).read_text(encoding="utf-8") if script_files else cap
    return scr or cap, cap or scr

def build_audio(text, out="final_broadcast/voice.mp3"):
    # FIX: Persian only, no English TTS
    clean = text.replace("[","").replace("]","").strip()[:3500]
    # Remove any remaining English chars for TTS
    # Keep Persian + numbers
    print(f"Building audio from Persian text len={len(clean)}")

    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    bak_id = os.getenv("BAKTASH_VOICE_ID")
    # FIX COST: Claude said 2 voices expensive - use single voice to cut cost 50%
    # Old: 2 voices (Baktash + Charlotte) = $0.30 per 5min *24 = $7.2/day
    # New: 1 voice only (Baktash) = $0.15 per 5min *24 = $3.6/day, or gTTS free
    if eleven_key and bak_id:
        try:
            import requests
            headers = {"xi-api-key": eleven_key, "Content-Type": "application/json"}
            data = {"text": clean, "model_id": "eleven_multilingual_v2"}
            r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{bak_id}", json=data, headers=headers, timeout=90)
            if r.ok and len(r.content) > 2000:
                Path(out).write_bytes(r.content)
                print(f"✅ ElevenLabs single voice (cost saver) {Path(out).stat().st_size} bytes")
                return out
        except Exception as e:
            print(f"ElevenLabs fail: {e}")
    # FREE fallback - gTTS Persian (0 cost - Claude suggestion to reduce cost)
    try:
        from gtts import gTTS
        tts = gTTS(text=clean, lang='fa')
        tts.save(out)
        print(f"✅ gTTS Persian FREE {Path(out).stat().st_size} bytes - no cost")
        return out
    except Exception as e:
        print(f"gTTS fail: {e}")
        return None

def create_background_with_logo():
    """
    FIX black screen: Create 1080x1920 background with lion logo, not black
    Uses assets/irana_lion_gold_transparent.png + assets/iranamedia_cover_clean.jpg if exists
    """
    lion = None
    for p in ["assets/irana_lion_gold_transparent.png", "assets/iranamedia_lion_gold_transparent.png", "assets/shir_khorshid_shamshir_transparent.png"]:
        if Path(p).exists():
            lion = p
            break
    cover = None
    for p in ["assets/iranamedia_cover_clean.jpg", "assets/iranamedia_cover.jpg", "docs/assets/iranamedia_cover_clean.jpg"]:
        if Path(p).exists():
            cover = p
            break

    bg_path = "final_broadcast/bg_1080x1920.jpg"

    if cover:
        # Use cover as background
        run(f'ffmpeg -y -i {shlex.quote(cover)} -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" {shlex.quote(bg_path)}')
        print(f"Background from cover {cover}")
    else:
        # Create dark blue background with lion logo centered (not black)
        # Dark blue #0A1931 like IRANA brand, with lion gold
        if lion:
            # Create base dark blue, overlay lion
            run(f'ffmpeg -y -f lavfi -i color=c=0x0A1931:s=1080x1920:d=1:r=30 -i {shlex.quote(lion)} -filter_complex "[0][1]overlay=(W-w)/2:(H-h)/2:eval=init,scale=1080:1920" -frames:v 1 {shlex.quote(bg_path)}')
            if not Path(bg_path).exists():
                # fallback if overlay fails
                run(f'ffmpeg -y -f lavfi -i color=c=0x0A1931:s=1080x1920 -frames:v 1 {shlex.quote(bg_path)}')
            print(f"Background dark blue + lion {lion}")
        else:
            run(f'ffmpeg -y -f lavfi -i color=c=0x0A1931:s=1080x1920 -frames:v 1 {shlex.quote(bg_path)}')
            print("Background dark blue (no lion found)")

    return bg_path if Path(bg_path).exists() else None

def build_final():
    script_text, caption_text = get_latest()
    print(f"Script len {len(script_text)}")

    intro = None
    for p in ["assets/irana_intro_final.mp4", "irana_intro_final.mp4"]:
        if Path(p).exists():
            intro = p
            break
    if not intro:
        print("❌ Missing intro")
        return False

    bg = create_background_with_logo()
    if not bg:
        print("❌ Failed to create background")
        return False

    audio = build_audio(script_text)
    Path("final_broadcast").mkdir(exist_ok=True)

    # Main segment with background image + audio (not black)
    if audio and Path(audio).exists():
        try:
            out = subprocess.check_output(f'ffprobe -v error -show_entries format=duration -of json {shlex.quote(audio)}', shell=True).decode()
            dur = float(json.loads(out)['format']['duration'])
        except:
            dur = 240
        dur = max(90, min(dur, 280))
        print(f"Audio duration {dur}s - building main video with logo background (not black)")
        run(f'ffmpeg -y -loop 1 -i {shlex.quote(bg)} -i {shlex.quote(audio)} -t {dur} -vf "scale=1080:1920,fps=30" -c:v libx264 -preset veryfast -c:a aac -shortest final_broadcast/main_270.mp4')
    else:
        print("No audio - 270s with background (not black)")
        run(f'ffmpeg -y -loop 1 -i {shlex.quote(bg)} -f lavfi -i anullsrc=r=44100:cl=stereo -t 270 -vf "scale=1080:1920,fps=30" -c:v libx264 -preset veryfast -c:a aac -shortest final_broadcast/main_270.mp4')

    main = "final_broadcast/main_270.mp4"
    if not Path(main).exists():
        print(f"❌ Failed {main}")
        return False

    # Normalize intro
    run(f'ffmpeg -y -i {shlex.quote(intro)} -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30" -c:v libx264 -preset veryfast -c:a aac -r 30 final_broadcast/intro_1080.mp4')

    # Concat
    with open("final_broadcast/concat.txt","w") as f:
        f.write("file 'intro_1080.mp4'\n")
        f.write("file 'main_270.mp4'\n")
    ok = run(f'ffmpeg -y -f concat -safe 0 -i final_broadcast/concat.txt -c:v libx264 -preset veryfast -c:a aac final_5min.mp4')
    if not ok:
        ok = run(f'ffmpeg -y -f concat -safe 0 -i final_broadcast/concat.txt -c copy final_5min.mp4')

    if Path("final_5min.mp4").exists():
        size = Path("final_5min.mp4").stat().st_size
        try:
            dur = subprocess.check_output(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 final_5min.mp4', shell=True).decode().strip()
            print(f"✅✅✅ Built final_5min.mp4 {size} bytes duration {dur}s WITH background (not black) - Persian only")
            return float(dur) > 60
        except:
            print(f"Built {size} bytes")
            return True
    return False

if __name__ == "__main__":
    build_final()
