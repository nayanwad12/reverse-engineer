// Particle "sculptures". Every shape places the same COUNT points, so the GPU can
// morph any shape into any other by blending two rows of a data texture.
//
// Position texture: xyz + group id (w). Group ids let the page highlight subsets,
// e.g. one rasa's cluster in the mandala.
// Colour texture: sRGB rgb + size multiplier (a).

export const SIZE = 256
export const COUNT = SIZE * SIZE

// The nine rasas, coloured after the Natya Shastra's rasa palette.
// Shanta was added to the canon later; it takes moonlight white here.
export const RASAS = [
  { name: 'Shringara', deva: 'शृङ्गार', meaning: 'Beauty / Love', hue: 'Śyāma', hex: '#2fae8c' },
  { name: 'Hasya', deva: 'हास्य', meaning: 'Joy', hue: 'Sita · white', hex: '#f6f1e6' },
  { name: 'Karuna', deva: 'करुण', meaning: 'Compassion / Sorrow', hue: 'Kapota · dove grey', hex: '#a3acb8' },
  { name: 'Raudra', deva: 'रौद्र', meaning: 'Intensity / Anger', hue: 'Rakta · red', hex: '#e2283f' },
  { name: 'Veera', deva: 'वीर', meaning: 'Courage', hue: 'Gaura · wheat gold', hex: '#eaa64c' },
  { name: 'Bhayanaka', deva: 'भयानक', meaning: 'Fear', hue: 'Kṛṣṇa · black', hex: '#6a55a8' },
  { name: 'Bibhatsa', deva: 'बीभत्स', meaning: 'Disquiet', hue: 'Nīla · blue', hex: '#2f63d6' },
  { name: 'Adbhuta', deva: 'अद्भुत', meaning: 'Wonder', hue: 'Pīta · yellow', hex: '#f3d43b' },
  { name: 'Shanta', deva: 'शान्त', meaning: 'Peace', hue: 'Moonlight', hex: '#cfe6ff' },
]

const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
const RASA_RGB = RASAS.map((r) => rgb(r.hex))
const C = {
  ivory: rgb('#f3e9d6'),
  gold: rgb('#e6b45e'),
  copper: rgb('#d07a3e'),
  ember: rgb('#e2553a'),
  steel: rgb('#a9bccc'),
  wood: rgb('#9a6338'),
  leaf: rgb('#7f9e4f'),
  kraft: rgb('#cdb284'),
  dusk: rgb('#8a6fd0'),
  ice: rgb('#dcecff'),
  blue: rgb('#5d8dff'),
  night: rgb('#4a3d78'),
}

const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]
const scale = (a, k) => [a[0] * k, a[1] * k, a[2] * k]
const clamp01 = (x) => Math.min(1, Math.max(0, x))
const TAU = Math.PI * 2

// Colour sampled cyclically along the nine rasa colours.
function rasaGradient(u) {
  const f = (((u % 1) + 1) % 1) * 9
  const i = Math.floor(f)
  return mix(RASA_RGB[i], RASA_RGB[(i + 1) % 9], f - i)
}

function rng(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function gaussian(r) {
  let u = 0
  while (u === 0) u = r()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * r())
}

// Reusable point being written by a shape function.
const P = { x: 0, y: 0, z: 0, g: -1, c: C.ivory, s: 1 }
function set(x, y, z, c, s = 1, g = -1) {
  P.x = x
  P.y = y
  P.z = z
  P.c = c
  P.s = s
  P.g = g
}

// Point on a tube of twisted strands around a parametric curve.
function tubePoint(curve, t, strandAngle, radius) {
  const e = 0.002
  const a = curve(t - e)
  const b = curve(t + e)
  const p = curve(t)
  let tx = b[0] - a[0]
  let ty = b[1] - a[1]
  let tz = b[2] - a[2]
  const tl = Math.hypot(tx, ty, tz) || 1
  tx /= tl
  ty /= tl
  tz /= tl
  // normal = normalize(T x up), binormal = T x normal
  let nx = ty * 1 - tz * 0
  let ny = tz * 0 - tx * 1
  let nz = tx * 0 - ty * 0
  if (Math.hypot(nx, ny, nz) < 1e-3) {
    nx = 0
    ny = tz
    nz = -ty
  }
  const nl = Math.hypot(nx, ny, nz) || 1
  nx /= nl
  ny /= nl
  nz /= nl
  const bx = ty * nz - tz * ny
  const by = tz * nx - tx * nz
  const bz = tx * ny - ty * nx
  const c = Math.cos(strandAngle) * radius
  const s = Math.sin(strandAngle) * radius
  return [p[0] + nx * c + bx * s, p[1] + ny * c + by * s, p[2] + nz * c + bz * s]
}

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

