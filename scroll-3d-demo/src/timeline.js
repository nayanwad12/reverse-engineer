import gsap from 'gsap'

// One paused timeline whose time unit is "screens scrolled" (scrollY / innerHeight).
// It is never played: main.js seeks it to the current scroll position every frame,
// which is what makes scrolling feel like scrubbing a film. Swap this file for a
// Theatre.js sheet if you want to author the keyframes in a visual editor.
export function createTimeline(hero, arm, fx) {
  const tl = gsap.timeline({ paused: true, defaults: { ease: 'power1.inOut' } })

  // Hero: wide establishing shot, then a push into the orb.
  tl.to(hero.cam, { px: 3.2, py: 2.7, pz: 8.5, ty: 2.3, fov: 36, duration: 1 }, 0)
    .to(hero.cam, { px: 0.3, py: 2.35, pz: 3.0, fov: 28, duration: 0.9, ease: 'power2.in' }, 1)
    .to(hero.props, { orbY: 2.3, duration: 1 }, 0)
    .to(hero.props, { orbSpin: Math.PI, duration: 2, ease: 'none' }, 0)

  // Transition: the composite shader reveals scene B through a noisy edge.
  tl.to(fx, { transition: 1, duration: 1, ease: 'none' }, 0.85)
    .to(fx, { bloom: 0.8, duration: 0.5 }, 0.85)
    .to(fx, { bloom: 0.5, duration: 0.5 }, 1.35)

  // Armillary: orbit the sphere while its rings swing open.
  tl.to(arm.cam, { px: 5.5, py: 2.2, pz: 7.5, fov: 36, duration: 1.55 }, 0.85)
    .to(arm.cam, { px: -3.5, py: -0.8, pz: 5.5, fov: 34, duration: 1.2 }, 2.4)
    .to(arm.cam, { px: 0.5, py: 0.3, pz: 4.2, fov: 30, duration: 1.4 }, 3.6)
    .to(arm.props, { open: 1, duration: 1.8, ease: 'power2.inOut' }, 1.8)
    .to(arm.props, { spin: Math.PI * 0.8, duration: 4, ease: 'none' }, 1)
    .to(arm.props, { glow: 1.15, duration: 1.4 }, 3.6)

  // Pin the total length to the five screens before the paper section.
  tl.set({}, {}, 5)
  return tl
}
