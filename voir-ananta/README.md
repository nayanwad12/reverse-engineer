# VOIR ANANTA — Edition 01 · Infinite Raga

Immersive single-page site for VOIR ANANTA, the wearable-art competition and live
experience by VOIRTALES.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # static site in dist/
```

`#fallback` (or `?fallback`) shows the static version used when WebGL 2 is unavailable.

## How it works

- **One particle sculpture, many forms.** `src/shapes.js` bakes 65,536 points into 14
  procedural forms (infinity ribbon, wire-wound gown, nine-rasa mandala, torus knot and
  sound rings, folded material sheet with a red thread, fingerprint, stage and spotlight,
  galaxy, 20 pillars, six lenses, journey helix, eye, sphere). Positions and colours live
  in two data textures; the GPU morphs between any two forms with a per-particle stagger
  and a turbulent swirl (`src/particles.js`).
- **Chapters drive the camera.** Each `<section data-scene>` maps to a preset in
  `src/scenes.js` (form, camera, offset, spin, backdrop colours). Scroll position is turned
  into a fractional chapter index and everything is interpolated from it (`src/main.js`).
- **Interaction.** Hovering a rasa, category, material, finalist count or lens lights up
  its points in the sculpture. The pointer parts the particles. The Tanpura button plays a
  synthesized drone (Pa–Sa–Sa–low Sa) and the field pulses with each pluck.
- **Post-processing.** Unreal bloom, then a lens pass with chromatic fringing, grain and
  vignette.
- **Fallbacks.** Reduced motion calms the field and disables smooth scrolling; no WebGL 2
  shows a static gradient. Phones draw fewer particles and pull the camera back.

## Placeholders to fill

- Partnership email (`[EMAIL]` in section 15).
- Registration form link: the Register button currently explains that registration opens
  on 25 October 2026.
