import * as THREE from 'three'
import Lenis from 'lenis'
import 'lenis/dist/lenis.css'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { createHeroScene } from './scenes/hero.js'
import { createArmillaryScene } from './scenes/armillary.js'
import { createTimeline } from './timeline.js'
import { createCompositeMaterial } from './composite.js'

const root = document.documentElement
const params = new URLSearchParams(location.search)
// Flags work as ?debug or #debug (some hosts strip the query string).
const flag = (name) => params.has(name) || location.hash === `#${name}`
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches

setupReveals()

if (reducedMotion || flag('fallback') || !hasWebGL2()) {
  root.classList.add('no-webgl')
} else {
  start()
}

function hasWebGL2() {
  try {
    return !!document.createElement('canvas').getContext('webgl2')
  } catch {
    return false
  }
}

function setupReveals() {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) entry.target.classList.toggle('is-visible', entry.isIntersecting)
    },
    { threshold: 0.3 },
  )
  document.querySelectorAll('.reveal').forEach((el) => observer.observe(el))
}

function start() {
  const canvas = document.getElementById('stage')
  const paper = document.querySelector('.paper')
  const hud = document.getElementById('hud')
  hud.hidden = !flag('debug')

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' })
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  const dpr = Math.min(window.devicePixelRatio, 1.5)
  renderer.setPixelRatio(dpr)
  canvas.addEventListener('webglcontextlost', () => root.classList.add('no-webgl'))

  const hero = createHeroScene(renderer)
  const arm = createArmillaryScene(renderer)
  const fx = { transition: 0, bloom: 0.35 }
  const timeline = createTimeline(hero.state, arm.state, fx)

  // Each scene renders offscreen; the composite pass blends them.
  const targets = [0, 1].map(() => new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }))
  const composite = createCompositeMaterial(targets[0].texture, targets[1].texture)
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), composite)
  quad.frustumCulled = false
  const quadScene = new THREE.Scene().add(quad)
  const quadCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)

  const composer = new EffectComposer(renderer)
  composer.addPass(new RenderPass(quadScene, quadCamera))
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), fx.bloom, 0.5, 1.0)
  composer.addPass(bloom)
  composer.addPass(new OutputPass())

  let paperTop = Infinity
  function resize() {
    const w = window.innerWidth
    const h = window.innerHeight
    renderer.setSize(w, h, false)
    composer.setPixelRatio(dpr)
    composer.setSize(w, h)
    for (const target of targets) target.setSize(Math.round(w * dpr), Math.round(h * dpr))
    for (const camera of [hero.camera, arm.camera]) {
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    composite.uniforms.uAspect.value = w / h
    paperTop = paper.offsetTop / h
  }
  resize()
  window.addEventListener('resize', resize)

  // Pointer in [-1, 1], eased each frame for the camera "gaze".
  const pointer = { x: 0, y: 0, sx: 0, sy: 0 }
  window.addEventListener('pointermove', (e) => {
    if (e.pointerType === 'touch') return
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1
  })
  document.documentElement.addEventListener('pointerleave', () => {
    pointer.x = pointer.y = 0
  })

  const lenis = new Lenis({ autoRaf: false, lerp: 0.09 })

  function frame(now) {
    requestAnimationFrame(frame)
    lenis.raf(now)

    // The whole effect hangs on this one number.
    const screens = lenis.scroll / window.innerHeight
    if (screens >= paperTop) return // the paper section covers the canvas

    timeline.seek(Math.min(screens, timeline.duration()), false)

    pointer.sx += (pointer.x - pointer.sx) * 0.05
    pointer.sy += (pointer.y - pointer.sy) * 0.05
    const gaze = { x: pointer.sx, y: pointer.sy }
    const time = now / 1000

    if (fx.transition < 1) {
      hero.update(time, gaze)
      renderer.setRenderTarget(targets[0])
      renderer.render(hero.scene, hero.camera)
    }
    if (fx.transition > 0) {
      arm.update(time, gaze)
      renderer.setRenderTarget(targets[1])
      renderer.render(arm.scene, arm.camera)
    }
    renderer.setRenderTarget(null)

    composite.uniforms.uProgress.value = fx.transition
    composite.uniforms.uTime.value = time
    bloom.strength = fx.bloom
    composer.render()

    if (!hud.hidden) {
      hud.textContent =
        `scroll     ${screens.toFixed(2)} screens\n` +
        `timeline   ${timeline.time().toFixed(2)} / ${timeline.duration().toFixed(2)}\n` +
        `transition ${fx.transition.toFixed(2)}\n` +
        `bloom      ${fx.bloom.toFixed(2)}\n` +
        `rings open ${arm.state.props.open.toFixed(2)}`
    }
  }
  requestAnimationFrame(frame)
}
