"""Sprite + compositing helpers (all frames are RGB uint8, sprites RGBA uint8)."""
import numpy as np, cv2, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from functools import lru_cache
from timeline import S

FONT_DIR = os.path.join(S, "fonts")
ACCENT = (255, 181, 71)        # warm amber for graphic accents (captions stay white)


@lru_cache(None)
def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    if weight:
        f.set_variation_by_name(weight)
    return f


def F_cap(size):   return font("Montserrat.ttf", size, "Black")
def F_bold(size):  return font("Montserrat.ttf", size, "ExtraBold")
def F_semi(size):  return font("Montserrat.ttf", size, "SemiBold")
def F_title(size): return font("Anton.ttf", size)
def F_mono(size):  return font("Mono.ttf", size, "Bold")


def ease_out(p):  p = min(max(p, 0), 1); return 1 - (1 - p) ** 3
def ease_in(p):   p = min(max(p, 0), 1); return p ** 3
def ease_io(p):   p = min(max(p, 0), 1); return 3 * p * p - 2 * p * p * p
def ease_back(p, s=1.9):
    p = min(max(p, 0), 1); p -= 1
    return 1 + p * p * ((s + 1) * p + s)


def text_sprite(text, fnt, fill=(255, 255, 255), shadow=True, glow=0.0, stroke=3, pad=40, glow_col=None):
    """White text with layered shadow: dark outline, hard offset shadow, soft drop shadow, optional glow."""
    l, t, r, b = fnt.getbbox(text)
    w, h = r - l + pad * 2, b - t + pad * 2
    ox, oy = pad - l, pad - t
    base = Image.new("L", (w, h), 0)
    ImageDraw.Draw(base).text((ox, oy), text, font=fnt, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        soft = Image.new("L", (w, h), 0); soft.paste(base, (0, 10))
        soft = soft.filter(ImageFilter.GaussianBlur(14))
        out = Image.alpha_composite(out, Image.merge("RGBA", (*[Image.new("L", (w, h), 0)] * 3, soft.point(lambda v: int(v * 0.75)))))
        hard = Image.new("L", (w, h), 0); hard.paste(base, (4, 6))
        hard = hard.filter(ImageFilter.GaussianBlur(1.2))
        out = Image.alpha_composite(out, Image.merge("RGBA", (*[Image.new("L", (w, h), 0)] * 3, hard.point(lambda v: int(v * 0.55)))))
    if glow > 0:
        g = base.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(min(255, v * glow)))
        gc = glow_col or fill
        out = Image.alpha_composite(out, Image.merge("RGBA", (*[Image.new("L", (w, h), c) for c in gc], g)))
    if stroke:
        st_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(st_img).text((ox, oy), text, font=fnt, fill=(0, 0, 0, 0), stroke_width=stroke, stroke_fill=(20, 20, 24, 150))
        out = Image.alpha_composite(out, st_img)
    txt = Image.new("RGBA", (w, h), (*fill, 0))
    txt.putalpha(base)
    out = Image.alpha_composite(out, txt)
    return np.array(out)


def pill_sprite(text, fnt, bg=(12, 12, 16, 170), fg=(255, 255, 255), padx=34, pady=18, radius=None, border=(255, 255, 255, 60), icon=None):
    l, t, r, b = fnt.getbbox(text)
    tw, th = r - l, b - t
    iw = 0
    if icon: iw = th + 16
    w, h = tw + padx * 2 + iw, th + pady * 2
    sh = 30
    img = Image.new("RGBA", (w + sh * 2, h + sh * 2), (0, 0, 0, 0))
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((sh, sh + 8, sh + w, sh + h + 8), radius or h // 2, fill=140)
    m = m.filter(ImageFilter.GaussianBlur(12))
    img.putalpha(m)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((sh, sh, sh + w, sh + h), radius or h // 2, fill=bg, outline=border, width=2)
    if icon:
        icon(d, sh + padx, sh + pady, th)
    d.text((sh + padx + iw - l, sh + pady - t), text, font=fnt, fill=fg)
    return np.array(img)


def draw_check(d, x, y, s, col=(255, 255, 255), w=6):
    d.line([(x + s * 0.12, y + s * 0.55), (x + s * 0.4, y + s * 0.82), (x + s * 0.9, y + s * 0.18)], fill=col, width=w, joint="curve")


def draw_spark(d, cx, cy, r, col=(255, 255, 255, 255)):
    pts = []
    for k in range(8):
        a = np.pi / 4 * k
        rr = r if k % 2 == 0 else r * 0.28
        pts.append((cx + rr * np.cos(a), cy + rr * np.sin(a)))
    d.polygon(pts, fill=col)


def blit(frame, spr, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    """alpha-composite RGBA sprite centred at (cx, cy) with scale/rotation."""
    if alpha <= 0.003 or scale <= 0.01:
        return
    s = spr
    if abs(scale - 1) > 1e-3 or abs(rot) > 1e-3:
        h, w = spr.shape[:2]
        if abs(rot) > 1e-3:
            M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
            nw, nh = int(w * scale * 1.3) + 2, int(h * scale * 1.3) + 2
            M[0, 2] += nw / 2 - w / 2; M[1, 2] += nh / 2 - h / 2
            s = cv2.warpAffine(spr, M, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        else:
            s = cv2.resize(spr, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    h, w = s.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    H, W = frame.shape[:2]
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    sp = s[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0].astype(np.float32)
    a = sp[..., 3:4] * (alpha / 255.0)
    roi = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    frame[fy0:fy1, fx0:fx1] = (roi * (1 - a) + sp[..., :3] * a).astype(np.uint8)


def canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))
