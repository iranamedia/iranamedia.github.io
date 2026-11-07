"""آزمایش گوینده‌ی گویا (منتشر نمی‌شود).

از خبرنامه‌ی کنونی دو تکه‌ی کوتاه می‌سازد: خبر نخست با صدای شارلوت و خبر دوم با صدای بکتاش،
سپس با SadTalker (متن‌باز، Apache-2.0) چهره‌ی هر گوینده را با صدایش گویا می‌کند،
نوار تیتر ایرانا را رویش می‌گذارد و talking_test.mp4 را می‌سازد. زمان هر گام را هم گزارش می‌کند.
اجرا (در workflow): python3 tools/talking_test.py <SadTalker-dir> <out-dir>"""
import glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SAD, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)
os.environ["TV_DIR"] = OUT

import radio  # noqa: E402
import tv     # noqa: E402

STILL = os.environ.get("STILL", "1") == "1"
MAX_CHARS = int(os.environ.get("MAX_CHARS", "220"))
report = []


def step(name, t0):
    report.append(f"{name}: {time.time() - t0:.0f} ثانیه")
    print(report[-1], flush=True)


def short(it):
    text = it["title"] + ". " + it.get("body", "")
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS].rsplit(" ", 1)[0] + "."


b = json.load(open(os.path.join(HERE, "bulletin", "latest.json"), encoding="utf-8"))
tv.fonts()
parts = [("woman", radio.VOICE_ID_2, b["items"][0], 0), ("man", radio.VOICE_ID, b["items"][1], 1)]
clips = []
for who, voice_id, it, n in parts:
    t0 = time.time()
    mp3, wav = os.path.join(OUT, f"{who}.mp3"), os.path.join(OUT, f"{who}.wav")
    radio.tts(short(it), mp3, voice_id)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "16000", "-ac", "1", wav], check=True)
    step(f"صدای {who} ({tv.dur(wav):.1f} ثانیه گفتار)", t0)

    t0 = time.time()
    photo = tv.studio_photo(who)
    res = os.path.join(OUT, f"sad_{who}")
    cmd = [sys.executable, "inference.py", "--driven_audio", wav, "--source_image", photo, "--result_dir", res,
           "--preprocess", "full", "--size", "256", "--cpu", "--batch_size", "4"]
    if STILL:
        cmd.append("--still")
    subprocess.run(cmd, cwd=SAD, check=True)
    vids = sorted(glob.glob(os.path.join(res, "**", "*.mp4"), recursive=True), key=os.path.getmtime)
    if not vids:
        sys.exit(f"SadTalker no output for {who}")
    step(f"چهره‌ی گویای {who}", t0)

    png = os.path.join(OUT, f"lt_{who}.png")
    count = f"خبر {str(n + 1).translate(tv.FA)} از {str(min(len(b['items']), 5)).translate(tv.FA)}"
    tv.lower_third(b, png, it["title"], count)
    clip = os.path.join(OUT, f"clip_{who}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vids[-1], "-loop", "1", "-i", png, "-i", mp3,
                    "-filter_complex", f"[0:v]scale={tv.W}:{tv.H},setsar=1[v];[v][1:v]overlay=0:0:shortest=1",
                    "-map", "2:a", *tv.ENC, "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-shortest", clip],
                   check=True)
    clips.append(clip)

lst = os.path.join(OUT, "list.txt")
open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
final = os.path.join(OUT, "talking_test.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                "-movflags", "+faststart", final], check=True)
report.append(f"ویدیوی آزمایش: {tv.dur(final):.1f} ثانیه، {os.path.getsize(final) // 1024} KB")
open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8").write("\n".join(report) + "\n")
print("\n".join(report))
