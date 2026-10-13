import * as THREE from 'three'
import Lenis from 'lenis'
import 'lenis/dist/lenis.css'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { createParticles, createBackdrop, LensShader } from './particles.js'
import { SCENES } from './scenes.js'
import { RASAS } from './shapes.js'
import { createDrone } from './drone.js'
import { setupUI } from './ui.js'

const root = document.documentElement
const params = new URLSearchParams(location.search)
const flag = (name) => params.has(name) || location.hash === `#${name}`
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches
const narrow = matchMedia('(max-width: 760px)')

const sections = [...document.querySelectorAll('[data-scene]')]
const ui = setupUI(sections, RASAS)

const drone = createDrone(() => {
  pulse = 1
})
let pulse = 0
ui.onSound(() => drone.toggle())

if (flag('fallback') || !hasWebGL2()) {
  root.classList.add('no-webgl')
  ui.ready()
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

function start() {
  const canvas = document.getElementById('stage')
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' })
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.05
  canvas.addEventListener('webglcontextlost', (e) => {
    e.preventDefault()
    root.classList.add('no-webgl')
  })

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100)
  const backdrop = createBackdrop()
  scene.add(backdrop.mesh)

  const mobile = narrow.matches
  const particles = createParticles({ count: mobile ? 40000 : undefined })
  const { points, uniforms, shapeIndex } = particles
  scene.add(points)
  if (reducedMotion) uniforms.uCalm.value = 0

  const composer = new EffectComposer(renderer)
  composer.addPass(new RenderPass(scene, camera))
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.6, 0.6, 0.22)
  composer.addPass(bloom)
  const lens = new ShaderPass(LensShader)
  composer.addPass(lens)
  composer.addPass(new OutputPass())

  // Scroll anchors: the morph into section k happens while its top travels
  // from just below the fold to a quarter of the way down the screen.
  let anchors = []
  let dpr = 1
  function resize() {
    const w = window.innerWidth
    const h = window.innerHeight
    dpr = Math.min(window.devicePixelRatio, narrow.matches ? 1.5 : 1.75)
    renderer.setPixelRatio(dpr)
    renderer.setSize(w, h, false)
    composer.setPixelRatio(dpr)
    composer.setSize(w, h)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
    uniforms.uPixelRatio.value = dpr * (h / 900) * (narrow.matches ? 1.5 : 1)
    backdrop.uniforms.uAspect.value = w / h
    lens.uniforms.uAspect.value = w / h
    anchors = sections.map((el) => el.getBoundingClientRect().top + window.scrollY)
  }
  resize()
  window.addEventListener('resize', resize)
  new ResizeObserver(() => resize()).observe(document.querySelector('main'))

  function progressAt(y) {
    const vh = window.innerHeight
    let t = 0
    for (let k = 1; k < anchors.length; k++) {
      const start = anchors[k] - vh * 0.95
      const end = anchors[k] - vh * 0.25
      if (y >= end) t = k
      else {
        if (y > start) t = k - 1 + (y - start) / (end - start)
        break
      }
    }
    return t
  }

  // Pointer: eased gaze for the camera, plus a world-space point that parts the particles.
  const pointer = { x: 0, y: 0, sx: 0, sy: 0, active: 0, last: 0 }
  window.addEventListener('pointermove', (e) => {
    if (e.pointerType === 'touch') return
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1
    pointer.last = performance.now()
  })
  const raycaster = new THREE.Raycaster()
  const plane = new THREE.Plane()
  const hit = new THREE.Vector3()
  const ndc = new THREE.Vector2()

  const lenis = reducedMotion ? null : new Lenis({ autoRaf: false, lerp: 0.085 })
  ui.bindScroll((el) => (lenis ? lenis.scrollTo(el, { offset: 0, duration: 1.6 }) : el.scrollIntoView()))

  const presets = sections.map((el) => SCENES[el.dataset.scene])
  const tmpA = new THREE.Color()
  const tmpB = new THREE.Color()
  const look = new THREE.Vector3()
  const lerp = (a, b, t) => a + (b - a) * t
  const ease = (t) => t * t * (3 - 2 * t)

  let rotY = 0
  let introStart = 0
  let last = performance.now()
  let rendered = false

  function frame(now) {
    requestAnimationFrame(frame)
    lenis?.raf(now)
    const dt = Math.min(0.05, (now - last) / 1000)
    last = now
    const time = now / 1000
    const y = lenis ? lenis.scroll : window.scrollY
    const velocity = lenis ? Math.abs(lenis.velocity) : 0
    const isMobile = narrow.matches

    const t = progressAt(y)
    const a = Math.min(Math.floor(t), presets.length - 1)
    const b = Math.min(a + 1, presets.length - 1)
    const m = t - a
    const e = ease(m)
    const A = presets[a]
    const B = presets[b]

    uniforms.uA.value = shapeIndex[A.shape]
    uniforms.uB.value = shapeIndex[B.shape]
    uniforms.uMix.value = m

    // Opening: the dust of every colour gathers into the infinite.
    if (!introStart) introStart = now
    const intro = reducedMotion ? 1 : Math.min(1, (now - introStart) / 3200)
    if (intro < 1 && t < 0.02) {
      uniforms.uA.value = shapeIndex.scatter
      uniforms.uB.value = shapeIndex.infinity
      uniforms.uMix.value = intro
    }

    // Camera, with a little gaze towards the pointer.
    const gaze = reducedMotion ? 0 : 1
    pointer.sx += (pointer.x - pointer.sx) * 0.045
    pointer.sy += (pointer.y - pointer.sy) * 0.045
    // Narrow portrait screens pull the camera back so wide sculptures still fit.
    const zoom = isMobile ? Math.max(1.3, 0.85 / camera.aspect) : 1
    camera.position.set(
      lerp(A.cam[0], B.cam[0], e) * zoom + pointer.sx * 0.7 * gaze,
      lerp(A.cam[1], B.cam[1], e) * zoom - pointer.sy * 0.45 * gaze,
      lerp(A.cam[2], B.cam[2], e) * zoom,
    )
    look.set(lerp(A.look[0], B.look[0], e), lerp(A.look[1], B.look[1], e), lerp(A.look[2], B.look[2], e))
    camera.lookAt(look)

    const offset = isMobile ? 0 : lerp(A.x, B.x, e)
    points.position.x = offset
    points.scale.setScalar(lerp(A.s, B.s, e) * (isMobile ? 0.82 : 1))

    // Free spin for sculptural forms, a held pose with sway for flat ones.
    const spin = lerp(A.spin, B.spin, e)
    if (!reducedMotion) rotY += dt * 0.16 * spin
    const facing = Math.round(rotY / (Math.PI * 2)) * Math.PI * 2
    const sway = Math.sin(time * 0.3) * 0.22 * (reducedMotion ? 0 : 1)
    rotY += (facing + sway - rotY) * (1 - spin) * Math.min(1, dt * 2.5)
    points.rotation.y = rotY

    backdrop.uniforms.uBase.value.copy(tmpA.set(A.base).lerp(tmpB.set(B.base), e))
    backdrop.uniforms.uGlow.value.copy(tmpA.set(A.glow).lerp(tmpB.set(B.glow), e))
    backdrop.uniforms.uShift.value = offset / 3
    backdrop.uniforms.uTime.value = time

    // Pointer parting.
    const moving = now - pointer.last < 1400 && !isMobile && !reducedMotion
    pointer.active += ((moving ? 1 : 0) - pointer.active) * 0.06
    uniforms.uMouseOn.value = pointer.active
    if (pointer.active > 0.01) {
      ndc.set(pointer.x, -pointer.y)
      raycaster.setFromCamera(ndc, camera)
      plane.setFromNormalAndCoplanarPoint(camera.getWorldDirection(hit).negate(), points.position)
      if (raycaster.ray.intersectPlane(plane, hit)) uniforms.uMouse.value.copy(hit)
    }

    // Highlight from hovered list items, only while their chapter is on screen.
    const hl = ui.highlight()
    uniforms.uActive.value = hl && Math.round(t) === hl.section ? hl.group : -1

    pulse *= Math.pow(0.04, dt)
    uniforms.uPulse.value = pulse
    uniforms.uTurb.value += (Math.min(1, velocity / 30) - uniforms.uTurb.value) * 0.08
    uniforms.uTime.value = time
    lens.uniforms.uTime.value = time
    lens.uniforms.uAberration.value = 1 + uniforms.uTurb.value * 2.5

    composer.render()
    ui.update(t, lenis?.velocity ?? 0)

    if (!rendered) {
      rendered = true
      ui.ready()
    }
  }
  requestAnimationFrame(frame)
}