const lemniscate = (t) => {
  const s = Math.sin(t)
  const c = Math.cos(t)
  const d = 1 + s * s
  return [(3.4 * c) / d, ((3.4 * s * c) / d) * 1.2, Math.sin(t) * 0.6]
}

function infinity(i, r) {
  if (r() < 0.9) {
    const t = r() * TAU
    const strand = Math.floor(r() * 56)
    const radius = 0.34 * (0.8 + 0.2 * Math.sin(t * 6)) + gaussian(r) * 0.012
    const p = tubePoint(lemniscate, t, (strand / 56) * TAU + t * 5, radius)
    const bright = strand % 7 === 0
    const c = rasaGradient(t / TAU + 0.05)
    set(p[0], p[1], p[2], bright ? mix(c, C.ivory, 0.5) : c, bright ? 1.5 : 1)
  } else {
    const p = lemniscate(r() * TAU)
    const k = 0.55
    set(p[0] + gaussian(r) * k, p[1] + gaussian(r) * k, p[2] + gaussian(r) * k, scale(C.ivory, 0.45), 0.6)
  }
}

// Silhouette radius of the sculptural gown, by height.
const GOWN = [
  [-3.0, 2.05], [-2.6, 1.8], [-2.0, 1.4], [-1.4, 1.05], [-0.8, 0.72], [-0.25, 0.48],
  [0.3, 0.55], [0.7, 0.66], [0.95, 1.3], [1.08, 1.32], [1.16, 0.62], [1.45, 0.22],
  [1.62, 0.17], [1.75, 0.27], [2.0, 0.33], [2.22, 0.29], [2.42, 0.0],
]
function gownRadius(y) {
  if (y <= GOWN[0][0]) return GOWN[0][1]
  for (let k = 1; k < GOWN.length; k++) {
    if (y <= GOWN[k][0]) {
      const [y0, r0] = GOWN[k - 1]
      const [y1, r1] = GOWN[k]
      const f = (y - y0) / (y1 - y0)
      return r0 + (r1 - r0) * (f * f * (3 - 2 * f))
    }
  }
  return 0
}

function gownPoint(r, k = 1, ox = 0, oy = 0, oz = 0) {
  const roll = r()
  let x, y, z, c, s
  if (roll < 0.55) {
    // Triple helix of copper wire wound around the body.
    const u = r()
    y = -3 + u * 5.35
    const strand = Math.floor(r() * 3)
    const th = u * TAU * 24 + (strand * TAU) / 3 + gaussian(r) * 0.02
    let rad = gownRadius(y)
    if (y < -0.4) rad *= 1 + 0.16 * Math.sin(th * 7 + y * 2.5) * clamp01((-0.4 - y) / 2.6)
    x = rad * Math.cos(th)
    z = rad * Math.sin(th)
    c = mix(C.copper, C.gold, u)
    s = 1.05
  } else if (roll < 0.85) {
    // Paper skin.
    y = -3 + Math.pow(r(), 0.85) * 5.4
    const th = r() * TAU
    let rad = gownRadius(y) * (0.97 + r() * 0.05)
    if (y < -0.4) rad *= 1 + 0.16 * Math.sin(th * 7 + y * 2.5) * clamp01((-0.4 - y) / 2.6)
    x = rad * Math.cos(th)
    z = rad * Math.sin(th)
    c = scale(C.ivory, 0.75)
    s = 0.7
  } else {
    // Sunburst crown: a ring with radial spikes.
    const th = r() * TAU
    if (r() < 0.5) {
      const rad = 0.95 + gaussian(r) * 0.015
      x = Math.cos(th) * rad
      y = 2.25 + Math.sin(th) * rad * 0.28
      z = Math.sin(th) * rad * 0.96
    } else {
      const spike = Math.floor(r() * 28)
      const a = (spike / 28) * TAU
      const len = 0.35 + r() * (spike % 2 ? 0.55 : 0.95)
      x = Math.cos(a) * len
      y = 2.0 + Math.sin(a) * len
      z = gaussian(r) * 0.02
    }
    c = C.gold
    s = 1.4
  }
  set(x * k + ox, (y + 0.25) * k + oy, z * k + oz, c, s)
}

