
# persian_corrector.py - تضمین نوشتار فارسی درست برای ایرانامدیا
import re

# نگاشت حروف عربی به فارسی
AR_TO_FA = {
    'ي': 'ی',
    'ك': 'ک',
    'ؤ': 'و',
    'إ': 'ا',
    'أ': 'ا',
    'ة': 'ه',
}

def normalize_persian(text):
    """تبدیل حروف عربی به فارسی و اصلاح نیم‌فاصله"""
    for ar, fa in AR_TO_FA.items():
        text = text.replace(ar, fa)
    
    # اصلاح نیم‌فاصله‌های مهم - می‌شود، نمی‌شود، etc
    text = re.sub(r'\s+می\s+شود', ' می‌شود', text)
    text = re.sub(r'\s+می\s+کند', ' می‌کند', text)
    text = re.sub(r'\s+می\s+شود', ' می‌شود', text)
    text = re.sub(r'\bها\s+ی\b', 'های', text)
    text = re.sub(r'\s+ترین\b', '‌ترین', text)
    text = re.sub(r'\s+تر\b', '‌تر', text)
    
    # حذف فاصله‌های اضافی
    text = re.sub(r'\s{2,}', ' ', text)
    
    # اعداد فارسی به انگلیسی برای تاریخ؟ نگه می‌داریم فارسی
    return text.strip()

def persian_spellcheck_prompt(text):
    """
    پرامپت برای OpenAI که نوشتار را کاملا درست می‌کند
    """
    return f"""
لطفا متن زیر را به فارسی معیار و درست بازنویسی کن - بدون غلط املایی، بدون حروف عربی:

قوانین:
1. ی و ک فارسی: ی ک نه ي ك
2. نیم‌فاصله را رعایت کن: می‌شود نه می شود، کتاب‌ها نه کتاب ها، ایرانیان نه ایرانیان
3. نشانه‌گذاری درست: ویرگول ، نقطه .
4. لحن: رسمی خبری ایرانامدیا، بی‌طرف، کوتاه و دقیق
5. هیچ علامت جمهوری اسلامی اضافه نکن
6. فقط متن درست شده را برگردان

متن:
{text}
"""

# تست
samples = [
    "واكنش آسوشيتدپرس به تحولات تهران",
    "گزارش رويترز از وضعيت حقوق بشر در ايران",
    "پیام شهبانو فرح پهلوی به مناسبت روز فرهنگی"
]

for s in samples:
    print(f"قبل: {s}")
    print(f"بعد: {normalize_persian(s)}\n")

from pathlib import Path
Path("/mnt/data/persian_corrector.py").write_text(code, encoding="utf-8")
print("persian_corrector.py created")
