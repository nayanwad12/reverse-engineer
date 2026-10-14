"""Voice edit + procedural music score + synthesized SFX + mix."""
import numpy as np, subprocess, os, wave
from scipy import signal
from timeline import S, KEEP, DUR, BODY, s2o, word_t, WORDS

SR = 48000
rng = np.random.default_rng(7)
OUT = os.path.join(S, "audio")
os.makedirs(OUT, exist_ok=True)


def read_wav(p):
    w = wave.open(p)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a.reshape(-1, w.getnchannels())


def write_wav(p, a):
    a = np.clip(a, -1, 1)
    w = wave.open(p, "wb"); w.setnchannels(a.shape[1]); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((a * 32767).astype(np.int16).tobytes()); w.close()


def bp(x, lo, hi, order=2):
    nyq = SR / 2
    if lo is None:
        b, a = signal.butter(order, hi / nyq, "low")
    elif hi is None:
        b, a = signal.butter(order, lo / nyq, "high")
    else:
        b, a = signal.butter(order, [lo / nyq, hi / nyq], "band")
    return signal.lfilter(b, a, x, axis=0)


def env(n, a, d, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-curve * np.maximum(0, t - a) / max(d, 1e-4))
    return e


def reverb(x, secs=1.8, mix=0.25, damp=3000):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-6.9 * np.arange(n) / n)
    ir = bp(ir, None, damp)
    ir /= np.sqrt(np.sum(ir ** 2))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    irl, irr = ir, np.roll(ir, 311)
    wet = np.stack([signal.fftconvolve(x[:, 0], irl)[:len(x)], signal.fftconvolve(x[:, 1], irr)[:len(x)]], 1)
    return x * (1 - mix) + wet * mix * 1.4


def st(x, pan=0.0):
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l * 1.414, x * r * 1.414], 1)


# ---------------------------------------------------------------- voice
def voice():
    raw = os.path.join(OUT, "raw48.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(S, "raw.mp4"), "-ac", "2", "-ar", str(SR), raw], check=True)
    a = read_wav(raw)
    xf = int(0.012 * SR)
    out = np.zeros((0, 2), np.float32)
    for s, e in KEEP:
        seg = a[int(s * SR):int(e * SR)].copy()
        if len(out):
            ramp = np.linspace(0, 1, xf)[:, None]
            out[-xf:] = out[-xf:] * (1 - ramp) + seg[:xf] * ramp
            seg = seg[xf:]
        out = np.concatenate([out, seg])
    pad = int(DUR * SR) - len(out)
    out = np.concatenate([out, np.zeros((max(pad, 0), 2), np.float32)])[:int(DUR * SR)]
    cut = os.path.join(OUT, "voice_cut.wav"); write_wav(cut, out)
    proc = os.path.join(OUT, "voice_proc.wav")
    # cleanup + broadcast-style chain: HPF, gentle denoise, presence, compression, de-harsh
    chain = ("highpass=f=85,afftdn=nr=10:nf=-45,equalizer=f=220:t=q:w=1.2:g=-2,"
             "equalizer=f=3200:t=q:w=1.0:g=2.5,equalizer=f=7500:t=q:w=2:g=-1.5,"
             "acompressor=threshold=-20dB:ratio=3.5:attack=8:release=120:makeup=4,"
             "alimiter=limit=0.95")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", cut, "-af", chain, "-ar", str(SR), proc], check=True)
    return read_wav(proc)[:int(DUR * SR)]


# ---------------------------------------------------------------- music
BPM = 96
BEAT = 60 / BPM
BAR = BEAT * 4


def note(m):
    return 440 * 2 ** ((m - 69) / 12)


def pad_voice(freq, n):
    t = np.arange(n) / SR
    x = np.zeros(n)
    for det in (-0.12, 0.0, 0.11):
        f = freq * 2 ** (det / 12)
        ph = rng.random()
        x += 2 * ((t * f + ph) % 1) - 1  # saw
    return x / 3


def kick(n=int(0.45 * SR)):
    t = np.arange(n) / SR
    f = 45 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7.5)
    x[:200] += rng.standard_normal(200) * np.linspace(0.4, 0, 200)
    return np.tanh(x * 1.6)


def snare(n=int(0.3 * SR)):
    t = np.arange(n) / SR
    nz = bp(rng.standard_normal(n), 1400, 7000) * np.exp(-t * 16)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return 0.8 * nz + 0.5 * tone