function garment(i, r) {
  gownPoint(r)
}

function mandala(i, r) {
  if (r() < 0.9) {
    const k = i % 9
    const a = Math.PI / 2 - (k * TAU) / 9
    const cx = Math.cos(a) * 2.55
    const cy = Math.sin(a) * 2.55
    const phi = r() * TAU
    const petal = 0.7 * Math.pow(Math.abs(Math.cos(2.5 * phi)), 0.55) * Math.sqrt(r())
    const lx = Math.cos(phi + a) * petal
    const ly = Math.sin(phi + a) * petal
    const core = 1 - petal / 0.7
    const c = scale(mix(RASA_RGB[k], C.ivory, core * core * 0.15), 0.8)
    set(cx + lx, cy + ly, core * 0.3 + gaussian(r) * 0.05, c, 1 + core * 0.4, k)
  } else {
    const th = r() * TAU
    const ring = r() < 0.6 ? 2.55 : 1.15
    set(Math.cos(th) * ring, Math.sin(th) * ring, gaussian(r) * 0.04, scale(C.gold, 0.6), 0.6)
  }
}

const knot = (t) => {
  const rr = Math.cos(3 * t) + 2
  return [rr * Math.cos(2 * t) * 0.62, rr * Math.sin(2 * t) * 0.62, -Math.sin(3 * t) * 0.62]
}

function split(i, r) {
  if (i % 2 === 0) {
    // RAGA / FORM: a torus knot of twisted strands.
    const t = r() * TAU
    const strand = Math.floor(r() * 24)
    const p = tubePoint(knot, t, (strand / 24) * TAU + t * 3, 0.24)
    set(p[0] - 2.4, p[1], p[2], mix(C.ember, C.gold, (Math.sin(t * 2) + 1) / 2), 1, 20)
  } else {
    // RAGA / VOICE: rippling sound rings.
    const j = Math.floor(r() * 30)
    const base = 0.22 + j * 0.068
    const phi = r() * TAU
    const rad = base * (1 + 0.16 * Math.sin(phi * (3 + (j % 5)) + j) * (j / 30))
    set(
      Math.cos(phi) * rad + 2.4,
      Math.sin(phi) * rad,
      Math.sin(base * 7) * 0.2 + gaussian(r) * 0.01,
      mix(C.blue, C.ice, j / 30),
      0.95,
      21,
    )
  }
}

// Folded sheet: 95% unconventional material, 5% red textile thread.
const MATERIALS = [C.ivory, C.steel, C.copper, C.wood, C.leaf, C.kraft, C.steel]
const SEEDS = [[-1.8, 0.9], [-0.6, -0.8], [0.7, 0.6], [1.9, -0.7], [-2.2, -1.0], [0.1, 1.4], [2.2, 1.1]]
const crease = (x, y) =>
  0.42 * Math.abs(Math.sin(x * 1.15 + y * 0.55)) -
  0.3 * Math.abs(Math.sin(y * 1.9 - x * 0.45 + 1.0)) +
  0.12 * Math.sin(x * 3.1) * Math.cos(y * 2.7)

function rotateSheet(x, y, z) {
  const ax = -0.55
  const ay = 0.35
  const y1 = y * Math.cos(ax) - z * Math.sin(ax)
  const z1 = y * Math.sin(ax) + z * Math.cos(ax)
  const x2 = x * Math.cos(ay) + z1 * Math.sin(ay)
  const z2 = -x * Math.sin(ay) + z1 * Math.cos(ay)
  return [x2, y1, z2]
}

