# Scroll 3D Demo

A small, original recreation of the scroll-driven 3D technique used on
[Shopify Editions Winter '26](https://www.shopify.com/editions/winter2026). No Shopify
assets are used; both scenes are generated in code.

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production build in dist/
```

URL flags: `#debug` (or `?debug`) shows the scroll-to-timeline mapping, `#fallback` forces the
static no-WebGL version.

## How it works

```
scrollY ──Lenis (smoothed)──► screens = scroll / innerHeight
                                   │
                                   ▼
                     GSAP timeline.seek(screens)   ← keyframes, never "played"
                                   │ writes plain state objects
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
     hero scene → render target A        armillary scene → render target B
                 └──────────► composite shader ◄─────┘
                         (noise reveal + glowing rim)
                                   │
                         bloom pass → tone mapping → <canvas>
```

| File | Role |
| --- | --- |
| `src/main.js` | Renderer, render targets, post-processing, Lenis and the frame loop |
| `src/timeline.js` | All keyframes, in "screens scrolled" units |
| `src/composite.js` | GLSL transition between the two offscreen scenes |
| `src/scenes/hero.js` | Colonnade and golden orb |
| `src/scenes/armillary.js` | Night sky and armillary sphere whose rings open |
| `src/scenes/common.js` | Sky gradient, particles, and pointer "gaze" camera helper |

Key ideas, all mirrored from the reference site:

1. **Fixed canvas, normal HTML.** The canvas is `position: fixed` behind the page. Text
   sections scroll over it; the final opaque "paper" section covers it, and rendering stops
   once it does.
2. **Scroll scrubs a timeline.** The timeline is paused. Every frame it is seeked to the
   current scroll position, so scrolling backwards plays the animation backwards.
3. **Offscreen scenes plus a composite pass.** Each scene renders to its own half-float
   render target. A full-screen shader blends them along a noise-warped edge. Only the
   scenes that are visible are rendered.
4. **Pointer gaze.** The pointer orbits each camera a few degrees around its keyframed
   target, eased every frame.
5. **Fallbacks.** No WebGL 2, `prefers-reduced-motion`, or a lost context switches to a
   static CSS background.

## Taking it further

- **Real models:** export `.glb` files from Blender, compress them with
  `gltf-transform` (Draco geometry, KTX2 textures), and load them with three's
  `GLTFLoader` + `DRACOLoader` + `KTX2Loader`.
- **Visual keyframing:** replace `timeline.js` with a [Theatre.js](https://www.theatrejs.com/)
  sheet, as the reference site does, and set `sheet.sequence.position` from scroll.
- **React:** the same loop maps onto React Three Fiber with `useFrame`.
