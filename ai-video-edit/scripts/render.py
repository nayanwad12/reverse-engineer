"""Full edit renderer: 9:16 face-tracked reframe, grade, FX, kinetic captions, motion graphics."""
import numpy as np, cv2, json, os, sys, subprocess, math
from multiprocessing import Process
from PIL import Image, ImageDraw, ImageFilter
from timeline import S, FPS, W, H, KEEP, SHOT_STARTS, BODY, DUR, s2o, o2s, word_t, WORDS
from gfx import *

SRC_FPS = 24
CX = 528            # horizontal centre for graphics (nudged left of IG action buttons)
CAP_Y = 1245        # caption centre line
BAND_Y = 930        # graphics band (chest area)
rng = np.random.default_rng(3)
Wt = word_t

# ------------------------------------------------------------------ source + grade
def grade_luts():
    x = np.arange(256) / 255.0
    sm = x * x * (3 - 2 * x)
    y = x + (sm - x) * 0.45                      # S-curve contrast
    y = 0.035 + y * 0.925                        # lifted blacks, rolled highlights
    sh = (1 - y) ** 2; hi = y ** 2
    r = y + 0.030 * hi - 0.010 * sh
    g = y + 0.008 * hi + 0.012 * sh
    b = y - 0.040 * hi + 0.035 * sh
    return [np.clip(c * 255, 0, 255).astype(np.uint8) for c in (r, g, b)]


def load_source():
    cap = cv2.VideoCapture(os.path.join(S, "raw.mp4"))
    luts = grade_luts()
    raw, graded = [], []
    while True:
        ok, f = cap.read()
        if not ok: break
        f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        raw.append(f)
        g = cv2.merge([cv2.LUT(f[..., i], luts[i]) for i in range(3)])
        # saturation 1.08 via luma mix
        gf = g.astype(np.float32)
        l = (gf @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        g = np.clip(l + (gf - l) * 1.08, 0, 255).astype(np.uint8)
        graded.append(g)
    return raw, graded


def face_track(n):
    det = np.array(json.load(open(os.path.join(S, "face.json"))))
    idx = np.arange(n)
    cx = np.interp(idx, det[:, 0], det[:, 1]); cy = np.interp(idx, det[:, 0], det[:, 2]); fw = np.interp(idx, det[:, 0], det[:, 3])
    bounds = [0] + [int(s * SRC_FPS) for s in SHOT_STARTS] + [n]
    out = []
    for arr in (cx, cy, fw):
        sm = arr.copy()
        for a, b in zip(bounds[:-1], bounds[1:]):
            seg = arr[a:b]
            k = 31
            padded = np.pad(seg, (k, k), mode="edge")
            for _ in range(2):
                padded = np.convolve(padded, np.ones(k) / k, mode="same")
            sm[a:b] = padded[k:-k]
        out.append(sm)
    return out


# ------------------------------------------------------------------ camera
SEG_ZOOM = [1.0, 1.12, 1.0, 1.04, 1.13, 1.03, 1.0, 1.1, 1.02]
drop_t = s2o(18.06)
whip_ts = [s2o(8.0), s2o(28.0)]

PUNCH = [(Wt("technical"), 0.05), (Wt("vibe"), 0.12), (Wt("soul"), 0.07), (Wt("intangible"), 0.04),
         (Wt("texture"), 0.05), (Wt("color", 9), 0.05), (Wt("emotion"), 0.08), (Wt("feels"), 0.09),
         (Wt("AI", 18), 0.14), (Wt("heavy"), 0.06), (Wt("vibe", 27), 0.08), (Wt("editor"), 0.04),
         (Wt("amplifying"), 0.12), (Wt("faster"), 0.10), (Wt("feeling", 37), 0.12)]
PULSES = [Wt("pacing") + 0.1 + k * 0.16 for k in range(3)]
SHAKES = [(Wt("vibe"), 12, 0.35), (Wt("different"), 7, 0.25), (drop_t, 20, 0.5), (Wt("AI", 18), 15, 0.45),
          (Wt("amplifying"), 9, 0.3), (Wt("feeling", 37), 7, 0.4)]


def punch_amt(t):
    z = 0.0
    for t0, a in PUNCH:
        d = t - t0
        if d < -0.02 or d > 1.4: continue
        if d < 0.12: z += a * ease_out(d / 0.12)
        elif d < 0.4: z += a
        else: z += a * (1 - ease_io((d - 0.4) / 0.9))
    for t0 in PULSES:
        d = t - t0
        if 0 <= d < 0.16: z += 0.045 * math.sin(math.pi * d / 0.16)
    return z


def camera(t, track):
    cxs_a, cys_a, fw_a = track
    src, seg = o2s(t)
    outro = src is None
    if outro:
        src = 37.95
    fi = min(int(src * SRC_FPS), len(cxs_a) - 1)
    seg_t0 = sum(b - a for a, b in KEEP[:seg]); seg_len = KEEP[seg][1] - KEEP[seg][0]
    z = SEG_ZOOM[seg] + 0.045 * min(1, (t - seg_t0) / seg_len)
    z += 0.18 * (1 - ease_out(t / 0.6))                       # opening zoom-out
    z += punch_amt(t)
    if t >= drop_t: z += 0.22 * (1 - ease_out((t - drop_t) / 0.45))
    if outro: z += 0.06 * ease_io((t - BODY) / 1.4)
    z = min(z, 1.32)
    dx = 5 * math.sin(2 * math.pi * 0.21 * t) + 3 * math.sin(2 * math.pi * 0.53 * t + 1)
    dy = 4 * math.sin(2 * math.pi * 0.17 * t + 2)
    rot = 0.25 * math.sin(2 * math.pi * 0.13 * t)
    for t0, amp, dur in SHAKES:
        d = t - t0
        if 0 <= d < dur:
            e = amp * (1 - d / dur) ** 2
            dx += e * math.sin(2 * math.pi * 21 * d + t0); dy += e * math.cos(2 * math.pi * 17 * d + 2 * t0)
            rot += e * 0.05 * math.sin(2 * math.pi * 13 * d)
    ch = 720 / z; cw = ch * 9 / 16
    cx = np.clip(cxs_a[fi], cw / 2, 1280 - cw / 2)
    cy = np.clip(cys_a[fi] + ch * 0.20, ch / 2, 720 - ch / 2)
    return dict(fi=fi, z=z, cx=cx, cy=cy, dx=dx, dy=dy, rot=rot, k=ch / H, outro=outro,
                fx=cxs_a[fi], fy=cys_a[fi], fw=fw_a[fi])


def render_cam(src, c):
    k = c["k"]; a = math.radians(c["rot"])
    ca, sa = math.cos(a) * k, math.sin(a) * k
    # output (u,v) -> source: R*k*(u-W/2-dx, v-H/2-dy) + (cx,cy)
    ox, oy = W / 2 + c["dx"], H / 2 + c["dy"]
    M = np.array([[ca, -sa, c["cx"] - ca * ox + sa * oy],
                  [sa, ca, c["cy"] - sa * ox - ca * oy]], np.float32)
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)


