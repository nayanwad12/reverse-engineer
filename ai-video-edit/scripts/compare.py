"""Side-by-side RAW vs EDITED comparison reel, all content inside the Instagram Reels safe zone."""
import numpy as np, cv2, os, subprocess, math
from PIL import Image, ImageDraw, ImageFilter
from timeline import S, FPS, W, H, DUR, o2s
from gfx import *
from render import face_track

CX = 520
PW, PH = 440, 782
PY = 935
LX, RX = CX - PW / 2 - 12, CX + PW / 2 + 12


def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return np.array(m, np.float32)[..., None] / 255


def frame_border(w, h, r, col, width):
    im = canvas(w + 80, h + 80)
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((40, 52, 40 + w, 52 + h), r, fill=170)
    im.putalpha(sh.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(im).rounded_rectangle((40 - width, 40 - width, 40 + w + width, 40 + h + width), r + width, outline=col, width=width)
    return np.array(im)


def background(t):
    yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    bg = np.zeros((H // 4, W // 4, 3), np.float32) + np.array([11, 11, 15], np.float32)
    for col, bx, by, r in (((255, 150, 50), 0.15 + 0.08 * math.sin(t * 0.6), 0.22, 90),
                           ((140, 80, 255), 0.85 + 0.08 * math.cos(t * 0.5), 0.75 + 0.05 * math.sin(t * 0.7), 110)):
        gg = np.exp(-(((xx - bx * W / 4) ** 2 + (yy - by * H / 4) ** 2) / (2 * r ** 2)))
        bg += gg[..., None] * np.array(col, np.float32) * 0.28
    return cv2.resize(np.clip(bg, 0, 255).astype(np.uint8), (W, H))


def main():
    cap = cv2.VideoCapture(os.path.join(S, "raw.mp4")); raw = []
    while True:
        ok, f = cap.read()
        if not ok: break
        raw.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    track = face_track(len(raw))
    ed = cv2.VideoCapture(os.path.join(S, "edited_final.mp4"))
    mask = rounded_mask(PW, PH, 30)
    b_raw = frame_border(PW, PH, 30, (255, 255, 255, 90), 3)
    b_ed = frame_border(PW, PH, 30, (*ACCENT, 255), 4)
    words = [("Fully", (255, 255, 255), 0.0), ("Edited", (255, 255, 255), 0.0), ("by", (255, 255, 255), 0.0), ("AI", (255, 255, 255), 1.3)]
    tf = F_cap(84)
    wspr = [text_sprite(w, tf, fill=c, glow=gl, glow_col=ACCENT, stroke=3) for w, c, gl in words]
    advs = [tf.getlength(w) for w, _, _ in words]
    sp = 24
    sub = text_sprite("CAPTIONS · MOTION GFX · SFX · MUSIC · COLOR", F_mono(25), fill=(225, 225, 225), shadow=False, stroke=0)
    lab_raw = pill_sprite("RAW FOOTAGE", F_bold(32), bg=(30, 30, 36, 230))
    lab_ed = pill_sprite("AI EDIT", F_bold(32), bg=(*ACCENT, 255), fg=(18, 18, 22), border=(255, 255, 255, 0),
                         icon=lambda d, x, y, s: draw_spark(d, x + s / 2, y + s / 2, s / 2, (18, 18, 22, 255)))
    vs = canvas(110, 110); d = ImageDraw.Draw(vs)
    d.ellipse((10, 10, 100, 100), fill=(255, 255, 255, 255))
    l, t_, r, b = F_title(40).getbbox("VS"); d.text((55 - (r - l) / 2 - l, 55 - (b - t_) / 2 - t_), "VS", font=F_title(40), fill=(18, 18, 22))
    vs = np.array(vs)

    total = int(round(DUR * FPS))
    out = os.path.join(S, "comparison_reel.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", os.path.join(S, "audio", "final_mix.wav"), "-map", "0:v", "-map", "1:a",
                          "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
                          "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for n in range(total):
        t = n / FPS
        f = background(t)
        ok, e = ed.read()
        e = cv2.cvtColor(e, cv2.COLOR_BGR2RGB) if ok else e_last
        e_last = e
        src, _ = o2s(t)
        fi = min(int((src if src is not None else 37.95) * 24), len(raw) - 1)
        cw = 405; cx = int(np.clip(track[0][fi], cw / 2, 1280 - cw / 2))
        rp = cv2.resize(raw[fi][:, cx - cw // 2:cx - cw // 2 + cw], (PW, PH), interpolation=cv2.INTER_AREA)
        ep = cv2.resize(e, (PW, PH), interpolation=cv2.INTER_AREA)
        intro = ease_out(t / 0.6)
        for spr, panel, x, k in ((b_raw, rp, LX, 0), (b_ed, ep, RX, 1)):
            q = ease_out((t - 0.1 - 0.12 * k) / 0.5)
            yoff = int(80 * (1 - q))
            blit(f, spr, x, PY + yoff, 1.0, q)
            x0, y0 = int(x - PW / 2), int(PY - PH / 2) + yoff
            roi = f[y0:y0 + PH, x0:x0 + PW].astype(np.float32)
            a = mask * q
            f[y0:y0 + PH, x0:x0 + PW] = (roi * (1 - a) + panel.astype(np.float32) * a).astype(np.uint8)
        blit(f, vs, CX, PY, 0.4 + 0.6 * ease_back((t - 0.5) / 0.35), min(1, max(0, (t - 0.5) / 0.15)))
        # labels under panels
        for spr, x, k in ((lab_raw, LX, 0), (lab_ed, RX, 1)):
            q = (t - 0.55 - 0.1 * k) / 0.35
            if q > 0: blit(f, spr, x, PY + PH / 2 + 62, 0.5 + 0.5 * ease_back(q), min(1, q * 3))
        # title: kinetic word pop, then gentle breathing
        x = CX - (sum(advs) + sp * 3) / 2
        for k, spr in enumerate(wspr):
            c = x + advs[k] / 2; x += advs[k] + sp
            q = (t - 0.05 - 0.14 * k) / 0.3
            if q <= 0: continue
            br = 1 + (0.035 * math.sin(t * 3) if k == 3 and q > 1 else 0)
            blit(f, spr, c, 335 + 30 * (1 - ease_out(q)), (0.4 + 0.6 * ease_back(q, 2.4)) * br, min(1, q * 3))
        q = (t - 0.8) / 0.4
        if q > 0: blit(f, sub, CX, 425, 1.0, min(1, q))
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
