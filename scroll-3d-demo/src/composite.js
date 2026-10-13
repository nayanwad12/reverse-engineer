import * as THREE from 'three'

// Full-screen pass that blends the two offscreen scene renders. The reveal edge
// is a radial gradient warped by fractal noise, with a glowing rim and a little
// refraction along it, so scene B bleeds in like paint rather than a crossfade.
export function createCompositeMaterial(textureA, textureB) {
  return new THREE.ShaderMaterial({
    depthTest: false,
    depthWrite: false,
    uniforms: {
      tA: { value: textureA },
      tB: { value: textureB },
      uProgress: { value: 0 },
      uTime: { value: 0 },
      uAspect: { value: 1 },
      uEdgeColor: { value: new THREE.Color(1.8, 1.1, 0.45) },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 0.0, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D tA;
      uniform sampler2D tB;
      uniform float uProgress;
      uniform float uTime;
      uniform float uAspect;
      uniform vec3 uEdgeColor;
      varying vec2 vUv;

      float hash(vec2 p) {
        p = fract(p * vec2(123.34, 456.21));
        p += dot(p, p + 45.32);
        return fract(p.x * p.y);
      }

      float noise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        vec2 u = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
                   mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
      }

      float fbm(vec2 p) {
        float v = 0.0;
        float a = 0.5;
        for (int i = 0; i < 5; i++) {
          v += a * noise(p);
          p = p * 2.03 + 11.7;
          a *= 0.5;
        }
        return v;
      }

      void main() {
        vec2 p = vec2(vUv.x * uAspect, vUv.y);
        float n = fbm(p * 2.6 + vec2(uTime * 0.04, -uTime * 0.03));

        // Distance from a point slightly above centre, roughened by noise.
        float d = length((vUv - vec2(0.5, 0.55)) * vec2(uAspect, 1.0));
        float field = d * 0.9 + n * 0.4;
        float edge = mix(-0.25, 1.55, uProgress);

        float rim = 1.0 - smoothstep(0.0, 0.04, abs(field - edge));
        rim *= step(0.001, uProgress) * step(uProgress, 0.999);

        // Refract the image along the rim.
        vec2 warp = (vec2(n, fbm(p * 2.6 + 4.0)) - 0.5) * 0.06 * rim;
        vec3 a = texture2D(tA, vUv + warp).rgb;
        vec3 b = texture2D(tB, vUv - warp).rgb;

        float showA = smoothstep(edge - 0.015, edge + 0.015, field);
        vec3 color = mix(b, a, showA);
        color += uEdgeColor * pow(rim, 2.0) * 0.9;

        // Vignette and film grain.
        color *= mix(0.72, 1.0, smoothstep(1.05, 0.35, length((vUv - 0.5) * vec2(uAspect, 1.0))));
        color += (hash(vUv * 1000.0 + fract(uTime)) - 0.5) * 0.025;

        gl_FragColor = vec4(color, 1.0);
      }`,
  })
}
