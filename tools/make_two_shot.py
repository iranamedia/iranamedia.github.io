"""ابزار یک‌باره برای نمای دور استودیو و رنگ لباس گوینده‌ها (در GitHub Actions، با rembg).

خروجی‌ها (در پوشه‌ی داده‌شده):
- studio_back.png: پس‌زمینه‌ی مات استودیو، بی گوینده
- presenter_<man|woman>_person.png: نقاب گوینده (هم‌اندازه‌ی عکس اصلی)
- presenter_<man|woman>_clothes.png: نقاب لباس (کت، کراوات، پیراهن) برای رنگ دیگر در هر بخش
tv.py با این‌ها نمای دو گوینده پشت میز را در هر برنامه می‌سازد.
اجرا: python tools/make_two_shot.py <out-dir>"""
import os, sys

import numpy as np
from PIL import Image, ImageFilter
from rembg import remove

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda f: os.path.join(HERE, "assets", f)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "assets")
os.makedirs(OUT, exist_ok=True)
W, H = 1920, 1080

# پس‌زمینه: تنها دو کناره‌ی استودیوی شارلوت (بی خودِ گوینده)، کشیده و مات
src = Image.open(A("presenter_woman.jpg")).convert("RGB")
sw, sh = src.size
left = src.crop((0, 0, int(sw * 0.28), int(sh * 0.74))).resize((W // 2, H))
right = src.crop((int(sw * 0.72), 0, sw, int(sh * 0.74))).resize((W - W // 2, H))
bg = Image.new("RGB", (W, H))
bg.paste(left, (0, 0)); bg.paste(right, (W // 2, 0))
bg.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.72)).save(os.path.join(OUT, "studio_back.png"))

CHIN = 0.47                                         # زیر چانه: لباس؛ بالای آن: چهره و مو
for name in ("man", "woman", "man_serious", "woman_serious"):     # عکس‌های جدی، اگر باشند
    if not os.path.exists(A(f"presenter_{name}.jpg")):
        continue
    who = name.split("_")[0]
    im = Image.open(A(f"presenter_{name}.jpg")).convert("RGB")
    person = remove(im, only_mask=True)
    person.save(os.path.join(OUT, f"presenter_{name}_person.png"))
    p = np.asarray(person).astype(np.float32) / 255
    h, w = p.shape
    rows = np.arange(h)[:, None] / h
    cols = np.arange(w)[None, :] / w
    ycc = np.asarray(im.convert("YCbCr")).astype(np.int16)
    skin = (ycc[..., 2] > 135) & (ycc[..., 2] < 180) & (ycc[..., 1] > 85) & (ycc[..., 1] < 135)
    neck = skin & (abs(cols - 0.5) < 0.07) & (rows < 0.62)      # گردن و یقه‌ی باز: پوست
    mask = p * (rows > CHIN) * (~neck)
    if who == "man":
        mask *= ~skin                                 # کت سرمه‌ای: هرچه پوست نیست
    else:
        v = np.asarray(im.convert("HSV")).astype(np.float32)[..., 2] / 255
        mask *= (v > 0.38)                            # کت روشن و پیراهن؛ موی تیره بیرون
    Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)).save(
        os.path.join(OUT, f"presenter_{name}_clothes.png"))
print("saved to", OUT)
