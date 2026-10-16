import React, { useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { Lightformer } from "@react-three/drei"
import {
  AdditiveBlending,
  Color,
  Group,
} from "three"
import type { MaterialPreset } from "./savant-surfaces"

type AtmosphereProps = {
  time: React.MutableRefObject<number>
  preset: MaterialPreset
}

export function ReflectionLighting({
  time,
  preset,
}: AtmosphereProps) {
  const group = useRef<Group>(null)
  const scene = preset.scene

  useFrame(() => {
    if (!group.current) return

    const t = time.current * scene.drift

    group.current.rotation.set(
      Math.sin(t * 0.6) * 0.14,
      t * 0.12,
      scene.tilt + Math.sin(t) * 0.08,
    )
  }, -2)

  return (
    <group ref={group}>
      <Lightformer
        form="rect"
        color="#edf3ff"
        intensity={scene.energy * 1.8}
        position={[0, 3, 4]}
        scale={[4, 2, 1]}
        target={[0, 0, 0]}
      />

      <Lightformer
        form="rect"
        color={preset.accent2}
        intensity={scene.energy}
        position={[2, -2, -4]}
        scale={[3, 0.65, 1]}
        target={[0, 0, 0]}
      />

      {[0, 1, 2, 3, 4, 5].map(i => (
        <Lightformer
          key={i}
          form={scene.form}
          color={
            i % 3 === 0
              ? preset.accent
              : i % 3 === 1
                ? preset.accent2
                : "#eaf2ff"
          }
          intensity={
            scene.energy * (i % 2 === 0 ? 1.1 : 0.65)
          }
          position={[
            Math.cos(i * Math.PI / 3) * 4,
            Math.sin(i * Math.PI / 3) * 3,
            -2 - (i % 2) * 2,
          ]}
          rotation={[0, 0, i * 0.7]}
          scale={[scene.width, scene.stretch, 1]}
          target={[0, 0, 0]}
        />
      ))}
    </group>
  )
}

export function AtmosphereGlow({
  time,
  preset,
}: AtmosphereProps) {
  const targets = useMemo(
    () => [
      new Color(preset.accent),
      new Color(preset.accent2),
    ],
    [preset.accent, preset.accent2],
  )

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uStrength: { value: preset.scene.glow },
      uColor: { value: new Color(preset.accent) },
      uAccent: { value: new Color(preset.accent2) },
      uEnergy: { value: preset.scene.energy },
      uDrift: { value: preset.scene.drift },
      uStyle: { value: preset.style },
    }),
    [],
  )

  useFrame((_, delta) => {
    const blend =
      1 - Math.exp(-5 * Math.min(delta, 0.1))

    uniforms.uTime.value = time.current

    uniforms.uStrength.value +=
      (preset.scene.glow -
        uniforms.uStrength.value) * blend

    uniforms.uEnergy.value +=
      (preset.scene.energy -
        uniforms.uEnergy.value) * blend

    uniforms.uDrift.value +=
      (preset.scene.drift -
        uniforms.uDrift.value) * blend

    uniforms.uStyle.value = preset.style

    uniforms.uColor.value.lerp(
      targets[0],
      blend,
    )

    uniforms.uAccent.value.lerp(
      targets[1],
      blend,
    )
  }, -2)

  return (
    <mesh position={[0, 0.12, -1.9]} renderOrder={-2}>
      <planeGeometry args={[4.6, 4.6]} />

      <shaderMaterial
        uniforms={uniforms}
        transparent
        depthWrite={false}
        depthTest={true}
        blending={AdditiveBlending}
        toneMapped={false}
        vertexShader={`
          varying vec2 vUv;

          void main() {
            vUv = uv;

            gl_Position =
              projectionMatrix *
              modelViewMatrix *
              vec4(position, 1.0);
          }
        `}
        fragmentShader={`
          uniform float uTime;
          uniform float uStrength;
          uniform float uEnergy;
          uniform float uDrift;
          uniform float uStyle;

          uniform vec3 uColor;
          uniform vec3 uAccent;

          varying vec2 vUv;

          float hash21(vec2 p) {
            return fract(
              sin(dot(p, vec2(127.1, 311.7))) *
              43758.5453123
            );
          }

          float noise21(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);

            f = f * f * (3.0 - 2.0 * f);

            return mix(
              mix(
                hash21(i),
                hash21(i + vec2(1.0, 0.0)),
                f.x
              ),
              mix(
                hash21(i + vec2(0.0, 1.0)),
                hash21(i + vec2(1.0, 1.0)),
                f.x
              ),
              f.y
            );
          }

          void main() {
            vec2 p = (vUv - 0.5) * 2.0;

            float t = uTime * uDrift;

            float angle = atan(p.y, p.x);

            float r = length(
              p * vec2(1.0, 1.12)
            );

            float distortion =
              noise21(p * 5.0 + t * 0.15) *
              0.035;

            float warped = r + distortion;

            float breathe =
              0.72 +
              0.18 * sin(t * 1.5) +
              0.1 * sin(t * 2.9 + 0.8);

            float ripple =
              0.5 +
              0.5 * sin(
                warped * 22.0 -
                t * 2.4 +
                sin(angle * 3.0 + t * 0.3) *
                0.4
              );

            float core =
              exp(-warped * warped * 5.5) *
              breathe;

            float halo =
              exp(
                -pow(
                  warped -
                  0.47 -
                  0.025 * sin(t * 0.8),
                  2.0
                ) * 22.0
              ) *
              ripple *
              0.3;

            float outer =
              exp(
                -pow(
                  warped -
                  0.74 -
                  0.035 * sin(t * 0.4),
                  2.0
                ) * 35.0
              ) * 0.13;

            float rays =
              pow(
                abs(
                  sin(
                    angle * 6.0 +
                    t * 0.12
                  )
                ),
                18.0
              ) *
              exp(-warped * 3.5) *
              0.13;

            float spokes =
              pow(
                abs(
                  cos(
                    angle * 9.0 -
                    t * 0.22
                  )
                ),
                28.0
              ) *
              exp(-warped * 4.0) *
              0.09;

            float spiral =
              sin(
                angle * 4.0 -
                warped * 17.0 +
                t * 1.4
              );

            float spiralGlow =
              pow(
                max(spiral, 0.0),
                8.0
              ) *
              exp(-warped * 3.0) *
              0.11;

            float materialPhase =
              uStyle * 0.6180339;

            float chroma =
              0.5 +
              0.5 * sin(
                t * 0.2 +
                warped * 5.0 +
                materialPhase
              );

            vec3 color = mix(
              uColor,
              uAccent,
              chroma
            );

            float energy =
              core +
              halo +
              outer +
              rays +
              spokes +
              spiralGlow;

            float feather =
              1.0 -
              smoothstep(
                0.55,
                0.98,
                warped
              );

            float intensity =
              energy *
              feather *
              uStrength;

            float alpha = clamp(
              intensity *
              min(uEnergy, 2.5),
              0.0,
              0.55
            );

            gl_FragColor = vec4(
              color * energy,
              alpha
            );

            #include <colorspace_fragment>
          }
        `}
      />
    </mesh>
  )
}
