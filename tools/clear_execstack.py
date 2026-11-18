"""نشانه‌ی «پشته‌ی اجرایی» (PT_GNU_STACK با PF_X) را از کتابخانه‌های .so برمی‌دارد.
glibc تازه‌ی رایانه‌های GitHub (از آبان ۲۵۸۵) بارگذاری torch 1.12 را با این خطا نمی‌پذیرد:
  libtorch_cpu.so: cannot enable executable stack as shared object requires: Invalid argument
اجرا: python tools/clear_execstack.py  (همه‌ی .so های torch/torchvision/torchaudio در site-packages)"""
import glob, os, struct, sys, sysconfig

PT_GNU_STACK, PF_X = 0x6474E551, 1


def clear(path):
    with open(path, "r+b") as f:
        h = f.read(64)
        if h[:4] != b"\x7fELF" or h[4] != 2:            # تنها ELF 64 بیتی
            return False
        end = "<" if h[5] == 1 else ">"
        phoff = struct.unpack(end + "Q", h[32:40])[0]
        phentsize, phnum = struct.unpack(end + "HH", h[54:58])
        changed = False
        for i in range(phnum):
            off = phoff + i * phentsize
            f.seek(off)
            p_type, p_flags = struct.unpack(end + "II", f.read(8))
            if p_type == PT_GNU_STACK and p_flags & PF_X:
                f.seek(off + 4)
                f.write(struct.pack(end + "I", p_flags & ~PF_X))
                changed = True
        return changed


roots = sys.argv[1:] or [sysconfig.get_paths()["purelib"], sysconfig.get_paths()["platlib"]]
n = 0
for root in set(roots):
    for pkg in ("torch", "torchvision", "torchaudio"):
        for so in glob.glob(os.path.join(root, pkg, "**", "*.so*"), recursive=True):
            try:
                if clear(so):
                    n += 1
                    print("پاک شد:", os.path.relpath(so, root))
            except OSError as e:
                print("نشد:", so, e)
print(n, "کتابخانه")
