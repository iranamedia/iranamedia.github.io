"""رادیو ایرانا: خبرنامه‌ی تازه را با صدای ElevenLabs می‌خواند و به کانال تلگرام می‌فرستد."""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error, uuid


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


# ---- خواندن درست شماره‌ها: پیش از گفتار، شماره‌ها به واژه برمی‌گردند ----
import re

_ONES = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه", "ده", "یازده", "دوازده", "سیزده",
         "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
_TENS = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
_HUNDS = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]
_BIG = ["", "هزار", "میلیون", "میلیارد", "تریلیون"]
_MONTHS = "فروردین|اردیبهشت|خرداد|تیر|امرداد|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند"
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _under1000(n):
    parts = []
    if n >= 100: parts.append(_HUNDS[n // 100]); n %= 100
    if n >= 20: parts.append(_TENS[n // 10]); n %= 10
    if n: parts.append(_ONES[n])
    return " و ".join(parts)


def words(n):
    if n == 0: return "صفر"
    groups, i = [], 0
    while n and i < len(_BIG):
        n, g = divmod(n, 1000)
        if g: groups.append(_under1000(g) + (" " + _BIG[i] if _BIG[i] else ""))
        i += 1
    return " و ".join(reversed(groups))


def ordinal(n):
    w = words(n)
    if w.endswith("سه"): return w[:-2] + "سوم"
    if w.endswith("ی"): return w + "‌ام"
    return w + "م"


# نام‌هایی که گوینده باید به شیوه‌ی درست بخواند (نوشتار آوایی، فقط برای صدا)
SAY = {
    "هرانا": "هْرانا",   # Hrana، نه Harana
    "چاپ[\u200c ]?کنندگان": "چاپ کُنَندِگان",   # Chaapkonandegaan
    "چاپ[\u200c ]?کننده": "چاپ کُنَنده",
}


def speakable(text):
    """شماره‌ها را برای گوینده به واژه برمی‌گرداند؛ روز ماه به‌صورت ترتیبی (پانزدهم مهر)."""
    t = text.translate(_DIGITS)
    for k, v in SAY.items():
        t = re.sub(r"(?<![\w\u200c])" + k + r"(?![\w\u200c])", v, t)
    t = re.sub(r"(?<=\d)[٬,](?=\d{3})", "", t)
    t = re.sub(r"(\d+)\s+(" + _MONTHS + r")", lambda m: ordinal(int(m.group(1))) + " " + m.group(2), t)
    t = re.sub(r"(\d+)[.٫/](\d+)", lambda m: words(int(m.group(1))) + " ممیز " + words(int(m.group(2))), t)
    t = re.sub(r"(\d+)\s*[%٪]", lambda m: words(int(m.group(1))) + " درصد", t)
    t = re.sub(r"\d+", lambda m: words(int(m.group(0))), t)
    return t


HEADLINES = 3
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def opening(b):
    """سرآغاز: نام رسانه و ساعت، سپس سه تیتر نخست یکراست پشت هم؛ روی زیرآهنگ خوانده می‌شود."""
    heads = [it["title"].rstrip(".") for it in b["items"][:HEADLINES]]
    return f"اینجا رسانه ایرانا است. {b['stamp']}.\n\n" + ".\n\n".join(heads) + "."


def script(b):
    """متن گفتاری خبرها، پس از سرآغاز."""
    parts = [it["body"] for it in b["items"]]          # بی‌تیتر: تیترها در سرآغاز آمده‌اند
    parts.append("رسانه ایرانا؛ تازه‌ترین رویدادها را سر ساعت آینده بشنوید.")
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


# نزدیک‌ترین آوا به صدای اصلی گوینده: شباهت بیشینه، پایداری میانه، بی‌سبک‌سازی.
SIMILARITY = float(os.environ.get("VOICE_SIMILARITY", "1.0"))
STABILITY = float(os.environ.get("VOICE_STABILITY", "0.5"))


def settings_for(model):
    if model == "eleven_v3":          # v3 فقط پایداری 0، 0.5 یا 1 را می‌پذیرد
        return {"stability": min((0.0, 0.5, 1.0), key=lambda v: abs(v - STABILITY))}
    return {"stability": STABILITY, "similarity_boost": SIMILARITY, "style": 0.0, "use_speaker_boost": True}


def tts(text, path):
    text = speakable(text)
    last = None
    for model in MODELS:
        for vs in (settings_for(model), None):   # اگر تنظیم‌ها پذیرفته نشد، بی آن‌ها
            body = {"text": text, "model_id": model}
            if vs: body["voice_settings"] = vs
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128",
                data=json.dumps(body).encode(),
                headers={"xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
            bad = False
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as f:
                        f.write(r.read())
                    return model
                except urllib.error.HTTPError as e:
                    last = f"{model}: {e.code} {e.read()[:300]!r}"
                    if e.code in (400, 422): bad = True; break
                    time.sleep(5 * (attempt + 1))
            if not bad: break
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
    head = f"🎙 {b['stamp']}\n\n"
    lines, size = [], len(head) + 40
    for it in b["items"]:
        l = "▪️ " + it["title"]
        if size + len(l) + 1 > 1000: break
        lines.append(l); size += len(l) + 1
    return head + "\n".join(lines) + f"\n\n{CHANNEL}"


def send(path, cap, stamp):
    boundary = uuid.uuid4().hex
    fields = {"chat_id": CHANNEL, "caption": cap, "title": "رسانه ایرانا", "performer": stamp}
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
        if os.environ.get("SAVE_DIR"):                  # برای اپ ایرانا
            os.makedirs(os.environ["SAVE_DIR"], exist_ok=True)
            shutil.copy(out, os.path.join(os.environ["SAVE_DIR"], "latest.mp3"))
        send(out, caption(b), b["stamp"])
    print("sent")


if __name__ == "__main__":
    main(*(a for a in sys.argv[1:] if a != "--dry"), dry="--dry" in sys.argv)
