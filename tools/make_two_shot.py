"""نمای دور استودیو: بکتاش و شارلوت کنار هم پشت میز خبر (یک بار ساخته می‌شود، assets/studio_two.png).

گوینده‌ها با rembg از عکس‌هایشان بریده می‌شوند، روی پس‌زمینه‌ی مات استودیو کنار هم می‌نشینند
و یک میز خبر با نشان ایرانا جلوی آن‌ها می‌آید. نوشته‌های چاپ‌شده در پایین عکس‌ها زیر میز پنهان است.
اجرا (در GitHub Actions): python tools/make_two_shot.py <out.png>"""
import os, sys

from PIL import Image, ImageDraw, ImageFilter
from rembg import remove

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda f: os.path.join(HERE, "assets", f)
W, H = 1920, 1080
GOLD = (224, 180, 82)


def cutout(path, keep=0.74):
    im = Image.open(path).convert("RGB")
    im = im.crop((0, 0, im.width, int(im.height * keep)))      # نوار نوشته‌ی پایین عکس بیرون
    cut = remove(im)                                              # RGBA: تنها گوینده
    return cut.crop(cut.getbbox())


# پس‌زمینه: استودیوی شارلوت، بسیار مات و کمی تیره (مانند نمای دور با ژرفای میدان کم)
# (فقط دو کناره‌ی عکس، بی خودِ گوینده، کشیده و مات می‌شوند)
src = Image.open(A("presenter_woman.jpg")).convert("RGB")
sw, sh = src.size
left = src.crop((0, 0, int(sw * 0.28), int(sh * 0.74))).resize((W // 2, H))
right = src.crop((int(sw * 0.72), 0, sw, int(sh * 0.74))).resize((W - W // 2, H))
bg = Image.new("RGB", (W, H))
bg.paste(left, (0, 0)); bg.paste(right, (W // 2, 0))
bg = bg.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.72)).convert("RGBA")

man, woman = cutout(A("presenter_man.jpg")), cutout(A("presenter_woman.jpg"))
target_h = int(H * 0.58)                                          # گوینده‌ها از کمر به بالا، دورتر
desk_top = int(H * 0.72)
for img, cx in ((man, int(W * 0.34)), (woman, int(W * 0.66))):
    s = target_h / img.height
    img = img.resize((int(img.width * s), target_h), Image.LANCZOS)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(img.getchannel("A").point(lambda a: int(a * 0.45)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    x, y = cx - img.width // 2, desk_top + 40 - img.height
    bg.alpha_composite(shadow, (x + 12, y + 10))
    bg.alpha_composite(img, (x, y))

# میز خبر: رویه‌ی براق تیره با لبه‌ی زرین و نشان ایرانا
d = ImageDraw.Draw(bg)
d.polygon([(int(W * 0.06), desk_top), (int(W * 0.94), desk_top), (W, H), (0, H)], fill=(14, 26, 58, 255))
d.rectangle([int(W * 0.06), desk_top, int(W * 0.94), desk_top + 10], fill=GOLD + (255,))
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(glow).rectangle([int(W * 0.06), desk_top + 10, int(W * 0.94), desk_top + 60], fill=(255, 255, 255, 22))
bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
logo_p = A("irana_logo_transparent.png")
if os.path.exists(logo_p):
    lg = Image.open(logo_p).convert("RGBA").resize((220, 220), Image.LANCZOS)
    bg.alpha_composite(lg, ((W - 220) // 2, desk_top + 50))

out = sys.argv[1] if len(sys.argv) > 1 else A("studio_two.png")
bg.convert("RGB").save(out)
print("saved", out)

# --- نقاب لباس هر گوینده (برای رنگ دیگر کت، کراوات و پیراهن در هر بخش) ---
import numpy as np  # noqa: E402

CHIN = {"man": 0.47, "woman": 0.47}                # زیر چانه: لباس؛ بالای آن: چهره و مو
for who in ("man", "woman"):
    im = Image.open(A(f"presenter_{who}.jpg")).convert("RGB")
    person = np.asarray(remove(im, only_mask=True)).astype(np.float32) / 255
    ycc = np.asarray(im.convert("YCbCr")).astype(np.int16)
    cb, cr = ycc[..., 1], ycc[..., 2]
    skin = (cr > 135) & (cr < 180) & (cb > 85) & (cb < 135)
    rows = np.arange(im.height)[:, None] / im.height
    mask = person * (~skin) * (rows > CHIN[who])
    m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))
    dest = os.path.join(os.path.dirname(out), f"presenter_{who}_clothes.png")
    m.save(dest)
    print("saved", dest)
