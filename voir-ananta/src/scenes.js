// One preset per page section, matched by the section's data-scene attribute.
// shape: particle sculpture. cam/look: camera. x: horizontal offset of the
// sculpture on wide screens (opposite the text column). spin: 1 rotates freely,
// 0 holds facing the viewer with a gentle sway. base/glow: backdrop colours.
export const SCENES = {
  hero: { shape: 'infinity', cam: [0, 0, 9.2], look: [0, -0.2, 0], x: 0, s: 1.05, spin: 0, base: '#09070f', glow: '#3b2160' },
  what: { shape: 'garment', cam: [0, 0.5, 9.6], look: [0, 0.2, 0], x: 2.7, s: 0.95, spin: 1, base: '#0b0810', glow: '#4b2a17' },
  edition: { shape: 'mandala', cam: [0, -0.3, 10.2], look: [0, 0, 0], x: 2.9, s: 0.95, spin: 0, base: '#08070f', glow: '#2b1b52' },
  categories: { shape: 'split', cam: [0, 0.6, 10.4], look: [0, 0, 0], x: 0, s: 1, spin: 0, base: '#0a0810', glow: '#2a1a3a' },
  material: { shape: 'material', cam: [0.4, 1.1, 8.6], look: [0, 0, 0], x: -2.1, s: 0.82, spin: 0, base: '#0b0907', glow: '#3d2610' },
  human: { shape: 'fingerprint', cam: [0, 0, 9.2], look: [0, 0.2, 0], x: 2.8, s: 0.95, spin: 0, base: '#0b0908', glow: '#3d2a14' },
  experience: { shape: 'stage', cam: [0, 2.1, 10.2], look: [0, 0.1, 0], x: -2.6, s: 0.95, spin: 1, base: '#0a0807', glow: '#47321a' },
  who: { shape: 'constellation', cam: [0, 1.6, 9.4], look: [0, 0, 0], x: 2.8, s: 0.85, spin: 1, base: '#07070f', glow: '#1d2150' },
  selection: { shape: 'pillars', cam: [0, 3.6, 11.5], look: [0, -0.3, 0], x: -2.3, s: 0.8, spin: 1, base: '#070810', glow: '#1a2244' },
  lenses: { shape: 'lenses', cam: [0, 0, 12.5], look: [0, 0.3, 0], x: 0, s: 1.35, spin: 0, base: '#09070e', glow: '#2b1d3d' },
  journey: { shape: 'helix', cam: [0, 0.4, 10], look: [0, 0, 0], x: 2.7, s: 0.95, spin: 1, base: '#08070f', glow: '#2e1f4c' },
  participate: { shape: 'sphere', cam: [0, 0, 9.2], look: [0, 0, 0], x: -2.3, s: 0.75, spin: 1, base: '#0a0810', glow: '#3f2a14' },
  develop: { shape: 'garment', cam: [3.5, 0.2, 8.6], look: [0, 0.3, 0], x: 2.7, s: 0.95, spin: 1, base: '#0b0810', glow: '#4b2a17' },
  show: { shape: 'pillars', cam: [0, 0.6, 8.6], look: [0, 0.3, 0], x: 0, s: 1, spin: 1, base: '#08070e', glow: '#3a1f4c' },
  judges: { shape: 'eye', cam: [0, 0, 9.5], look: [0, 0, 0], x: 2.7, s: 0.8, spin: 0, base: '#08070f', glow: '#2c1d50' },
  partners: { shape: 'constellation', cam: [0, 6.5, 5.5], look: [0, 0, 0], x: -2.4, s: 0.78, spin: 1, base: '#07070f', glow: '#2a1f48' },
  about: { shape: 'sphere', cam: [0, 1.5, 9.5], look: [0, 0, 0], x: 2.7, s: 0.78, spin: 1, base: '#0a0810', glow: '#36251a' },
  final: { shape: 'infinity', cam: [0, 0, 10.4], look: [0, 0, 0], x: 0, s: 1.15, spin: 0, base: '#09070f', glow: '#3b2160' },
}