def hat(n=int(0.06 * SR), open_=False):
    if open_:
        n = int(0.22 * SR)
    t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 7000, None, 3) * np.exp(-t * (18 if open_ else 70))


def music(drop_t, end_t):
    n = int(DUR * SR) + SR
    L = np.zeros(n); R = np.zeros(n)
    pads = np.zeros(n)
    bass = np.zeros(n)
    drums = np.zeros((n, 2))
    # Fmaj9 - Em7 - Dm9 - Cmaj7 (lo-fi, warm)
    prog = [[53, 57, 60, 64, 67], [52, 55, 59, 62, 66], [50, 53, 57, 60, 64], [48, 52, 55, 59, 62]]
    roots = [41, 40, 38, 36]
    # bar grid anchored so a downbeat lands exactly on the drop
    t0 = drop_t - np.ceil(drop_t / BAR) * BAR
    bar_i = 0
    t = t0
    while t < DUR + BAR:
        ch = prog[bar_i % 4]
        s = int(max(t, 0) * SR); ln = int(BAR * SR) + int(0.4 * SR)
        off = int((max(t, 0) - t) * SR)
        if s < n:
            for m in ch:
                v = pad_voice(note(m), ln + off)[off:]
                e = np.minimum(1, np.arange(len(v)) / (0.35 * SR)) * np.minimum(1, (len(v) - np.arange(len(v))) / (0.4 * SR))
                seg = v * e * 0.11
                pads[s:s + len(seg)] += seg[:n - s]
            # bass: root on 1, and-of-2, 4
            for bt, dur in ((0, 1.4), (1.5, 0.5), (3, 0.9)):
                bs = t + bt * BEAT
                if bs < 0: continue
                i0 = int(bs * SR); m = int(dur * BEAT * SR)
                tt = np.arange(m) / SR
                b = np.sin(2 * np.pi * note(roots[bar_i % 4]) * tt) + 0.3 * np.sin(4 * np.pi * note(roots[bar_i % 4]) * tt)
                b *= np.minimum(1, tt / 0.01) * np.exp(-tt * 1.8) * np.minimum(1, (m - np.arange(m)) / 600)
                bass[i0:i0 + m] += np.tanh(b * 1.3)[:n - i0] * 0.5
            # drums
            post = t >= drop_t - 0.01
            final = t >= end_t - 0.01
            for b8 in range(8):
                bt = t + b8 * BEAT / 2 + (0.035 if b8 % 2 else 0)  # swing
                if bt < 0: continue
                i0 = int(bt * SR)
                if i0 >= n: continue
                def add(x, g, pan=0.0):
                    seg = st(x, pan) * g
                    m = min(len(seg), n - i0); drums[i0:i0 + m] += seg[:m]
                if final:
                    continue
                if post:
                    if b8 in (0, 5):
                        add(kick(), 0.85)
                    if b8 in (2, 6):
                        add(snare(), 0.32, 0.05)
                    add(hat(open_=(b8 == 7)), 0.14 if b8 % 2 == 0 else 0.09, 0.3)
                else:
                    # intro: soft heartbeat kick + light hats
                    if b8 == 0:
                        add(kick(), 0.45)
                    add(hat(), 0.06, 0.3)
        t += BAR; bar_i += 1
    # pad filter: closed in intro, opens on drop
    pads_dark = bp(pads, None, 900)
    pads_open = bp(pads, None, 2600)
    tt = np.arange(n) / SR
    k = np.clip((tt - (drop_t - 1.2)) / 1.2, 0, 1)
    pads_f = pads_dark * (1 - k) + pads_open * k
    padsS = reverb(st(pads_f, 0) , 2.5, 0.35)
    padsS[:, 0] *= 1.0; padsS[:, 1] = np.roll(padsS[:, 1], 240)  # width
    bassS = st(bp(bass, None, 400), 0) * 0.9
    # vinyl crackle = texture
    cr = np.zeros(n)
    idx = rng.integers(0, n, int(DUR * 22)); cr[idx] = rng.standard_normal(len(idx)) * 0.5
    cr = bp(cr, 1500, 9000) + bp(rng.standard_normal(n), 300, 3000) * 0.004
    mix = padsS + bassS + drums + st(cr, 0) * 0.18
    # master envelope: fade-in, gentle fade at end
    fade_in = np.clip(tt / 0.6, 0, 1)
    fade_out = np.clip((DUR - tt) / 1.4, 0, 1)
    mix *= (fade_in * fade_out)[:, None]
    return mix[:int(DUR * SR)]


