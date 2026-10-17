
import React, { useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  Group,
  LineBasicMaterial,
  Mesh,
  PointLight,
  Vector3,
} from "three"
import { savantContour } from "./savant-contour-data"

type Props = {
  time: React.MutableRefObject<number>
  active: boolean
  color?: string
}

const gold = new Color("#e5ad39")
const pink = new Color("#ef6ca5")
const front = 0.18
const back = -0.18
const step = 0.055
const tracerSpeed = 0.19

type ContourSample = {
  point: Vector3
  tangent: Vector3
}

function buildContour() {
  const points = savantContour.map(
    ([x, y]) => new Vector3(x, y, 0),
  )

  const lengths = [0]
  let total = 0

  for (let i = 1; i < points.length; i++) {
    total += points[i].distanceTo(points[i - 1])
    lengths.push(total)
  }

  const closed =
    points.length > 2 &&
    points[0].distanceTo(points[points.length - 1]) < 0.015

  if (!closed && points.length > 2) {
    total += points[points.length - 1].distanceTo(points[0])
  }

  function sample(distance: number): ContourSample {
    const d = ((distance % total) + total) % total

    for (let i = 1; i < points.length; i++) {
      if (d > lengths[i]) continue

      const span = Math.max(
        lengths[i] - lengths[i - 1],
        1e-8,
      )

      const fraction = (d - lengths[i - 1]) / span
      const a = points[i - 1]
      const b = points[i]

      return {
        point: a.clone().lerp(b, fraction),
        tangent: b.clone().sub(a).normalize(),
      }
    }

    const a = points[points.length - 1]
    const b = points[0]
    const span = Math.max(total - lengths[lengths.length - 1], 1e-8)

    return {
      point: a.clone().lerp(
        b,
        (d - lengths[lengths.length - 1]) / span,
      ),
      tangent: b.clone().sub(a).normalize(),
    }
  }

  return { total, sample }
}

function buildLines(
  contour: ReturnType<typeof buildContour>,
) {
  const positions: number[] = []
  const colors: number[] = []
  const samples = Math.max(
    48,
    Math.ceil(contour.total / step),
  )

  const spacing = contour.total / samples

  function add(
    a: Vector3,
    b: Vector3,
    at: number,
  ) {
    const colorA = gold.clone().lerp(pink, at)
    const colorB = gold.clone().lerp(
      pink,
      Math.min(1, at + spacing / contour.total),
    )

    positions.push(
      a.x, a.y, a.z,
      b.x, b.y, b.z,
    )

    colors.push(
      colorA.r, colorA.g, colorA.b,
      colorB.r, colorB.g, colorB.b,
    )
  }

  for (let i = 0; i < samples; i++) {
    const d = i * spacing
    const next = (i + 1) * spacing

    const a = contour.sample(d).point
    const b = contour.sample(next).point

    const af = a.clone().setZ(front)
    const ab = a.clone().setZ(back)
    const bf = b.clone().setZ(front)
    const bb = b.clone().setZ(back)

    const t = i / samples

    // Two uninterrupted contour rails.
    add(af, bf, t)
    add(ab, bb, t)

    // Alternating diagonal braces across the extrusion.
    // The crossing is deterministic and follows the contour.
    add(af, bb, t)
    add(ab, bf, t)
  }

  const geometry = new BufferGeometry()

  geometry.setAttribute(
    "position",
    new BufferAttribute(
      new Float32Array(positions),
      3,
    ),
  )

  geometry.setAttribute(
    "color",
    new BufferAttribute(
      new Float32Array(colors),
      3,
    ),
  )

  geometry.computeBoundingSphere()

  return geometry
}

export function SavantContourLight({
  time,
  active,
}: Props) {
  const contour = useMemo(buildContour, [])
  const geometry = useMemo(
    () => buildLines(contour),
    [contour],
  )

  const coreMaterial = useMemo(
    () => new LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.86,
      depthWrite: false,
      toneMapped: false,
    }),
    [],
  )

  const haloMaterial = useMemo(
    () => new LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.24,
      depthWrite: false,
      depthTest: true,
      blending: AdditiveBlending,
      toneMapped: false,
    }),
    [],
  )

  const first = useRef<Mesh>(null)
  const second = useRef<Mesh>(null)
  const firstLight = useRef<PointLight>(null)
  const secondLight = useRef<PointLight>(null)
  const group = useRef<Group>(null)

  useFrame(() => {
    const phase = active
      ? time.current * tracerSpeed
      : 0

    const a = contour.sample(
      phase * contour.total,
    ).point

    const b = contour.sample(
      (phase + 0.5) * contour.total,
    ).point

    a.z = front + 0.018
    b.z = back - 0.018

    first.current?.position.copy(a)
    second.current?.position.copy(b)

    firstLight.current?.position.copy(a)
    secondLight.current?.position.copy(b)

    const pulse = active
      ? 0.88 + 0.12 * Math.sin(time.current * 3.1)
      : 1

    if (group.current) {
      group.current.scale.setScalar(1)
    }

    if (firstLight.current) {
      firstLight.current.intensity = 1.9 * pulse
    }

    if (secondLight.current) {
      secondLight.current.intensity = 1.6 * pulse
    }
  })

  return (
    <group ref={group}>
      <lineSegments
        geometry={geometry}
        material={haloMaterial}
        renderOrder={8}
        frustumCulled={false}
      />

      <lineSegments
        geometry={geometry}
        material={coreMaterial}
        renderOrder={9}
        frustumCulled={false}
      />

      <mesh ref={first} renderOrder={10}>
        <sphereGeometry args={[0.025, 24, 16]} />
        <meshBasicMaterial
          color="#ffe4a0"
          toneMapped={false}
        />
      </mesh>

      <mesh ref={second} renderOrder={10}>
        <sphereGeometry args={[0.025, 24, 16]} />
        <meshBasicMaterial
          color="#e5ad39"
          toneMapped={false}
        />
      </mesh>

      <pointLight
        ref={firstLight}
        color="#e5ad39"
        intensity={1.9}
        distance={0.75}
        decay={2}
      />

      <pointLight
        ref={secondLight}
        color="#e5ad39"
        intensity={1.6}
        distance={0.75}
        decay={2}
      />
    </group>
  )
}
