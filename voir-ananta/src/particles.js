import * as THREE from 'three'
import { SIZE, COUNT, bakeShapes, SHAPE_NAMES } from './shapes.js'

// One Points object whose vertices are looked up in baked shape textures.
// uA/uB pick two shapes, uMix morphs between them with a per-particle stagger
// and a turbulent "travel" swirl so the form dissolves and re-forms.
export function createParticles({ count = COUNT } = {}) {
  const baked = bakeShapes()
  const posTex = new THREE.DataTexture(baked.pos, SIZE, SIZE * baked.count, THREE.RGBAFormat, THREE.FloatType)
  const colTex = new THREE.DataTexture(baked.col, SIZE, SIZE * baked.count, THREE.RGBAFormat, THREE.UnsignedByteType)
  for (const tex of [posTex, colTex]) {
    tex.minFilter = tex.magFilter = THREE.NearestFilter
    tex.generateMipmaps = false
    tex.needsUpdate = true
  }

  const ref = new Float32Array(COUNT * 2)
  const rand = new Float32Array(COUNT)
  for (let i = 0; i < COUNT; i++) {
    ref[i * 2] = ((i % SIZE) + 0.5) / SIZE
    ref[i * 2 + 1] = (Math.floor(i / SIZE) + 0.5) / SIZE
    rand[i] = Math.random()
  }
  const geometry = new THREE.BufferGeometry()
  // Positions are unused by the shader but three needs the attribute for draw counts.
  geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(COUNT * 3), 3))
  geometry.setAttribute('aRef', new THREE.BufferAttribute(ref, 2))
  geometry.setAttribute('aRand', new THREE.BufferAttribute(rand, 1))
  geometry.setDrawRange(0, count)

  const uniforms = {
    uPosTex: { value: posTex },
    uColTex: { value: colTex },
    uShapes: { value: baked.count },
    uA: { value: 0 },
    uB: { value: 0 },
    uMix: { value: 0 },
    uTime: { value: 0 },
    uTurb: { value: 0 },
    uCalm: { value: 1 },
    uSize: { value: 26 },
    uPixelRatio: { value: 1 },
    uActive: { value: -1 },
    uActiveBase: { value: 0 },
    uPulse: { value: 0 },
    uMouse: { value: new THREE.Vector3(999, 999, 999) },
    uMouseOn: { value: 0 },
    uOpacity: { value: 0.5 },
  }

  const material = new THREE.ShaderMaterial({
    uniforms,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      uniform sampler2D uPosTex;
      uniform sampler2D uColTex;
      uniform float uShapes, uA, uB, uMix, uTime, uTurb, uCalm, uSize, uPixelRatio;
      uniform float uActive, uActiveBase, uPulse, uMouseOn;
      uniform vec3 uMouse;
      attribute vec2 aRef;
      attribute float aRand;
      varying vec3 vColor;

      vec3 flow(vec3 p, float t) {
        return vec3(
          sin(p.y * 1.7 + t * 0.6) + sin(p.z * 2.3 + t * 0.4),
          sin(p.z * 1.9 + t * 0.5) + sin(p.x * 2.1 - t * 0.3),
          sin(p.x * 1.5 - t * 0.45) + sin(p.y * 2.7 + t * 0.35)
        ) * 0.5;
      }

      void main() {
        vec2 uvA = vec2(aRef.x, (aRef.y + uA) / uShapes);
        vec2 uvB = vec2(aRef.x, (aRef.y + uB) / uShapes);
        vec4 pa = texture2D(uPosTex, uvA);
        vec4 pb = texture2D(uPosTex, uvB);
        vec4 ca = texture2D(uColTex, uvA);
        vec4 cb = texture2D(uColTex, uvB);

        float m = clamp((uMix - aRand * 0.3) / 0.7, 0.0, 1.0);
        m = m * m * (3.0 - 2.0 * m);
        vec3 p = mix(pa.xyz, pb.xyz, m);

        float travel = sin(m * 3.14159);
        float amp = (0.03 + uTurb * 0.08) * uCalm + travel * 0.6;
        p += flow(p * 0.6 + aRand * 6.0, uTime) * amp;

        vec4 world = modelMatrix * vec4(p, 1.0);
        vec3 d = world.xyz - uMouse;
        float dist = length(d) + 1e-4;
        world.xyz += d / dist * uMouseOn * 0.6 * smoothstep(1.5, 0.0, dist);

        vec4 mv = viewMatrix * world;
        gl_Position = projectionMatrix * mv;

        vec3 col = mix(pow(ca.rgb, vec3(2.2)), pow(cb.rgb, vec3(2.2)), m);
        float size = mix(ca.a, cb.a, m) * 2.55;

        // Highlight one group (e.g. one rasa) and dim the rest.
        float group = m < 0.5 ? pa.w : pb.w;
        float on = step(-0.5, uActive);
        float hit = 1.0 - step(0.5, abs(group - uActive - uActiveBase));
        col *= mix(1.0, mix(0.18, 2.6, hit), on);
        size *= mix(1.0, mix(0.8, 1.5, hit), on);

        vColor = col * (1.0 + uPulse * 0.8);
        gl_PointSize = uSize * size * (0.55 + aRand * 0.9) * (1.0 + uPulse * 0.3) * uPixelRatio / -mv.z;
      }`,
    fragmentShader: /* glsl */ `
      uniform float uOpacity;
      varying vec3 vColor;
      void main() {
        vec2 c = gl_PointCoord - 0.5;
        float d = dot(c, c) * 4.0;
        if (d > 1.0) discard;
        float a = exp(-d * 3.2) * (1.0 - d);
        gl_FragColor = vec4(vColor * uOpacity, a);
      }`,
  })

  const points = new THREE.Points(geometry, material)
  points.frustumCulled = false
  const shapeIndex = Object.fromEntries(SHAPE_NAMES.map((name, k) => [name, k]))
  return { points, uniforms, shapeIndex }
}

// Full-screen backdrop: a deep night tinted per chapter with a slow nebula.
export function createBackdrop() {
  const uniforms = {
    uBase: { value: new THREE.Color('#0a0812') },
    uGlow: { value: new THREE.Color('#3a1f5c') },
    uTime: { value: 0 },
    uAspect: { value: 1 },
    uShift: { value: 0 },
  }
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(2, 2),
    new THREE.ShaderMaterial({
      uniforms,
      depthTest: false,
      depthWrite: false,
      vertexShader: /* glsl */ `
        varying vec2 vUv;
        void main() { vUv = uv; gl_Position = vec4(position.xy, 0.999, 1.0); }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uBase, uGlow;
        uniform float uTime, uAspect, uShift;
        varying vec2 vUv;
        float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
        float noise(vec2 p) {
          vec2 i = floor(p); vec2 f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
          return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
        }
        float fbm(vec2 p) { float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { v += a * noise(p); p = p * 2.02 + 7.1; a *= 0.5; } return v; }
        void main() {
          vec2 p = vec2((vUv.x - 0.5) * uAspect, vUv.y - 0.5);
          float n = fbm(p * 1.6 + vec2(uTime * 0.012, -uTime * 0.008));
          float glow = smoothstep(1.1, 0.0, length(p - vec2(uShift * 0.35, 0.05))) * (0.35 + n * 0.9);
          vec3 col = uBase + uGlow * glow * 0.55;
          gl_FragColor = vec4(col, 1.0);
        }`,
    }),
  )
  mesh.frustumCulled = false
  mesh.renderOrder = -1
  return { mesh, uniforms }
}

// Final lens pass: subtle chromatic fringing, film grain and vignette.
export const LensShader = {
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uAspect: { value: 1 },
    uAberration: { value: 1 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime, uAspect, uAberration;
    varying vec2 vUv;
    float hash(vec2 p) { p = fract(p * vec2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return fract((p.x + p.y) * p.x); }
    void main() {
      vec2 c = vUv - 0.5;
      float r2 = dot(c * vec2(uAspect, 1.0), c * vec2(uAspect, 1.0));
      vec2 off = c * r2 * 0.012 * uAberration;
      vec3 col;
      col.r = texture2D(tDiffuse, vUv + off).r;
      col.g = texture2D(tDiffuse, vUv).g;
      col.b = texture2D(tDiffuse, vUv - off).b;
      col *= mix(1.0, 0.55, smoothstep(0.15, 0.9, r2));
      col += (hash(vUv * 1024.0 + fract(uTime * 7.0)) - 0.5) * 0.035;
      gl_FragColor = vec4(col, 1.0);
    }`,
}
