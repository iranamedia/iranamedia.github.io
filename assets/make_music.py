"""آهنگ خبری رسانه ایرانا را می‌سازد (ساخته‌ی خود ما، بی‌نیاز از پروانه).
خروجی: bed.mp3 (زیرآهنگ پیوسته‌ی تیترها) و sting.mp3 (نشانه‌ی آغاز خبرها).
برای جایگزینی با آهنگ دلخواه، کافی است دو فایل هم‌نام را در همین پوشه بگذارید."""
import numpy as np, subprocess, wave, os, sys

SR = 44100
BPM = 116
BEAT = 60 / BPM
here = os.path.dirname(os.path.abspath(__file__))


def note(n):  # MIDI -> Hz
    return 440 * 2 ** ((n - 69) / 12)


def env(n, a, d, sustain=0.0, r=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * (sustain + (1 - sustain) * np.exp(-t / d))
    if r:
        rl = int(r * SR); e[-rl:] *= np.linspace(1, 0, rl)
    return e


def tone(freq, dur, harm=(1,), amps=None, detune=0.0):
    t = np.arange(int(dur * SR)) / SR
    amps = amps or [1 / (i + 1) for i in range(len(harm))]
    s = sum(a * np.sin(2 * np.pi * freq * h * t) for h, a in zip(harm, amps))
    if detune:
        s += sum(a * np.sin(2 * np.pi * freq * (1 + detune) * h * t) for h, a in zip(harm, amps))
    return s


def add(buf, sig, at, pan=0.0):
    i = int(at * SR); j = min(len(buf), i + len(sig)); sig = sig[: j - i]
    buf[i:j, 0] += sig * (1 - pan) ; buf[i:j, 1] += sig * (1 + pan)


def bed():
    bars = 4; length = bars * 4 * BEAT
    buf = np.zeros((int(length * SR) + SR, 2))
    chords = [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]]  # Dm Bb F C
    roots = [38, 34, 41, 36]
    for b in range(bars):
        t0 = b * 4 * BEAT
        for n in chords[b]:  # soft pad
            p = tone(note(n), 4 * BEAT + 0.6, harm=(1, 2, 3), amps=[1, .3, .12], detune=0.004)
            add(buf, 0.045 * p * env(len(p), 0.35, 9, 0.6, r=0.6), t0)
        for k in range(4):  # bass pulse on beats
            p = tone(note(roots[b]), BEAT * 0.9, harm=(1, 2), amps=[1, .25])
            add(buf, 0.22 * p * env(len(p), 0.005, 0.25, r=0.05), t0 + k * BEAT)
        seq = [chords[b][3] + 12, chords[b][2] + 12, chords[b][3] + 12, chords[b][1] + 12]
        for k in range(16):  # ticking 16ths: the "news" urgency
            n = seq[k % 4]; d = BEAT / 4
            p = tone(note(n), d, harm=(1, 3), amps=[1, .2])
            vel = 0.075 if k % 4 == 0 else 0.045
            add(buf, vel * p * env(len(p), 0.002, 0.045, r=0.01), t0 + k * d, pan=0.35 if k % 2 else -0.35)
    # wrap the tail so the loop is seamless
    n = int(length * SR); tail = buf[n:].copy(); buf = buf[:n]; buf[: len(tail)] += tail
    return buf


def sting():
    buf = np.zeros((int(3.2 * SR), 2))
    for k, n in enumerate([62, 65, 69, 74]):  # rising run
        p = tone(note(n), 0.5, harm=(1, 2, 3), amps=[1, .35, .15])
        add(buf, 0.09 * p * env(len(p), 0.003, 0.12, r=0.05), k * 0.11, pan=-0.3 + 0.2 * k)
    hit = 0.46
    for n in [38, 50, 57, 62, 65, 69, 74]:  # full Dm hit
        p = tone(note(n), 2.7, harm=(1, 2, 3, 4), amps=[1, .4, .2, .1], detune=0.003)
        add(buf, 0.06 * p * env(len(p), 0.004, 0.9, r=0.4), hit)
    t = np.arange(int(0.6 * SR)) / SR  # low timpani-like thump
    add(buf, 0.5 * np.sin(2 * np.pi * (70 * np.exp(-t * 3)) * t) * np.exp(-t * 6), hit)
    return buf


def write(buf, name):
    buf = buf / max(1e-9, np.abs(buf).max()) * 0.89
    wav = os.path.join(here, name + ".wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libmp3lame", "-b:a", "160k",
                    os.path.join(here, name + ".mp3")], check=True)
    os.remove(wav)


if __name__ == "__main__":
    write(bed(), "bed"); write(sting(), "sting"); print("ok")
