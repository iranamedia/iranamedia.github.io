"""یک بخش گوینده‌دار تلویزیون ایرانا را گویا می‌کند (SadTalker، روی پردازنده).
هر بخش در یک رایانه‌ی جداگانه‌ی GitHub ساخته می‌شود تا همه با هم و به موقع آماده شوند.

ورودی: _site/latest.mp3 و _site/talk_plan.json (از tv.py --plan)
خروجی: _talk/talk_<i>.mp4 (۱۹۲۰×۱۰۸۰، بی‌صدا؛ صدای اصلی از رادیو است)
اجرا: python tools/talk_shot.py <shot-index> <SadTalker-dir>"""
import glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ.setdefault("TV_DIR", os.path.join(HERE, "_tvwork"))
import tv  # noqa: E402

i, sad = int(sys.argv[1]), os.path.abspath(sys.argv[2])
shot = next(s for s in json.load(open(os.path.join(tv.SITE, "talk_plan.json"), encoding="utf-8")) if s["i"] == i)
work = os.path.join(tv.OUT, f"talk_{i:02d}")
os.makedirs(work, exist_ok=True)
os.makedirs(tv.TALK_DIR, exist_ok=True)
t0 = time.time()

wav = os.path.join(work, "voice.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{shot.get('talk_start', shot['start']):.3f}", "-t", f"{shot['on_cam']:.3f}",
                "-i", os.path.join(tv.SITE, "latest.mp3"), "-ar", "16000", "-ac", "1", wav], check=True)
photo = tv.studio_photo(shot["voice"], shot.get("mood", ""))
cmd = [sys.executable, "inference.py", "--driven_audio", wav, "--source_image", photo, "--result_dir", work,
       "--preprocess", "full", "--size", "256", "--cpu", "--batch_size", "4", "--still"]
subprocess.run(cmd, cwd=sad, check=True)
vids = [v for v in sorted(glob.glob(os.path.join(work, "*.mp4")), key=os.path.getmtime)]
if not vids:
    sys.exit(f"shot {i}: SadTalker no output")
out = os.path.join(tv.TALK_DIR, f"talk_{i:02d}.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vids[-1], "-vf", f"fps=25,scale={tv.W}:{tv.H},setsar=1",
                *tv.ENC, "-an", out], check=True)
print(f"shot {i} ({shot['voice']}, {shot['on_cam']:.1f}s): {time.time() - t0:.0f} ثانیه → {out}", flush=True)
