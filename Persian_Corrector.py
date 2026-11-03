# persian_corrector.py - تضمین نوشتار فارسی درست برای ایرانامدیا
import re

AR_TO_FA = {
    'ي': 'ی',
    'ك': 'ک',
    'ؤ': 'و',
    'إ': 'ا',
    'أ': 'ا',
    'ة': 'ه',
}

def normalize_persian(text):
    if not text:
        return ""
    for ar, fa in AR_TO_FA.items():
        text = text.replace(ar, fa)
    text = re.sub(r'\s+می\s+شود', ' می‌شود', text)
    text = re.sub(r'\s+می\s+کند', ' می‌کند', text)
    text = re.sub(r'\s+می\s+شوند', ' می‌شوند', text)
    text = re.sub(r'\s+ها\s+', '‌ها ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def correct_persian(text):
    """alias برای سازگاری"""
    return normalize_persian(text)

# واژه‌نامه ایرانامدیا - بدون علامت جمهوری اسلامی
GLOSSARY = {
    "شهبانو": "شهبانو",
    "شاهزاده": "شاهزاده",
    "ایرانامدیا": "ایرانامدیا",
}