def src_to_out(c, x, y):
    k = c["k"]; a = math.radians(c["rot"])
    rx, ry = (x - c["cx"]) / k, (y - c["cy"]) / k
    ca, sa = math.cos(-a), math.sin(-a)
    return W / 2 + c["dx"] + ca * rx - sa * ry, H / 2 + c["dy"] + sa * rx + ca * ry


# ------------------------------------------------------------------ FX
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.42) / (H * 0.62)) ** 2)
VIG = np.clip(1 - np.clip(_r - 0.55, 0, None) ** 1.6, 0, 1).astype(np.float32)
GRAIN = [cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7) for _ in range(6)]
del xx, yy, _r


def win(t, a, b, fi=0.15, fo=0.15):
    if t < a - 1e-9 or t > b: return 0.0
    return min(1.0, (t - a) / fi if fi else 1, (b - t) / fo if fo else 1)


def vignette(f, strength):
    m = 1 - strength * (1 - VIG)
    return (f.astype(np.float32) * m[..., None]).clip(0, 255).astype(np.uint8)


def add_grain(f, amp, i):
    g = GRAIN[i % 6] * amp
    return np.clip(f.astype(np.float32) + g[..., None], 0, 255).astype(np.uint8)


def sharpen(f):
    b = cv2.GaussianBlur(f, (0, 0), 1.6)
    return cv2.addWeighted(f, 1.45, b, -0.45, 0)


def glitch(f, I, seed):
    r = np.random.default_rng(seed)
    out = f.copy()
    s = int(4 + 22 * I)
    out[..., 0] = np.roll(f[..., 0], -s, axis=1)
    out[..., 2] = np.roll(f[..., 2], s, axis=1)
    for _ in range(int(3 + 7 * I)):
        y0 = r.integers(0, H - 140); hh = r.integers(14, 140)
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], int(r.integers(-90, 90) * I), axis=1)
    out[::4] = (out[::4] * (1 - 0.25 * I)).astype(np.uint8)
    return out


def light_leak(f, strength, t):
    if strength <= 0.01: return f
    h, w = 240, 135
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    leak = np.zeros((h, w, 3), np.float32)
    blobs = [((255, 150, 60), 0.15 + 0.1 * math.sin(t * 0.7), 0.2 + 0.15 * math.sin(t * 0.5), 70),
             ((255, 90, 120), 0.95 + 0.08 * math.sin(t * 0.9 + 1), 0.55 + 0.2 * math.cos(t * 0.4), 60),
             ((255, 220, 170), 0.6 + 0.3 * math.sin(t * 0.3 + 2), 0.05, 55)]
    for col, bx, by, rad in blobs:
        g = np.exp(-(((xx - bx * w) ** 2 + (yy - by * h) ** 2) / (2 * rad ** 2)))
        leak += g[..., None] * np.array(col, np.float32) / 255
    leak = cv2.resize(np.clip(leak * strength, 0, 1), (W, H), interpolation=cv2.INTER_LINEAR)
    ff = f.astype(np.float32) / 255
    return ((1 - (1 - ff) * (1 - leak)) * 255).astype(np.uint8)


PARTS = [dict(x=rng.uniform(60, W - 60), y=rng.uniform(150, H - 300), r=rng.uniform(2, 7), sp=rng.uniform(20, 60),
              ph=rng.uniform(0, 6.28), dr=rng.uniform(-12, 12)) for _ in range(46)]