function material(i, r) {
  if (r() < 0.95) {
    const u = (i % SIZE) / (SIZE - 1)
    const v = Math.floor(i / SIZE) / (SIZE - 1)
    const x = (u - 0.5) * 5.4 + gaussian(r) * 0.006
    const y = (v - 0.5) * 3.8 + gaussian(r) * 0.006
    let best = 0
    let bestD = Infinity
    SEEDS.forEach(([sx, sy], k) => {
      const d = (x - sx) ** 2 + (y - sy) ** 2
      if (d < bestD) {
        bestD = d
        best = k
      }
    })
    const p = rotateSheet(x, y, crease(x, y))
    const metal = best === 1 || best === 6
    set(p[0], p[1], p[2], scale(MATERIALS[best], metal ? 0.95 : 0.7), metal ? 1.05 : 0.8, 30 + best)
  } else {
    const s = r()
    if ((s * 70) % 1 > 0.62) return material(i, r)
    const x = -2.7 + s * 5.4
    const y = Math.sin(s * Math.PI * 3) * 1.25
    const p = rotateSheet(x, y, crease(x, y) + 0.05)
    set(p[0], p[1], p[2], C.ember, 1.6, 39)
  }
}

function fingerprint(i, r) {
  for (let attempt = 0; attempt < 12; attempt++) {
    const roll = r()
    let x, y
    if (roll < 0.62) {
      const ring = Math.floor(r() * 32)
      const rr = 0.12 + ring * 0.052
      const phi = r() * TAU
      // Minutiae: occasional ridge breaks.
      const seg = Math.floor((phi / TAU) * 9)
      if (Math.sin(ring * 12.9898 + seg * 78.233) * 43758.5453 % 1 > 0.82) continue
      x = Math.cos(phi) * rr * 0.86 + 0.07 * Math.sin(phi * 3 + ring * 0.45)
      y = 0.35 + Math.sin(phi) * rr * 1.12
    } else if (roll < 0.85) {
      const j = Math.floor(r() * 20)
      const s = r() * 2 - 1
      x = s * 1.9
      y = -1.5 - j * 0.058 + 0.62 * (1 - s * s)
    } else {
      const j = Math.floor(r() * 14)
      const s = r() * 2 - 1
      x = s * 1.9
      y = 2.15 + j * 0.06 - 0.5 * s * s
    }
    const e = (x / 1.95) ** 2 + ((y - 0.15) / 2.75) ** 2
    if (e > 1) continue
    const z = 0.55 * (1 - e) + gaussian(r) * 0.01
    const center = clamp01(1 - Math.hypot(x, y - 0.35) / 2)
    set(x, y, z, scale(mix(C.ivory, C.gold, center * 0.8), 0.6), 1, 40)
    return
  }
  set(gaussian(r) * 1.4, gaussian(r) * 1.8, gaussian(r) * 0.4, scale(C.gold, 0.35), 0.5)
}

function stage(i, r) {
  const roll = r()
  if (roll < 0.36) {
    const ring = Math.floor(r() * 30)
    const rad = 0.12 + ring * 0.106
    const th = r() * TAU
    set(Math.cos(th) * rad, -1.85, Math.sin(th) * rad, scale(mix(C.wood, C.gold, ring / 30), 0.8), 0.8)
  } else if (roll < 0.62) {
    const h = Math.pow(r(), 0.8)
    const y = 3.8 - h * 5.6
    const rad = h * 1.55 * Math.sqrt(r())
    const th = r() * TAU
    set(Math.cos(th) * rad, y, Math.sin(th) * rad, scale(C.ivory, 0.55 + (1 - h) * 0.4), 0.8)
  } else if (roll < 0.8) {
    // Edge ring with five bright arcs: five minutes on stage.
    const th = r() * TAU
    const tick = (th % (TAU / 5)) / (TAU / 5) < 0.14
    set(Math.cos(th) * 3.45, -1.8, Math.sin(th) * 3.45, tick ? C.gold : scale(C.gold, 0.3), tick ? 1.8 : 0.6)
  } else {
    gownPoint(r, 0.42, 0, -0.9, 0)
  }
}

