"""Shared edit decision list: kept source ranges, source<->output time mapping, word timings."""
import json, os
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
W, H = 1080, 1920
# kept source ranges (seconds) -- pauses tightened, cuts land inside detected silence
KEEP = [(0.18, 4.25), (4.42, 6.21), (6.34, 7.84), (8.00, 14.04), (14.26, 17.70),
        (18.06, 27.67), (28.00, 33.85), (34.00, 36.42), (36.57, 38.0)]
SHOT_STARTS = [8.0, 18.0, 28.0]          # real camera cuts in source
OUTRO = 1.6                               # seconds of designed outro after last frame

_cum = []; t = 0.0
for a, b in KEEP:
    _cum.append(t); t += b - a
BODY = t
DUR = BODY + OUTRO

def s2o(ts):
    """source time -> output time (snaps into nearest kept range)."""
    for (a, b), c in zip(KEEP, _cum):
        if ts < a: return c
        if ts <= b: return c + ts - a
    return BODY

def o2s(to):
    """output time -> (source time, segment index); None during outro."""
    for i, ((a, b), c) in enumerate(zip(KEEP, _cum)):
        if to < c + (b - a): return a + max(0.0, to - c), i
    return None, len(KEEP) - 1

def seg_starts_out():
    return list(_cum)

WORDS = json.load(open(os.path.join(S, "words.json")))
for i, w in enumerate(WORDS):
    w["os"] = s2o(w["s"])
    nxt = WORDS[i + 1]["s"] if i + 1 < len(WORDS) else 37.8
    w["oe"] = s2o(min(nxt, w["s"] + 0.9))

def word_t(text, after=0.0):
    """output start time of first word whose stripped text == text, at/after source time `after`."""
    for w in WORDS:
        if w["s"] >= after and w["w"].strip(".,!?").lower() == text.lower():
            return w["os"]
    raise KeyError(text)

if __name__ == "__main__":
    print("body", round(BODY, 3), "total", round(DUR, 3))
    print("seg starts", [round(c, 2) for c in _cum])
    for k in ["vibe", "texture", "color", "pacing", "This", "AI", "denoising", "tracking", "focus", "amplifying", "dial", "faster", "feeling"]:
        print(k, round(word_t(k), 2))
