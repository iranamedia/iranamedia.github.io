"""رادیو ایرانا: خبرنامه‌ی تازه را با صدای ElevenLabs می‌خواند و به کانال تلگرام می‌فرستد."""
import json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error, uuid

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
VOICE_ID = os.environ.get("VOICE_ID", "g8OwRTuNvpJKpiVarLb6")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "@IranaMediaNews")
MODELS = [m for m in os.environ.get("TTS_MODELS", "eleven_v3,eleven_multilingual_v2").split(",") if m]
MAX_CHARS = 2500


def script(b):
    """متن گفتاری: آغاز، خبرها، پایان."""
    parts = [f"اینجا رسانه ایرانا است؛ تازه‌ترین رویدادهای ایران. {b['stamp']}."]
    for it in b["items"]:
        parts.append(f"{it['title'].rstrip('.')}. {it['body']}")
    parts.append("رسانه ایرانا؛ تازه‌ترین خبرها را سر ساعت آینده بشنوید.")
    return parts


def chunks(parts):
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + len(p) + 1 > MAX_CHARS:
            out.append(cur); cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur: out.append(cur)
    return out


def tts(text, path):
    last = None
    for model in MODELS:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128",
            data=json.dumps({"text": text, "model_id": model}).encode(),
            headers={"xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as f:
                    f.write(r.read())
                return model
            except urllib.error.HTTPError as e:
                last = f"{model}: {e.code} {e.read()[:300]!r}"
                if e.code in (400, 422): break          # این مدل این متن را نمی‌پذیرد؛ مدل بعدی
                time.sleep(5 * (attempt + 1))
    sys.exit(f"ElevenLabs failed: {last}")


def join(files, out):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in files: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-b:a", "128k", "-metadata", "title=رسانه ایرانا", out], check=True)


def caption(b):
    head = f"🎙 رسانه ایرانا\n{b['stamp']}\n\n"
    lines, size = [], len(head) + 40
    for it in b["items"]:
        l = "▪️ " + it["title"]
        if size + len(l) + 1 > 1000: break
        lines.append(l); size += len(l) + 1
    return head + "\n".join(lines) + f"\n\n{CHANNEL}"


def send(path, cap, title):
    boundary = uuid.uuid4().hex
    fields = {"chat_id": CHANNEL, "caption": cap, "title": title, "performer": "رسانه ایرانا"}
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"irana.mp3\"\r\n"
             "Content-Type: audio/mpeg\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Telegram failed: {e.code} {e.read()[:300]!r}")
    if not res.get("ok"): sys.exit(f"Telegram failed: {res}")


def main(src="bulletin/latest.json", dry=False):
    b = json.load(open(src, encoding="utf-8"))
    if not b.get("items"): print("no items; nothing to send"); return
    parts = chunks(script(b))
    if dry:
        for c in parts: print(len(c), "|", c[:80].replace("\n", " "), "…")
        print(caption(b)); return
    if not API_KEY or not BOT_TOKEN: sys.exit("missing ELEVENLABS_API_KEY or TELEGRAM_BOT_TOKEN secret")
    with tempfile.TemporaryDirectory() as d:
        files = []
        for n, c in enumerate(parts):
            p = os.path.join(d, f"{n:02d}.mp3"); print("tts", n, len(c), tts(c, p)); files.append(p)
        out = os.path.join(d, "irana.mp3"); join(files, out)
        send(out, caption(b), f"رسانه ایرانا · {b['stamp']}")
    print("sent")


if __name__ == "__main__":
    main(*(a for a in sys.argv[1:] if a != "--dry"), dry="--dry" in sys.argv)
