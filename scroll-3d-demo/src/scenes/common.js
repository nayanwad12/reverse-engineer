import * as THREE from 'three'

// Large inside-out sphere with a vertical gradient, used as each scene's sky.
export function makeSky(top, bottom, horizon = 0.0) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(60, 32, 16),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: {
        uTop: { value: new THREE.Color(top) },
        uBottom: { value: new THREE.Color(bottom) },
        uHorizon: { value: horizon },
      },
      vertexShader: /* glsl */ `
        varying vec3 vDir;
        void main() {
          vDir = normalize(position);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uTop;
        uniform vec3 uBottom;
        uniform float uHorizon;
        varying vec3 vDir;
        void main() {
          float t = smoothstep(-0.25, 0.65, vDir.y + uHorizon);
          gl_FragColor = vec4(mix(uBottom, uTop, t), 1.0);
        }`,
    }),
  )
}

let dotTexture
function getDotTexture() {
  if (dotTexture) return dotTexture
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  g.addColorStop(0, 'rgba(255,255,255,1)')
  g.addColorStop(0.35, 'rgba(255,255,255,0.45)')
  g.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, size, size)
  dotTexture = new THREE.CanvasTexture(canvas)
  dotTexture.colorSpace = THREE.SRGBColorSpace
  return dotTexture
}

// Soft additive points: dust motes in the hero, stars in the armillary scene.
export function makeParticles({ count, spread, center = [0, 0, 0], color, size, seed = 1 }) {
  let s = seed
  const rand = () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i++) {
    positions[i * 3] = center[0] + (rand() - 0.5) * spread[0]
    positions[i * 3 + 1] = center[1] + (rand() - 0.5) * spread[1]
    positions[i * 3 + 2] = center[2] + (rand() - 0.5) * spread[2]
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  return new THREE.Points(
    geometry,
    new THREE.PointsMaterial({
      color,
      size,
      map: getDotTexture(),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
  )
}

const _target = new THREE.Vector3()
const _offset = new THREE.Vector3()
const _spherical = new THREE.Spherical()

// Place a camera from keyframed values, then orbit it a little around its
// target by the smoothed pointer ("gaze"), like the reference site.
export function applyCamera(camera, cam, pointer, gaze) {
  _target.set(cam.tx, cam.ty, cam.tz)
  _offset.set(cam.px, cam.py, cam.pz).sub(_target)
  _spherical.setFromVector3(_offset)
  _spherical.theta -= pointer.x * gaze
  _spherical.phi = THREE.MathUtils.clamp(_spherical.phi + pointer.y * gaze, 0.05, Math.PI - 0.05)
  _offset.setFromSpherical(_spherical)
  camera.position.copy(_target).add(_offset)
  camera.lookAt(_target)
  // Portrait screens get a wider lens so the subject still fits.
  const fov = camera.aspect < 1 ? Math.min(cam.fov * 1.6, 75) : cam.fov
  if (camera.fov !== fov) {
    camera.fov = fov
    camera.updateProjectionMatrix()
  }
}