function constellation(i, r) {
  let x, y, z, c, s
  if (r() < 0.97) {
    const d = Math.pow(r(), 1.5) * 3.8
    const arm = i % 4
    const a = (arm * TAU) / 4 + d * 1.3 + (gaussian(r) * 0.28) / (d + 0.5)
    x = Math.cos(a) * d
    z = Math.sin(a) * d
    y = gaussian(r) * 0.14 * (1 - d / 4.5)
    c = mix(C.gold, rasaGradient(r()), clamp01(d / 3.2))
    s = 0.85
  } else {
    // Fourteen bright nodes: the fourteen disciplines named on the page.
    const n = i % 14
    const d = 0.9 + (n / 14) * 2.6
    const a = ((n % 4) * TAU) / 4 + d * 1.3
    x = Math.cos(a) * d + gaussian(r) * 0.06
    z = Math.sin(a) * d + gaussian(r) * 0.06
    y = gaussian(r) * 0.06
    c = C.ivory
    s = 2.0
  }
  const tilt = 1.05
  set(x, y * Math.cos(tilt) - z * Math.sin(tilt), y * Math.sin(tilt) + z * Math.cos(tilt), c, s, 41)
}

function pillars(i, r) {
  const roll = r()
  if (roll < 0.86) {
    const col = i % 20
    const a = (col / 20) * TAU
    const rad = 0.09 * Math.sqrt(r())
    const th = r() * TAU
    const y = -2 + Math.pow(r(), 1.3) * 4
    const form = col % 2 === 0
    const c = form ? C.gold : C.blue
    set(
      Math.cos(a) * 3 + Math.cos(th) * rad,
      y,
      Math.sin(a) * 3 + Math.sin(th) * rad,
      scale(c, 0.55 + 0.6 * (1 - (y + 2) / 4)),
      1,
      form ? 50 : 51,
    )
  } else if (roll < 0.95) {
    const th = r() * TAU
    const rad = 3 + gaussian(r) * 0.05
    set(Math.cos(th) * rad, -2.02, Math.sin(th) * rad, scale(C.ivory, 0.35), 0.6)
  } else {
    // Two category winners.
    const gold = r() < 0.5
    const u = r() * 2 - 1
    const th = r() * TAU
    const k = Math.sqrt(1 - u * u) * 0.32
    set((gold ? -0.55 : 0.55) + Math.cos(th) * k, 0.4 + u * 0.32, Math.sin(th) * k, gold ? C.gold : C.ice, 1.5)
  }
}

function lenses(i, r) {
  const k = i % 7
  const th = r() * TAU
  const rad = 1.22 + gaussian(r) * 0.018
  let cx = 0
  let cy = 0
  if (k < 6) {
    const a = Math.PI / 2 - (k * TAU) / 6
    cx = Math.cos(a) * 1.22
    cy = Math.sin(a) * 1.22
  }
  const c = k < 6 ? mix(C.ivory, C.gold, k / 5) : scale(C.ivory, 0.6)
  set(cx + Math.cos(th) * rad, cy + Math.sin(th) * rad, Math.sin(th * 3 + k) * 0.14, c, k < 6 ? 1 : 0.7, k < 6 ? 60 + k : -1)
}

function helix(i, r) {
  const roll = r()
  if (roll < 0.86) {
    const s = r()
    const th = s * TAU * 3.25
    const rad = 1.7 + gaussian(r) * 0.025
    set(Math.cos(th) * rad, 3 - s * 6 + (r() - 0.5) * 0.2, Math.sin(th) * rad, mix(C.gold, C.dusk, s), 0.9)
  } else if (roll < 0.97) {
    // Seven milestones, the last one is the show.
    const k = i % 7
    const s = k / 6
    const th = s * TAU * 3.25
    const last = k === 6
    const u = r() * 2 - 1
    const a = r() * TAU
    const rr = (last ? 0.3 : 0.14) * Math.cbrt(r())
    const q = Math.sqrt(1 - u * u) * rr
    set(Math.cos(th) * 1.7 + Math.cos(a) * q, 3 - s * 6 + u * rr, Math.sin(th) * 1.7 + Math.sin(a) * q, last ? C.ember : C.ivory, 1.6)
  } else {
    set(gaussian(r) * 1.6, gaussian(r) * 2.4, gaussian(r) * 1.6, scale(C.ivory, 0.3), 0.5)
  }
}