# ---------------------------------------------------------------- sfx
def whoosh(d=0.55, up=True, hi=6000):
    n = int(d * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    # sweep a band through the noise
    out = np.zeros(n); blk = 1024
    for i in range(0, n, blk):
        p = i / n
        fc = 300 + (hi - 300) * (p if up else 1 - p) ** 1.5
        out[i:i + blk] = bp(x[i:i + blk], fc * 0.6, min(fc * 1.6, 20000))
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return out * e * 2.2


def impact(g=1.0):
    n = int(1.4 * SR); t = np.arange(n) / SR
    f = 32 + 90 * np.exp(-t * 12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    x += bp(rng.standard_normal(n), 80, 2500) * np.exp(-t * 20) * 0.6
    return reverb(np.tanh(x * 1.8) * g, 1.6, 0.2)


def pop(f0=600, f1=1100):
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = f0 + (f1 - f0) * (t / t[-1])
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * 0.9


def tick():
    n = int(0.25 * SR); t = np.arange(n) / SR
    c = bp(rng.standard_normal(n), 2000, 8000) * np.exp(-t * 400)
    p = np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 22) * 0.35 + np.sin(2 * np.pi * 2640 * t) * np.exp(-t * 30) * 0.2
    return c * 0.6 + p


def glitch(d=0.35):
    n = int(d * SR); out = np.zeros(n); i = 0
    while i < n:
        m = int(rng.uniform(0.012, 0.05) * SR)
        kind = rng.integers(3)
        tt = np.arange(m) / SR
        if kind == 0:
            seg = np.sign(np.sin(2 * np.pi * rng.uniform(200, 1800) * tt)) * 0.35
        elif kind == 1:
            seg = rng.standard_normal(m) * 0.4
        else:
            seg = np.zeros(m)
        out[i:i + m] = seg[:n - i]; i += m
    out = np.round(out * 6) / 6  # bitcrush
    return bp(out, 150, 9000) * 0.8


def riser(d=1.6):
    n = int(d * SR); t = np.arange(n) / SR
    f = 200 * 2 ** (3 * t / d)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    nz = whoosh(d, True, 9000) * 0.6
    e = (t / d) ** 2
    return (tone + nz[:n]) * e


def shimmer(d=1.6, base=1318.5):
    n = int(d * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for k, m in enumerate([1, 1.5, 2, 3]):
        x += np.sin(2 * np.pi * base * m * t + k) * (0.5 / (k + 1)) * (0.6 + 0.4 * np.sin(2 * np.pi * (5 + k) * t))
    x *= np.minimum(1, t / 0.05) * np.exp(-t * 2.5)
    return reverb(x * 0.6, 2.2, 0.45, 9000)


def ding(f=1046.5):
    n = int(1.6 * SR); t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 2.2 * np.exp(-t * 6)
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 3.5) * 0.5
    return reverb(x, 1.8, 0.3, 8000)


def buzz():
    n = int(0.28 * SR); t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.3 + np.sign(np.sin(2 * np.pi * 116 * t)) * 0.3
    return bp(x, 100, 2500) * np.minimum(1, t / 0.01) * np.exp(-t * 8)


def ratchet(k=6, gap=0.055):
    n = int((k * gap + 0.1) * SR); out = np.zeros(n)
    for i in range(k):
        c = tick()[:int(0.05 * SR)] * (0.5 + 0.08 * i)
        s = int(i * gap * SR); out[s:s + len(c)] += c
    return out


def scan_beeps():
    out = np.zeros(int(0.7 * SR))
    for i, f in enumerate([1900, 1900, 2400]):
        n = int(0.06 * SR); t = np.arange(n) / SR
        b = np.sin(2 * np.pi * f * t) * np.minimum(1, (n - np.arange(n)) / 200) * 0.35
        s = int(i * 0.16 * SR); out[s:s + n] += b
    return out


def sfx_track():
    n = int(DUR * SR) + 3 * SR
    tr = np.zeros((n, 2))

    def place(t, x, g=1.0, pan=0.0):
        if x.ndim == 1: x = st(x, pan)
        i = int(max(t, 0) * SR); m = min(len(x), n - i)
        tr[i:i + m] += x[:m] * g

    W = lambda w, after=0.0: word_t(w, after)
    # opener
    place(0.0, impact(0.5), 0.55)
    place(0.0, whoosh(0.5, False), 0.35)
    # "vibe editing is different" title
    place(W("vibe") - 0.45, whoosh(0.5), 0.5, -0.2)
    place(W("vibe"), impact(0.8), 0.6)
    place(W("different"), glitch(0.3), 0.35)
    place(W("soul"), shimmer(1.4, 1568), 0.25)
    place(W("feeling") - 0.05, shimmer(1.8, 1318.5), 0.3)
    # shot change 1 -> whip
    place(s2o(8.0) - 0.28, whoosh(0.5, True, 8000), 0.55, 0.3)
    # texture / color / pacing chips
    place(W("texture"), pop(520, 900), 0.5, -0.3)
    place(W("color", 9), pop(620, 1100), 0.5, 0.0)
    place(W("pacing"), pop(720, 1300), 0.5, 0.3)
    for k in range(3):
        place(W("pacing") + 0.12 + k * 0.16, tick()[:int(0.06 * SR)], 0.35)
    place(W("emotion"), ding(880), 0.22)
    # looks good vs feels right
    place(W("looks"), tick(), 0.35, -0.3)
    place(W("feels"), ding(1318.5), 0.28, 0.3)
    # riser into the drop
    drop = s2o(18.06)
    place(drop - 1.5, riser(1.5), 0.45)
    place(drop - 0.05, impact(1.0), 0.8)
    place(drop, whoosh(0.4, False), 0.4)
    place(W("AI", 18), glitch(0.45), 0.45)
    place(W("game"), pop(400, 700), 0.3)
    # checklist
    for w, p in (("denoising", -0.2), ("matching", 0.0), ("tracking", 0.2)):
        place(W(w), tick(), 0.55, p)
    place(W("tracking") + 0.1, scan_beeps(), 0.3, 0.2)
    # focus pull
    place(W("focus") - 0.45, whoosh(0.6, False, 3500), 0.35)
    place(W("vibe", 27), shimmer(1.2, 1760), 0.22)
    # shot change 3
    place(s2o(28.0) - 0.25, whoosh(0.45, True, 7000), 0.5, -0.3)
    place(W("replacing"), buzz(), 0.28)
    place(W("amplifying") - 0.05, pop(500, 1400), 0.5)
    place(W("amplifying") + 0.05, impact(0.5), 0.4)
    place(W("dial"), ratchet(7), 0.5, 0.2)
    place(W("faster"), whoosh(0.35, True, 10000), 0.5)
    place(W("intuitively"), pop(800, 1200), 0.25)
    # finale
    place(W("feeling", 37) - 0.1, shimmer(2.6, 1046.5), 0.4)
    place(W("feeling", 37), impact(0.6), 0.45)
    place(BODY + 0.05, whoosh(0.7, False, 5000), 0.35)
    return tr[:int(DUR * SR)]


def envelope_follow(x, win=0.06):
    m = np.abs(x).mean(1)
    k = int(win * SR)
    e = np.convolve(m, np.ones(k) / k, mode="same")
    return e


if __name__ == "__main__":
    v = voice()
    drop = s2o(18.06)
    end_t = word_t("feeling", 37) - 0.02
    m = music(drop, end_t)
    fx = sfx_track()
    write_wav(os.path.join(OUT, "music.wav"), m * 0.5)
    write_wav(os.path.join(OUT, "sfx.wav"), fx * 0.5)
    # sidechain duck music under voice
    ve = envelope_follow(v)
    gate = np.clip((20 * np.log10(ve + 1e-6) + 42) / 12, 0, 1)  # 0 below -42dB, 1 above -30dB
    k = int(0.15 * SR)
    gate = np.convolve(gate, np.ones(k) / k, mode="same")
    duck = 1 - 0.45 * gate
    mus = m / (np.abs(m).max() + 1e-9)
    voice_n = v / (np.abs(v).max() + 1e-9)
    mix = voice_n * 0.9 + mus * duck[:, None] * 0.30 + fx * 0.45
    pre = os.path.join(OUT, "mix_pre.wav"); write_wav(pre, mix / max(1.0, np.abs(mix).max()))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
                    "loudnorm=I=-14:TP=-1.0:LRA=9:print_format=summary", "-ar", str(SR),
                    os.path.join(OUT, "final_mix.wav")], check=True)
    # comparison audio uses the same mix
    print("done", DUR)
