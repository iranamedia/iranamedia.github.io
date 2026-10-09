"""رادیو ایرانا: خبرنامه‌ی تازه را با صدای ElevenLabs می‌خواند و به کانال تلگرام می‌فرستد."""
import json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error, uuid


def fail(msg):
    """خطا را به‌صورت هشدار GitHub نشان بده تا در خلاصه‌ی اجرا دیده شود؛ رازها را پنهان کن."""
    for secret in (API_KEY, BOT_TOKEN):
        if secret: msg = msg.replace(secret, "***")
    print(f"::error::{msg}", flush=True)
    sys.exit(1)

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
VOICE_ID = os.environ.get("VOICE_ID", "g8OwRTuNvpJKpiVarLb6")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL", "@IranaMediaNews")
MODELS = [m for m in os.environ.get("TTS_MODELS", "eleven_v3,eleven_multilingual_v2").split(",") if m]
MAX_CHARS = 2500


HEADLINES = 3
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def opening(b):
    """سرآغاز: نام رسانه، ساعت و سه تیتر مهم؛ روی زیرآهنگ خوانده می‌شود."""
    heads = [it["title"].rstrip(".") for it in b["items"][:HEADLINES]]
    return f"اینجا رسانه ایرانا است. {b['stamp']}. تیترهای مهم: " + ". ".join(heads) + "."


def script(b):
    """متن گفتاری خبرها، پس از سرآغاز."""
    parts = [f"{it['title'].rstrip('.')}. {it['body']}" for it in b["items"]]
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
    fail(f"ElevenLabs failed: {last}")


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())


def norm(src, out):
    """همه‌ی تکه‌ها یک‌دست: ۴۴۱۰۰ هرتز، دوکاناله."""
    ff("-i", src, "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", out)


def over_bed(voice, out, lead=2.0, tail=1.5):
    """صدای تیترها روی زیرآهنگ: آهنگ با بلندی آغاز می‌شود، زیر صدا پایین می‌رود و در پایان محو می‌شود."""
    bed = os.path.join(ASSETS, "bed.mp3")
    if not os.path.exists(bed):
        return norm(voice, out)
    total = lead + dur(voice) + tail
    ff("-i", voice, "-stream_loop", "-1", "-i", bed, "-filter_complex",
       f"[0:a]aresample=44100,aformat=channel_layouts=stereo,adelay={int(lead*1000)}:all=1,apad,asplit=2[v][sc];"
       f"[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.55[m];"
       f"[m][sc]sidechaincompress=threshold=0.02:ratio=10:attack=40:release=600[duck];"
       f"[v][duck]amix=inputs=2:duration=longest:normalize=0,atrim=0:{total:.2f},"
       f"afade=t=in:d=0.4,afade=t=out:st={total-tail:.2f}:d={tail}",
       "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", out)


def join(files, out):
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in files: f.write(f"file '{p}'\n")
    ff("-f", "concat", "-safe", "0", "-i", lst, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
       "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "128k", "-metadata", "title=رسانه ایرانا", out)


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
        fail(f"Telegram failed: {e.code} {e.read()[:300]!r}")
    if not res.get("ok"): fail(f"Telegram failed: {res}")


def main(src="bulletin/latest.json", dry=False):
    b = json.load(open(src, encoding="utf-8"))
    if not b.get("items"): print("no items; nothing to send"); return
    head, parts = opening(b), chunks(script(b))
    if dry:
        print("HEAD |", head)
        for c in parts: print(len(c), "|", c[:80].replace("\n", " "), "…")
        print(caption(b)); return
    if not API_KEY or not BOT_TOKEN:
        fail("missing secret: " + ", ".join(n for n, v in (("ELEVENLABS_API_KEY", API_KEY), ("TELEGRAM_BOT_TOKEN", BOT_TOKEN)) if not v))
    with tempfile.TemporaryDirectory() as d:
        P = lambda n: os.path.join(d, n)
        print("tts head", tts(head, P("head.mp3")))
        over_bed(P("head.mp3"), P("00_head.wav"))
        seq = [P("00_head.wav")]
        sting = os.path.join(ASSETS, "sting.mp3")
        if os.path.exists(sting):
            norm(sting, P("01_sting.wav")); seq.append(P("01_sting.wav"))
        for n, c in enumerate(parts):
            print("tts", n, len(c), tts(c, P(f"b{n:02d}.mp3")))
            norm(P(f"b{n:02d}.mp3"), P(f"10_{n:02d}.wav")); seq.append(P(f"10_{n:02d}.wav"))
        out = P("irana.mp3"); join(seq, out)
        send(out, caption(b), f"رسانه ایرانا · {b['stamp']}")
    print("sent")


if __name__ == "__main__":
    main(*(a for a in sys.argv[1:] if a != "--dry"), dry="--dry" in sys.argv)