def particles(f, strength, t):
    if strength <= 0.01: return f
    layer = np.zeros((H // 2, W // 2), np.float32)
    for p in PARTS:
        y = (p["y"] - p["sp"] * t) % (H - 200) + 100
        x = p["x"] + p["dr"] * math.sin(t + p["ph"])
        tw = 0.5 + 0.5 * math.sin(t * 3 + p["ph"])
        cv2.circle(layer, (int(x / 2), int(y / 2)), max(1, int(p["r"] / 2)), 0.6 + 0.4 * tw, -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(layer, (0, 0), 3) * 1.4 + layer
    glow = cv2.resize(glow, (W, H)) * strength
    add = glow[..., None] * np.array([255, 236, 200], np.float32)
    return np.clip(f.astype(np.float32) + add, 0, 255).astype(np.uint8)


def hblur(f, L):
    L = int(L)
    if L < 3: return f
    small = cv2.resize(f, (W // 2, H // 2))
    k = np.ones((1, L // 2 | 1), np.float32) / (L // 2 | 1)
    return cv2.resize(cv2.filter2D(small, -1, k), (W, H))


def zoom_blur(f, a):
    if a < 0.02: return f
    acc = f.astype(np.float32)
    for i in range(1, 5):
        s = 1 + 0.045 * a * i
        M = cv2.getRotationMatrix2D((W / 2, H * 0.4), 0, s)
        acc += cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return (acc / 5).astype(np.uint8)


def saturate(f, s, warm=0.0):
    ff = f.astype(np.float32)
    l = (ff @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    o = l + (ff - l) * s
    o[..., 0] += 18 * warm; o[..., 2] -= 14 * warm
    return np.clip(o, 0, 255).astype(np.uint8)


SPEED = None
def speed_lines():
    img = Image.new("L", (W, H), 0); d = ImageDraw.Draw(img)
    r = np.random.default_rng(11)
    for _ in range(70):
        a = r.uniform(0, 2 * math.pi); r0 = r.uniform(430, 620); r1 = r0 + r.uniform(250, 700)
        c = (W / 2, H * 0.42)
        d.line([(c[0] + r0 * math.cos(a), c[1] + r0 * math.sin(a) * 1.4), (c[0] + r1 * math.cos(a), c[1] + r1 * math.sin(a) * 1.4)],
               fill=int(r.uniform(120, 255)), width=int(r.uniform(2, 6)))
    return np.array(img.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255


# ------------------------------------------------------------------ captions
TITLE_WORDS = set()
def _mark(t_from_src, t_to_src):
    for i, w in enumerate(WORDS):
        if t_from_src - 0.01 <= w["s"] <= t_to_src + 0.01: TITLE_WORDS.add(i)
_mark(2.72, 3.92); _mark(18.64, 19.60); _mark(36.64, 37.36)

EMPH = {"technical", "vibe", "soul", "intangible", "feeling", "texture", "color", "pacing", "emotion", "feels", "right",
        "heavy", "lifting", "curator", "aesthetic", "faster", "focus", "amplifying", "how", "different"}
CAP_SIZE = 84


def build_chunks():
    chunks, cur = [], []
    def flush():
        nonlocal cur
        if cur: chunks.append(cur); cur = []
    for i, w in enumerate(WORDS):
        if i in TITLE_WORDS:
            flush(); continue
        txt = w["w"].upper()
        chars = sum(len(WORDS[j]["w"]) + 1 for j in cur) + len(txt)
        if cur and (len(cur) >= 3 or chars > 17):
            flush()
        cur.append(i)
        if txt[-1] in ".,?!":
            flush()
    flush()
    out = []
    for ci, ch in enumerate(chunks):
        t0 = WORDS[ch[0]]["os"]
        last = WORDS[ch[-1]]
        nxt = WORDS[ch[-1] + 1]["os"] if ch[-1] + 1 < len(WORDS) else BODY
        t1 = min(nxt, last["os"] + 0.9) if (ch[-1] + 1) in TITLE_WORDS else nxt
        t1 = max(t1, last["os"] + 0.25)
        words = []
        fnt = F_cap(CAP_SIZE)
        for i in ch:
            raw = WORDS[i]["w"].upper()
            key = WORDS[i]["w"].strip(".,!?").lower()
            em = key in EMPH
            spr = text_sprite(raw, fnt, glow=0.0)
            spr_em = text_sprite(raw, fnt, glow=1.1 if em else 0.6, glow_col=(255, 244, 225))
            words.append(dict(i=i, txt=raw, spr=spr, spr_on=spr_em, em=em, adv=fnt.getlength(raw),
                              t=WORDS[i]["os"], te=WORDS[i]["oe"]))
        # layout: one line, or two balanced lines
        space = CAP_SIZE * 0.42
        total = sum(w["adv"] for w in words) + space * (len(words) - 1)
        lines = [words]
        if total > 860 and len(words) > 1:
            best = None
            for k in range(1, len(words)):
                a = sum(w["adv"] for w in words[:k]); b = sum(w["adv"] for w in words[k:])
                if best is None or abs(a - b) < best[0]: best = (abs(a - b), k)
            lines = [words[:best[1]], words[best[1]:]]
        lh = CAP_SIZE * 1.12
        for li, line in enumerate(lines):
            lw = sum(w["adv"] for w in line) + space * (len(line) - 1)
            x = CX - lw / 2
            y = CAP_Y + (li - (len(lines) - 1) / 2) * lh
            for w in line:
                w["cx"] = x + w["adv"] / 2; w["cy"] = y; x += w["adv"] + space
        out.append(dict(t0=t0, t1=t1, words=words))
    return out


def draw_captions(f, t, chunks):
    for ch in chunks:
        if not (ch["t0"] - 0.02 <= t < ch["t1"]): continue
        ex = 1.0
        if ch["t1"] - t < 0.08: ex = (ch["t1"] - t) / 0.08
        for w in ch["words"]:
            d = t - w["t"] + 0.03
            if d < 0: continue
            p = d / 0.22
            sc = 0.45 + 0.55 * ease_back(p, 2.2)
            al = min(1, d / 0.07) * ex
            yo = 26 * (1 - ease_out(p))
            active = w["t"] - 0.03 <= t < w["te"]
            if active:
                sc *= 1.08 if w["em"] else 1.04
            sc *= 0.96 + 0.04 * ex
            rot = (2.5 if w["em"] else 0) * (1 - ease_out(p)) * (1 if w["i"] % 2 else -1)
            blit(f, w["spr_on"] if active else w["spr"], w["cx"], w["cy"] + yo, sc, al, rot)


# ------------------------------------------------------------------ motion graphics
class G: pass
g = G()


def build_graphics():
    g.hook = pill_sprite("TECHNICAL  vs  VIBE EDITING", F_bold(46), bg=(14, 14, 18, 190))
    g.vibe = text_sprite("VIBE", F_title(300), glow=1.0, glow_col=ACCENT, stroke=0)
    g.editing = text_sprite("EDITING", F_title(170), glow=0.5, glow_col=ACCENT, stroke=0)
    g.isdiff = text_sprite("IS DIFFERENT", F_cap(64))

    def ic_tex(d, x, y, s):
        for i in range(3):
            for j in range(3):
                r = s * 0.11; d.ellipse((x + i * s * 0.36, y + j * s * 0.36, x + i * s * 0.36 + 2 * r, y + j * s * 0.36 + 2 * r), fill=(255, 255, 255))
    def ic_col(d, x, y, s):
        cols = [(255, 92, 92), (255, 196, 64), (80, 210, 140), (70, 150, 255)]
        for k, c in enumerate(cols):
            d.pieslice((x, y, x + s, y + s), k * 90, k * 90 + 90, fill=c)
    def ic_pace(d, x, y, s):
        for k, hh in enumerate([0.45, 0.9, 0.65]):
            d.rounded_rectangle((x + k * s * 0.36, y + s * (1 - hh), x + k * s * 0.36 + s * 0.22, y + s), 3, fill=(255, 255, 255))
    f = F_bold(34)
    g.chips = [pill_sprite("TEXTURE", f, icon=ic_tex), pill_sprite("COLOR", f, icon=ic_col), pill_sprite("PACING", f, icon=ic_pace)]
    g.looks = pill_sprite("LOOKS GOOD", F_bold(38), bg=(14, 14, 18, 170), fg=(215, 215, 215))
    g.feels = pill_sprite("FEELS RIGHT", F_bold(38), bg=(255, 255, 255, 245), fg=(18, 18, 22), border=(255, 255, 255, 255),
                          icon=lambda d, x, y, s: draw_spark(d, x + s / 2, y + s / 2, s / 2, (255, 160, 40, 255)))
    g.ai = text_sprite("AI", F_title(520), glow=0.9, glow_col=(255, 255, 255), stroke=0)
    g.changes = [text_sprite(wd, F_cap(80)) for wd in ("CHANGES", "THE", "GAME.")]
    g.changes_on = [text_sprite(wd, F_cap(80), glow=1.0) for wd in ("CHANGES", "THE", "GAME.")]
    # checklist
    cw, chh = 560, 330
    card = canvas(cw + 60, chh + 60); d = ImageDraw.Draw(card)
    sh = Image.new("L", card.size, 0); ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + cw, 40 + chh), 34, fill=150)
    card.putalpha(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((30, 30, 30 + cw, 30 + chh), 34, fill=(12, 12, 16, 185), outline=(255, 255, 255, 70), width=2)
    d.text((70, 58), "AI HANDLES", font=F_mono(30), fill=ACCENT)
    d.ellipse((cw - 10, 66, cw + 8, 84), fill=ACCENT)
    g.card = np.array(card); g.card_size = (cw, chh)
    g.rows = []
    for txt in ("DENOISING", "COLOR MATCHING", "TRACKING"):
        im = canvas(500, 70); d = ImageDraw.Draw(im)
        d.rounded_rectangle((4, 9, 52, 57), 10, outline=(255, 255, 255, 230), width=4)
        d.text((76, 10), txt, font=F_bold(40), fill=(255, 255, 255))
        g.rows.append(np.array(im))
    tk = canvas(70, 70); d = ImageDraw.Draw(tk)
    d.rounded_rectangle((4, 4, 52, 52), 10, fill=ACCENT)
    draw_check(d, 6, 6, 44, (20, 20, 20), 6)
    g.tick = np.array(tk)
    g.trk = pill_sprite("TRACKING", F_mono(26), bg=(255, 255, 255, 235), fg=(18, 18, 22), padx=18, pady=8, radius=10,
                        icon=lambda d, x, y, s: d.ellipse((x + s * 0.2, y + s * 0.2, x + s * 0.8, y + s * 0.8), fill=(255, 60, 60)))
    g.replacing = text_sprite("REPLACING", F_title(118), fill=(235, 235, 235))
    g.editor_lbl = text_sprite("THE EDITOR", F_cap(46), fill=(235, 235, 235))
    g.amplifying = text_sprite("AMPLIFYING", F_title(150), glow=1.2, glow_col=ACCENT, stroke=0)
    g.curator = text_sprite("THE CURATOR", F_cap(50), glow=0.6, glow_col=ACCENT)
    g.aesthetic = pill_sprite("AESTHETIC", F_mono(30), bg=(14, 14, 18, 190), padx=22, pady=10, radius=12)
    g.fin1 = [text_sprite(wd, F_cap(76)) for wd in ("IT'S", "ALL", "ABOUT")]
    g.fin2 = text_sprite("THE FEELING.", F_title(190), glow=1.3, glow_col=ACCENT, stroke=0)
    g.cta = pill_sprite("FOLLOW FOR MORE", F_bold(36), bg=(255, 255, 255, 240), fg=(18, 18, 22), border=(255, 255, 255, 255),
                        icon=lambda d, x, y, s: draw_spark(d, x + s / 2, y + s / 2, s / 2, (255, 160, 40, 255)))


def dial_sprite(p, show_val):
    R = 128; sz = 2 * R + 80
    im = canvas(sz, sz); c = sz / 2
    sh = Image.new("L", im.size, 0); ImageDraw.Draw(sh).ellipse((c - R - 6, c - R + 4, c + R + 6, c + R + 14), fill=150)
    im.putalpha(sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    d.ellipse((c - R, c - R, c + R, c + R), fill=(12, 12, 16, 195), outline=(255, 255, 255, 70), width=2)
    a0, span = 135, 270
    for k in range(28):
        a = math.radians(a0 + span * k / 27)
        r0, r1 = R - 22, R - (34 if k % 3 == 0 else 28)
        on = k / 27 <= p
        d.line([(c + r0 * math.cos(a), c + r0 * math.sin(a)), (c + r1 * math.cos(a), c + r1 * math.sin(a))],
               fill=(*ACCENT, 255) if on else (255, 255, 255, 110), width=4)
    d.arc((c - R + 8, c - R + 8, c + R - 8, c + R - 8), a0, a0 + span, fill=(255, 255, 255, 50), width=6)
    if p > 0.005:
        d.arc((c - R + 8, c - R + 8, c + R - 8, c + R - 8), a0, a0 + span * p, fill=(*ACCENT, 255), width=6)
    a = math.radians(a0 + span * p)
    d.line([(c, c), (c + (R - 48) * math.cos(a), c + (R - 48) * math.sin(a))], fill=(255, 255, 255), width=7)
    d.ellipse((c - 12, c - 12, c + 12, c + 12), fill=(255, 255, 255))
    if show_val:
        txt = f"{int(round(p * 100))}%"
        l, t, r, b = F_mono(34).getbbox(txt)
        d.text((c - (r - l) / 2 - l, c + R * 0.42 - t), txt, font=F_mono(34), fill=(255, 255, 255))
    return np.array(im)


def draw_graphics(f, t, cam):
    # hook pill
    a, b = 0.15, Wt("vibe") - 0.15
    if a <= t < b + 0.2:
        p = ease_back((t - a) / 0.35)
        al = min(1, (t - a) / 0.15) * (1 if t < b else max(0, 1 - (t - b) / 0.2))
        blit(f, g.hook, CX, 285 - 50 * (1 - p), 0.9 + 0.1 * p, al)
    # VIBE EDITING title
    t0, te = Wt("vibe"), s2o(4.42) - 0.05
    if t0 - 0.02 <= t < te:
        ex = min(1, (te - t) / 0.12)
        p = (t - t0) / 0.2
        blit(f, g.vibe, CX, 1010, 1 + 0.8 * (1 - ease_out(p)), min(1, (t - t0) / 0.06) * ex)
        t1 = Wt("editing", 2.5)
        if t >= t1 - 0.03:
            p2 = ease_out((t - t1 + 0.03) / 0.22)
            blit(f, g.editing, CX, 1205 + 70 * (1 - p2), 1.0, p2 * ex)
        t2 = Wt("different")
        if t >= t2 - 0.03:
            p3 = (t - t2 + 0.03) / 0.2
            jit = (np.random.default_rng(int(t * 100)).integers(-14, 14) if p3 < 0.8 else 0)
            blit(f, g.isdiff, CX + jit, 1340, 0.6 + 0.4 * ease_back(p3), min(1, p3 * 3) * ex)
    # texture / color / pacing chips
    tc = [Wt("texture"), Wt("color", 9), Wt("pacing")]
    te = s2o(14.0)
    if tc[0] - 0.02 <= t < te + 0.2:
        ws = [c.shape[1] - 60 for c in g.chips]; gap = 14
        x = CX - (sum(ws) + gap * 2) / 2
        for k, (spr, wk) in enumerate(zip(g.chips, ws)):
            cx = x + wk / 2; x += wk + gap
            if t < tc[k] - 0.02: continue
            p = (t - tc[k] + 0.02) / 0.3
            ex = 1 if t < te else max(0, 1 - (t - te - k * 0.04) / 0.15)
            blit(f, spr, cx, BAND_Y + 40 * (1 - ease_out(p)), (0.3 + 0.7 * ease_back(p, 2.4)) * (0.9 + 0.1 * ex), min(1, p * 3) * ex,
                 rot=8 * (1 - ease_out(p)) * (-1) ** k)
    # looks good / feels right
    tl, tf, te = Wt("looks"), Wt("feels"), s2o(17.7) - 0.05
    if tl - 0.02 <= t < te + 0.15:
        ex = 1 if t < te else max(0, 1 - (t - te) / 0.15)
        p = (t - tl + 0.02) / 0.28
        dim = 1 - 0.45 * ease_out((t - tf) / 0.25) if t >= tf else 1
        blit(f, g.looks, CX - 205, BAND_Y + 30 * (1 - ease_out(p)), (0.5 + 0.5 * ease_back(p)) * (0.92 + 0.08 * dim), min(1, p * 3) * ex * dim)
        if t >= tf - 0.02:
            p2 = (t - tf + 0.02) / 0.3
            blit(f, g.feels, CX + 205, BAND_Y + 30 * (1 - ease_out(p2)), 0.4 + 0.65 * ease_back(p2, 2.6), min(1, p2 * 3) * ex)
    # AI changes the game
    ta = Wt("AI", 18); te = s2o(20.16) - 0.06
    if ta - 0.02 <= t < te:
        ex = min(1, (te - t) / 0.1)
        p = (t - ta + 0.02) / 0.25
        sc = 1.6 - 0.6 * ease_out(p)
        if p < 1.6:   # rgb-split ghosting while it lands
            off = int(28 * max(0, 1 - p / 1.6) * (1 + math.sin(t * 90)))
            r_ = g.ai.copy(); r_[..., 1] = 0; r_[..., 2] = 0
            b_ = g.ai.copy(); b_[..., 0] = 0; b_[..., 1] = 0
            blit(f, r_, CX - off, 1010, sc, 0.55 * ex)
            blit(f, b_, CX + off, 1010, sc, 0.55 * ex)
        blit(f, g.ai, CX, 1010, sc, min(1, p * 4) * ex)
        tw = [Wt("changes"), Wt("the", 19.4), Wt("game")]
        fnt = F_cap(80); advs = [fnt.getlength(s) for s in ("CHANGES", "THE", "GAME.")]; sp = 24
        x = CX - (sum(advs) + 2 * sp) / 2
        for k in range(3):
            cx = x + advs[k] / 2; x += advs[k] + sp
            if t < tw[k] - 0.03: continue
            q = (t - tw[k] + 0.03) / 0.22
            on = t < (tw[k + 1] if k < 2 else tw[k] + 0.5)
            blit(f, g.changes_on[k] if on else g.changes[k], cx, 1330 + 24 * (1 - ease_out(q)), (0.45 + 0.55 * ease_back(q)) * (1.08 if on else 1), min(1, q * 3) * ex)
    # checklist card
    tc0 = Wt("heavy") - 0.1; te = Wt("how") + 0.25
    if tc0 <= t < te + 0.3:
        ex = 1 if t < te else max(0, 1 - (t - te) / 0.25)
        p = ease_out((t - tc0) / 0.35)
        ox = -120 * (1 - p) - 160 * (1 - ex)
        cw, chh = g.card_size
        blit(f, g.card, CX + ox, BAND_Y, 1.0, p * ex)
        for k, wd in enumerate(("denoising", "matching", "tracking")):
            tk = Wt(wd) if wd != "matching" else Wt("color", 21)
            if t < tk - 0.08: continue
            q = ease_out((t - tk + 0.08) / 0.25)
            ry = BAND_Y - chh / 2 + 130 + k * 72
            rx = CX - cw / 2 + 40 + 250 + ox
            blit(f, g.rows[k], rx + 40 * (1 - q), ry, 1.0, q * ex)
            tt = Wt(wd)
            if t >= tt:
                q2 = (t - tt) / 0.22
                blit(f, g.tick, rx - 250 + 28 + 40 * (1 - q), ry, 0.3 + 0.7 * ease_back(q2, 3), min(1, q2 * 4) * ex)
    # tracking reticle on the face
    tt = Wt("tracking"); te = tt + 1.5
    if tt - 0.05 <= t < te:
        ex = min(1, (te - t) / 0.2)
        p = ease_out((t - tt + 0.05) / 0.3)
        fx, fy = src_to_out(cam, cam["fx"], cam["fy"])
        half = cam["fw"] / cam["k"] * 0.62 * (1 + 0.6 * (1 - p))
        L = half * 0.35
        blink = 1 if int(t * 8) % 2 == 0 or p < 1 else 0.6
        col = (255, 255, 255)
        lay = f.copy()
        for sgx in (-1, 1):
            for sgy in (-1, 1):
                x0, y0 = int(fx + sgx * half), int(fy + sgy * half)
                for off, c, th in ((3, (20, 20, 20), 7), (0, col, 5)):
                    cv2.line(lay, (x0 + off, y0 + off), (int(x0 - sgx * L) + off, y0 + off), c, th, cv2.LINE_AA)
                    cv2.line(lay, (x0 + off, y0 + off), (x0 + off, int(y0 - sgy * L) + off), c, th, cv2.LINE_AA)
        cv2.line(lay, (int(fx - 16), int(fy)), (int(fx + 16), int(fy)), col, 2, cv2.LINE_AA)
        cv2.line(lay, (int(fx), int(fy - 16)), (int(fx), int(fy + 16)), col, 2, cv2.LINE_AA)
        al = p * ex * blink
        f[:] = cv2.addWeighted(lay, al, f, 1 - al, 0)
        blit(f, g.trk, fx - half + g.trk.shape[1] / 2 - 30, fy - half - 36, 1.0, p * ex)
    # replacing / amplifying
    tr, ted, tam, te = Wt("replacing"), Wt("editor"), Wt("amplifying"), s2o(31.4)
    if tr - 0.02 <= t < te + 0.2:
        ex = 1 if t < te else max(0, 1 - (t - te) / 0.2)
        p = (t - tr + 0.02) / 0.25
        dim = 0.55 if t >= tam else 1
        blit(f, g.replacing, CX, BAND_Y - 60 + 30 * (1 - ease_out(p)), 0.6 + 0.4 * ease_back(p), min(1, p * 3) * ex * (0.85 * dim))
        if t >= ted - 0.05:
            q = ease_out((t - ted + 0.05) / 0.22)
            w2 = (g.replacing.shape[1] - 80) / 2 * 1.04
            x0, x1 = int(CX - w2), int(CX - w2 + 2 * w2 * q)
            y0 = int(BAND_Y - 60)
            lay = f.copy()
            cv2.line(lay, (x0, y0 + 4), (x1, y0 + 4), (20, 20, 20), 16, cv2.LINE_AA)
            cv2.line(lay, (x0, y0), (x1, y0), (255, 72, 72), 12, cv2.LINE_AA)
            al = ex * dim
            f[:] = cv2.addWeighted(lay, al, f, 1 - al, 0)
        if t >= tam - 0.04:
            q = (t - tam + 0.04) / 0.3
            rp = (t - tam) / 0.6
            if 0 <= rp < 1:
                lay = f.copy()
                cv2.ellipse(lay, (CX, BAND_Y + 95), (int(260 + 260 * ease_out(rp)), int(90 + 90 * ease_out(rp))), 0, 0, 360, ACCENT, 5, cv2.LINE_AA)
                al = (1 - rp) * ex
                f[:] = cv2.addWeighted(lay, al, f, 1 - al, 0)
            blit(f, g.amplifying, CX, BAND_Y + 95, 0.4 + 0.6 * ease_back(q, 2.5), min(1, q * 3) * ex)
    # dial into an aesthetic
    td, ta2, te = Wt("dial") - 0.08, Wt("aesthetic"), Wt("faster") - 0.02
    if td <= t < te + 0.15:
        ex = 1 if t < te else max(0, 1 - (t - te) / 0.15)
        p = ease_out((t - td) / 0.25)
        val = 0.87 * ease_io((t - td) / max(0.1, ta2 + 0.4 - td))
        spr = dial_sprite(val, True)
        blit(f, spr, CX, BAND_Y - 10, 0.5 + 0.5 * ease_back((t - td) / 0.3), p * ex, rot=-12 * (1 - p))
        if t >= ta2 - 0.03:
            q = (t - ta2 + 0.03) / 0.25
            blit(f, g.aesthetic, CX, BAND_Y + 160, 0.5 + 0.5 * ease_back(q), min(1, q * 3) * ex)
    # finale
    tf0 = Wt("It's", 36.5)
    if t >= tf0 - 0.03:
        tw = [Wt("It's", 36.5), Wt("all", 36.5), Wt("about", 36.5)]
        fnt = F_cap(76); advs = [fnt.getlength(s) for s in ("IT'S", "ALL", "ABOUT")]; sp = 22
        x = CX - (sum(advs) + 2 * sp) / 2
        yb = 1080 if t < BODY else 1080 - 70 * ease_io((t - BODY) / 0.5)
        for k in range(3):
            cx = x + advs[k] / 2; x += advs[k] + sp
            if t < tw[k] - 0.03: continue
            q = (t - tw[k] + 0.03) / 0.22
            blit(f, g.fin1[k], cx, yb + 24 * (1 - ease_out(q)), 0.45 + 0.55 * ease_back(q), min(1, q * 3))
        tfe = Wt("the", 37.1)
        if t >= tfe - 0.03:
            q = (t - tfe + 0.03) / 0.35
            pulse = 1 + 0.03 * math.sin(max(0, t - Wt("feeling", 37)) * 5) if t > Wt("feeling", 37) else 1
            blit(f, g.fin2, CX, yb + 175, (0.55 + 0.45 * ease_back(q)) * pulse, min(1, q * 3))
        if t >= BODY + 0.25:
            q = (t - BODY - 0.25) / 0.35
            blit(f, g.cta, CX, 1455, 0.5 + 0.5 * ease_back(q), min(1, q * 3))


# ------------------------------------------------------------------ frame
def frame_at(n, src_graded, track, chunks):
    t = n / FPS
    cam = camera(t, track)
    f = render_cam(src_graded[cam["fi"]], cam)
    # shot-change whips / zoom blur transitions
    for k, ts in enumerate(whip_ts):
        d = t - ts
        if -0.14 <= d < 0.14:
            a = ease_in(1 + d / 0.14) if d < 0 else 1 - ease_out(d / 0.14)
            if k == 0:
                f = np.roll(hblur(f, 140 * a), int((-1 if d < 0 else 1) * 260 * a), axis=1)
            else:
                f = zoom_blur(f, 2.2 * a)
    # colour-wipe demo on "color"
    tcol = Wt("color", 9)
    if tcol - 0.05 <= t < tcol + 1.4:
        p = ease_io((t - tcol + 0.05) / 0.45)
        back = ease_io((t - tcol - 0.7) / 0.6)
        strength = 1 - back
        vivid = saturate(f, 1 + 0.55 * strength, 0.9 * strength)
        xw = int(W * p)
        if xw > 0:
            f[:, :xw] = vivid[:, :xw]
        if 0 < p < 1:
            cv2.line(f, (xw, 0), (xw, H), (255, 255, 255), 4)
    # rack focus on "focus"
    tfo = Wt("focus")
    if tfo - 0.5 <= t < tfo + 0.2:
        d = t - tfo
        sig = 9 * ease_io((d + 0.5) / 0.38) if d < -0.12 else 9 * (1 - ease_out((d + 0.12) / 0.3))
        if sig > 0.3:
            f = cv2.GaussianBlur(f, (0, 0), sig)
    if cam["outro"]:
        f = cv2.GaussianBlur(f, (0, 0), 0.3 + 10 * ease_io((t - BODY) / 1.0))
        f = (f.astype(np.float32) * (1 - 0.45 * ease_io((t - BODY) / 0.8))).astype(np.uint8)
    # glitches
    gl = 0.0
    for t0, dur, I in ((Wt("different") - 0.02, 0.22, 0.6), (drop_t - 0.03, 0.14, 1.0), (Wt("AI", 18) - 0.02, 0.42, 0.85), (Wt("replacing"), 0.1, 0.35)):
        if t0 <= t < t0 + dur and (n % 3 != 1 or I > 0.9):
            gl = max(gl, I * (1 - 0.5 * (t - t0) / dur))
    if gl > 0:
        f = glitch(f, gl, n)
    # looks: light leaks, particles, speed lines
    leak = 0.0
    leak = max(leak, 0.38 * win(t, Wt("soul") - 0.2, s2o(7.84), 0.5, 0.35))
    for ts in whip_ts: leak = max(leak, 0.45 * max(0, 1 - abs(t - ts) / 0.3))
    leak = max(leak, 0.6 * max(0, 1 - (t - drop_t) / 0.5) if t >= drop_t else 0)
    leak = max(leak, 0.42 * win(t, Wt("It's", 36.5) - 0.2, DUR + 1, 0.6, 1))
    f = light_leak(f, leak, t)
    part = max(0.8 * win(t, Wt("soul") - 0.1, s2o(7.84) + 0.1, 0.4, 0.3), 0.9 * win(t, Wt("It's", 36.5), DUR + 1, 0.5, 1))
    f = particles(f, part, t)
    tfa = Wt("faster")
    if tfa - 0.03 <= t < tfa + 0.5:
        global SPEED
        if SPEED is None: SPEED = speed_lines()
        a = 0.85 * (1 - (t - tfa) / 0.5)
        sl = np.roll(SPEED, int(t * 997) % 40 - 20, axis=0)
        f = np.clip(f.astype(np.float32) + (sl * a * 255)[..., None], 0, 255).astype(np.uint8)
    # global finish: sharpen, vignette, grain
    f = sharpen(f)
    vs = 0.32 + 0.18 * win(t, tfo - 0.3, tfo + 1.6, 0.3, 0.5) + 0.12 * win(t, Wt("It's", 36.5), DUR + 1, 0.6, 1)
    f = vignette(f, vs)
    tx = Wt("texture")
    ga = 5.5 + 9 * win(t, tx - 0.03, tx + 0.7, 0.05, 0.4)
    f = add_grain(f, ga, n)
    # drop flash
    if drop_t - 0.02 <= t < drop_t + 0.35:
        a = 0.85 * (1 - ease_out((t - drop_t + 0.02) / 0.37))
        f = (f.astype(np.float32) * (1 - a) + 255 * a).astype(np.uint8)
    # overlays
    draw_graphics(f, t, cam)
    draw_captions(f, t, chunks)
    return f


def worker(wi, nw, src_graded, track, chunks, total, out_dir, only=None):
    build_graphics()
    frames = range(wi, total, 1) if only is None else only
    if only is None:
        per = math.ceil(total / nw)
        frames = range(wi * per, min(total, (wi + 1) * per))
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                              "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                              "-profile:v", "high", "-x264-params", "keyint=60", os.path.join(out_dir, f"chunk_{wi:02d}.mp4")],
                             stdin=subprocess.PIPE)
        for n in frames:
            p.stdin.write(frame_at(n, src_graded, track, chunks).tobytes())
        p.stdin.close(); p.wait()
    else:
        for n in frames:
            Image.fromarray(frame_at(n, src_graded, track, chunks)).save(os.path.join(out_dir, f"preview_{n:04d}.jpg"), quality=88)


if __name__ == "__main__":
    out_dir = os.path.join(S, "render"); os.makedirs(out_dir, exist_ok=True)
    raw, graded = load_source()
    track = face_track(len(graded))
    chunks = build_chunks()
    total = int(round(DUR * FPS))
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        times = [float(x) for x in sys.argv[2:]]
        worker(0, 1, graded, track, chunks, total, out_dir, only=[int(x * FPS) for x in times])
        sys.exit()
    nw = 4
    ps = [Process(target=worker, args=(i, nw, graded, track, chunks, total, out_dir)) for i in range(nw)]
    [p.start() for p in ps]; [p.join() for p in ps]
    with open(os.path.join(out_dir, "list.txt"), "w") as fh:
        for i in range(nw): fh.write(f"file 'chunk_{i:02d}.mp4'\n")
    final = os.path.join(S, "edited_final.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(out_dir, "list.txt"),
                    "-i", os.path.join(S, "audio", "final_mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final], check=True)
    print("wrote", final)