function eye(i, r) {
  const roll = r()
  const W = 2.9
  const upper = (x) => 1.3 * (1 - (x / W) ** 2)
  const lower = (x) => -1.0 * (1 - (x / W) ** 2)
  if (roll < 0.42) {
    const x = (r() * 2 - 1) * W
    const top = r() < 0.55
    const strand = Math.floor(r() * 5) * 0.035
    set(x, top ? upper(x) + strand : lower(x) - strand, gaussian(r) * 0.02, scale(C.ivory, 0.85), 0.9)
  } else if (roll < 0.5) {
    const x = (r() * 2 - 1) * W * 0.85
    const len = r() * 0.38 * (1 - Math.abs(x / W))
    const nx = (2 * 1.3 * x) / (W * W)
    set(x + nx * len * 0.5, upper(x) + 0.05 + len, 0, scale(C.ivory, 0.7), 0.7)
  } else if (roll < 0.68) {
    const fiber = Math.floor(r() * 140)
    const phi = (fiber / 140) * TAU + gaussian(r) * 0.01
    const rr = 0.36 + Math.pow(r(), 0.8) * 0.72
    const x = Math.cos(phi) * rr
    const y = Math.sin(phi) * rr
    if (y > upper(x) - 0.04 || y < lower(x) + 0.04) return eye(i, r)
    set(x, y, 0.25 * (1 - rr), scale(rasaGradient(phi / TAU), 0.85), 1)
  } else {
    set(gaussian(r) * 3.2, gaussian(r) * 1.8, gaussian(r) * 1.2, scale(C.gold, 0.22), 0.5)
  }
}

function sphere(i, r) {
  const roll = r()
  if (roll < 0.7) {
    const ring = Math.floor(r() * 36)
    const lat = (ring / 35 - 0.5) * Math.PI * 0.94
    const lon = r() * TAU
    const R = 2.2
    set(Math.cos(lat) * Math.cos(lon) * R, Math.sin(lat) * R, Math.cos(lat) * Math.sin(lon) * R, mix(C.ivory, C.gold, ring / 35), 0.85)
  } else if (roll < 0.78) {
    const u = r() * 2 - 1
    const a = r() * TAU
    const rr = 0.5 * Math.cbrt(r())
    const q = Math.sqrt(1 - u * u) * rr
    set(Math.cos(a) * q, u * rr, Math.sin(a) * q, C.gold, 1.4)
  } else {
    const u = r() * 2 - 1
    const a = r() * TAU
    const rr = 2.6 + r() * 1.6
    const q = Math.sqrt(1 - u * u) * rr
    set(Math.cos(a) * q, u * rr, Math.sin(a) * q, scale(C.ivory, 0.3), 0.5)
  }
}

function scatter(i, r) {
  const u = r() * 2 - 1
  const a = r() * TAU
  const rr = 5 + r() * 9
  const q = Math.sqrt(1 - u * u) * rr
  set(Math.cos(a) * q, u * rr, Math.sin(a) * q, scale(rasaGradient(r()), 0.6), 0.7)
}

export const SHAPES = {
  scatter,
  infinity,
  garment,
  mandala,
  split,
  material,
  fingerprint,
  stage,
  constellation,
  pillars,
  lenses,
  helix,
  eye,
  sphere,
}
export const SHAPE_NAMES = Object.keys(SHAPES)

// Bake every shape into one tall texture: shape k occupies rows [k*SIZE, (k+1)*SIZE).
export function bakeShapes() {
  const n = SHAPE_NAMES.length
  const pos = new Float32Array(COUNT * n * 4)
  const col = new Uint8Array(COUNT * n * 4)
  SHAPE_NAMES.forEach((name, k) => {
    const fn = SHAPES[name]
    const r = rng(1000 + k * 7919)
    for (let i = 0; i < COUNT; i++) {
      P.g = -1
      fn(i, r)
      const o = (k * COUNT + i) * 4
      pos[o] = P.x
      pos[o + 1] = P.y
      pos[o + 2] = P.z
      pos[o + 3] = P.g
      col[o] = Math.min(255, P.c[0])
      col[o + 1] = Math.min(255, P.c[1])
      col[o + 2] = Math.min(255, P.c[2])
      col[o + 3] = Math.min(255, P.s * 100)
    }
  })
  return { pos, col, count: n }
}
