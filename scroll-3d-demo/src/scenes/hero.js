import * as THREE from 'three'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { applyCamera, makeParticles, makeSky } from './common.js'

// Scene A: a warm colonnade with a floating golden orb.
export function createHeroScene(renderer) {
  const scene = new THREE.Scene()
  scene.fog = new THREE.Fog(0xb9805a, 10, 34)
  const pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.environmentIntensity = 0.6
  pmrem.dispose()

  scene.add(makeSky(0xd99a6c, 0x5a2e22, 0.05))
  scene.add(new THREE.HemisphereLight(0xffe2c0, 0x5a3424, 0.9))
  const sun = new THREE.DirectionalLight(0xffd29a, 2.2)
  sun.position.set(-6, 9, 6)
  scene.add(sun)

  const stone = new THREE.MeshStandardMaterial({ color: 0xcdb99a, roughness: 0.85 })
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(40, 64),
    new THREE.MeshStandardMaterial({ color: 0xc9a98a, roughness: 0.95 }),
  )
  floor.rotation.x = -Math.PI / 2
  scene.add(floor)

  // Semicircular colonnade behind the orb.
  const shaft = new THREE.CylinderGeometry(0.32, 0.38, 4.2, 20)
  const block = new THREE.BoxGeometry(0.95, 0.28, 0.95)
  const colonnade = new THREE.Group()
  const count = 11
  for (let i = 0; i < count; i++) {
    const a = Math.PI * (0.08 + (0.84 * i) / (count - 1))
    const column = new THREE.Group()
    const s = new THREE.Mesh(shaft, stone)
    s.position.y = 2.38
    const base = new THREE.Mesh(block, stone)
    base.position.y = 0.14
    const capital = new THREE.Mesh(block, stone)
    capital.position.y = 4.62
    column.add(s, base, capital)
    column.position.set(Math.cos(a) * 7, 0, -Math.sin(a) * 7 - 1)
    colonnade.add(column)
  }
  const lintel = new THREE.Mesh(
    new THREE.TorusGeometry(7, 0.2, 4, 64, Math.PI * 0.9),
    stone,
  )
  lintel.rotation.set(Math.PI / 2, 0, Math.PI * 0.05)
  lintel.position.set(0, 4.86, -1)
  colonnade.add(lintel)
  scene.add(colonnade)

  // The orb: faceted gold shell around an emissive core (the core feeds bloom).
  const orb = new THREE.Group()
  const shell = new THREE.Mesh(
    new THREE.IcosahedronGeometry(1.15, 1),
    new THREE.MeshStandardMaterial({ color: 0xffc46b, metalness: 1, roughness: 0.22, flatShading: true }),
  )
  const core = new THREE.Mesh(
    new THREE.IcosahedronGeometry(0.62, 3),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 2.6, 1.2) }),
  )
  orb.add(shell, core)
  scene.add(orb)

  // Small shards orbiting the orb.
  const shards = new THREE.Group()
  const shardGeo = new THREE.TetrahedronGeometry(0.16)
  const shardMat = new THREE.MeshStandardMaterial({ color: 0xffd8a0, metalness: 1, roughness: 0.3 })
  for (let i = 0; i < 14; i++) {
    const m = new THREE.Mesh(shardGeo, shardMat)
    const a = (i / 14) * Math.PI * 2
    m.position.set(Math.cos(a) * 2.1, Math.sin(a * 3) * 0.35, Math.sin(a) * 2.1)
    shards.add(m)
  }
  orb.add(shards)

  const dust = makeParticles({
    count: 700,
    spread: [22, 9, 18],
    center: [0, 4, -2],
    color: 0xffe0b0,
    size: 0.07,
    seed: 7,
  })
  scene.add(dust)

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 120)

  // Everything the timeline animates lives in plain objects.
  const state = {
    cam: { px: 0, py: 2.1, pz: 15, tx: 0, ty: 2.4, tz: 0, fov: 42 },
    props: { orbY: 1.6, orbSpin: 0 },
  }

  function update(time, pointer) {
    applyCamera(camera, state.cam, pointer, 0.12)
    orb.position.y = state.props.orbY + Math.sin(time * 0.9) * 0.08
    orb.rotation.y = state.props.orbSpin + time * 0.15
    shell.rotation.x = time * 0.1
    shards.rotation.y = -time * 0.4
    dust.position.y = Math.sin(time * 0.2) * 0.25
    dust.rotation.y = time * 0.01
  }

  return { scene, camera, state, update }
}
