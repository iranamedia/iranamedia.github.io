"""مهر کردن فایل‌های خصوصی (مانند نمونه‌ی آوای گوینده) پیش از گذاشتن در مخزن همگانی.
کلید خصوصی تنها از رمزی که در GitHub نگه داشته شده (ELEVENLABS_API_KEY) ساخته می‌شود؛ کلید همگانی بی‌خطر است.
  python3 tools/seal.py pub                      (در Actions) کلید همگانی را چاپ می‌کند
  python3 tools/seal.py seal <pubhex> <in> <out>  (هر جا) فایل را مهر می‌کند
  python3 tools/seal.py open <in> <out>           (در Actions) مهر را می‌گشاید"""
import hashlib, os, sys
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization

RAW = serialization.Encoding.Raw, serialization.PublicFormat.Raw


def private():
    seed = hashlib.sha256((os.environ["ELEVENLABS_API_KEY"] + "-irana-voice-seal").encode()).digest()
    return X25519PrivateKey.from_private_bytes(seed)


def key(shared, eph):
    return HKDF(hashes.SHA256(), 32, eph, b"irana-seal").derive(shared)


mode = sys.argv[1]
if mode == "pub":
    print(private().public_key().public_bytes(*RAW).hex())
elif mode == "seal":
    pub = X25519PublicKey.from_public_bytes(bytes.fromhex(sys.argv[2]))
    eph = X25519PrivateKey.generate()
    e = eph.public_key().public_bytes(*RAW)
    nonce = os.urandom(12)
    ct = AESGCM(key(eph.exchange(pub), e)).encrypt(nonce, open(sys.argv[3], "rb").read(), None)
    open(sys.argv[4], "wb").write(e + nonce + ct)
elif mode == "open":
    d = open(sys.argv[2], "rb").read()
    e, nonce, ct = d[:32], d[32:44], d[44:]
    pt = AESGCM(key(private().exchange(X25519PublicKey.from_public_bytes(e)), e)).decrypt(nonce, ct, None)
    open(sys.argv[3], "wb").write(pt)
