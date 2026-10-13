import * as THREE from 'three'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { applyCamera, makeParticles, makeSky } from './common.js'

// Scene B: a night sky with an armillary sphere whose rings open on scroll.
export function createArmillaryScene(renderer) {
  const scene = new THREE.Scene()
  const pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.environmentIntensity = 0.45
  pmrem.dispose()

  scene.add(makeSky(0x1d2a5c, 0x05060f, -0.1))
  scene.add(new THREE.HemisphereLight(0x8fa6ff, 0x0a0a18, 0.6))
  const rim = new THREE.DirectionalLight(0xffcf8a, 3.5)
  rim.position.set(4, 5, 3)
  scene.add(rim)

  const stars = makeParticles({
    count: 2200,
    spread: [90, 60, 90],
    color: 0xcfd8ff,
    size: 0.18,
    seed: 3,
  })
  scene.add(stars)

  const gold = new THREE.MeshStandardMaterial({ color: 0xf0b860, metalness: 1, roughness: 0.25 })
  const sphere = new THREE.Group()

  // Each ring sits in a pivot so the timeline can swing it about its own axis.
  const ringSpecs = [
    { r: 2.5, tilt: [0, 0, 0], axis: 'x', open: 1.35 },
    { r: 2.2, tilt: [Math.PI / 2, 0, 0], axis: 'y', open: -1.1 },
    { r: 1.9, tilt: [0, Math.PI / 2, 0.4], axis: 'x', open: 1.6 },
    { r: 1.6, tilt: [Math.PI / 3, 0, Math.PI / 5], axis: 'z', open: -1.4 },
    { r: 1.3, tilt: [0, 0, Math.PI / 2.4], axis: 'y', open: 2.0 },
  ]
  const rings = ringSpecs.map((spec, i) => {
    const pivot = new THREE.Group()
    const ring = new THREE.Mesh(new THREE.TorusGeometry(spec.r, 0.045 + i * 0.004, 12, 160), gold)
    ring.rotation.set(...spec.tilt)
    pivot.add(ring)
    // Tick marks along the outer rings.
    if (i < 2) {
      const tick = new THREE.BoxGeometry(0.03, 0.18, 0.03)
      for (let k = 0; k < 24; k++) {
        const a = (k / 24) * Math.PI * 2
        const t = new THREE.Mesh(tick, gold)
        t.position.set(Math.cos(a) * spec.r, Math.sin(a) * spec.r, 0)
        t.rotation.z = a
        ring.add(t)
      }
    }
    sphere.add(pivot)
    return { pivot, spec }
  })

  // Glowing celestial core (bright enough to bloom).
  const core = new THREE.Mesh(
    new THREE.SphereGeometry(0.55, 48, 24),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(3.2, 2.0, 0.9) }),
  )
  sphere.add(core)

  // Axis rod and stand.
  const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 6.2, 8), gold)
  rod.rotation.z = 0.41
  sphere.add(rod)
  scene.add(sphere)

  const stand = new THREE.Group()
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.14, 2.2, 16), gold)
  post.position.y = -3.6
  const foot = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.25, 0.25, 32), gold)
  foot.position.y = -4.7
  stand.add(post, foot)
  scene.add(stand)

  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 160)

  const state = {
    cam: { px: 0, py: 0.4, pz: 12, tx: 0, ty: 0, tz: 0, fov: 40 },
    props: { open: 0, spin: 0, glow: 1 },
  }

  function update(time, pointer) {
    applyCamera(camera, state.cam, pointer, 0.18)
    const { open, spin, glow } = state.props
    sphere.rotation.y = spin + time * 0.05
    for (const { pivot, spec } of rings) {
      pivot.rotation[spec.axis] = open * spec.open + Math.sin(time * 0.3 + spec.r) * 0.04
    }
    core.scale.setScalar(glow * (1 + Math.sin(time * 2) * 0.03))
    stars.rotation.y = time * 0.004
  }

  return { scene, camera, state, update }
}
