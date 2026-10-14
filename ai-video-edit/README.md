# AI video edit: "Vibe Editing" talking-head reel

Source: a 38 s, 1280×720 / 24 fps talking-head clip in a white studio, shot from 4 camera angles.

## Outputs (`output/`)
| File | What it is |
|---|---|
| `vibe_editing_reel_edited.mp4` | Full edit, 1080×1920 9:16, 30 fps, H.264 + AAC, −14 LUFS, 37.7 s |
| `comparison_reel_fully_edited_by_ai.mp4` | Raw and edited side by side, titled "Fully Edited by AI", with all text inside the Instagram Reels safe zone |

## What the edit does
- **Reframe:** 16:9 → 9:16 crop that follows the face (face detection, smoothed per shot).
- **Pacing:** pauses tightened (about 1.9 s removed). The jump cuts are hidden with alternating zoom levels.
- **Color:** filmic S-curve, lifted blacks, warm highlights and teal shadows, a slight saturation boost, sharpening, vignette and film grain.
- **Camera motion:** opening zoom-out, a slow push-in, punch-in zooms on key words, handheld drift and camera shake on impacts.
- **Transitions:** a whip pan with motion blur (cut 1), a white flash with a zoom slam on the beat drop (cut 2), and a zoom blur (cut 3).
- **Captions:** word-by-word kinetic captions in white Montserrat Black. Each word pops in with overshoot, and the active word scales up and glows. The text has layered shadows (soft drop shadow, hard offset shadow and an outline) so it stays readable on the white set.
- **Motion graphics:** a hook pill and "VIBE EDITING" slam title; TEXTURE / COLOR / PACING chips; a live color-grade wipe on "color"; a grain spike on "texture"; zoom pulses on "pacing"; LOOKS GOOD vs FEELS RIGHT; a glitch "AI" title; an "AI HANDLES" checklist; a face-tracking reticle on "tracking"; a rack focus on "focus"; the word REPLACING struck through, then AMPLIFYING; an aesthetic dial; speed lines on "faster"; a finale title and a "Follow for more" end card.
- **FX:** RGB-split and slice glitches, light leaks and floating bokeh particles.
- **Audio:**
  - Voice cleanup: high-pass filter, denoise, EQ, compression.
  - Original lo-fi score at 96 BPM (pads, bass and drums, plus vinyl crackle). It builds up to a drop on "This is where AI changes the game" and ducks under the voice.
  - 30+ synthesized SFX: whooshes, impacts, pops, ticks, glitches, a riser, shimmers, dings, a ratchet and scan beeps.
  - Mastered to −14 LUFS with a −1 dBTP ceiling.

## Rebuild
Run the following inside `scripts/`:
1. `python3 audio.py`
2. `python3 render.py`
3. `python3 compare.py`

The scripts need `raw.mp4`, plus fonts (Montserrat, Anton and JetBrains Mono from google/fonts) in `fonts/` next to `scripts/`. They also need the Python packages opencv-python-headless 4.10, scipy and pillow.

Transcription used sherpa-onnx with NVIDIA Parakeet-TDT 0.6B (`asr.py`).
