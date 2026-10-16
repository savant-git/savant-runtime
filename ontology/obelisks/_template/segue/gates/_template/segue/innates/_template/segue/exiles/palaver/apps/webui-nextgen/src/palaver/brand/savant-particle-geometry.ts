import {
  BoxGeometry,
  BufferGeometry,
  Float32BufferAttribute,
  IcosahedronGeometry,
  OctahedronGeometry,
  SphereGeometry,
  TetrahedronGeometry,
  TorusGeometry,
} from "three"
import type { ParticleShape } from "./savant-surfaces"

function combine(parts: BufferGeometry[]): BufferGeometry {
  const positions: number[] = []
  const normals: number[] = []
  const uvs: number[] = []

  for (const original of parts) {
    const geometry = original.index ? original.toNonIndexed() : original
    const position = geometry.getAttribute("position")
    const normal = geometry.getAttribute("normal")
    const uv = geometry.getAttribute("uv")

    for (let i = 0; i < position.count; i++) {
      positions.push(position.getX(i), position.getY(i), position.getZ(i))
      normals.push(normal.getX(i), normal.getY(i), normal.getZ(i))
      uvs.push(uv ? uv.getX(i) : 0, uv ? uv.getY(i) : 0)
    }

    if (geometry !== original) geometry.dispose()
    original.dispose()
  }

  const result = new BufferGeometry()
  result.setAttribute("position", new Float32BufferAttribute(positions, 3))
  result.setAttribute("normal", new Float32BufferAttribute(normals, 3))
  result.setAttribute("uv", new Float32BufferAttribute(uvs, 2))
  result.computeBoundingSphere()
  result.computeBoundingBox()
  return result
}

function sculptSphere(shape: ParticleShape): BufferGeometry {
  const geometry = new SphereGeometry(1, 32, 20)
  const position = geometry.getAttribute("position")

  for (let i = 0; i < position.count; i++) {
    const x = position.getX(i)
    const y = position.getY(i)
    const z = position.getZ(i)
    const azimuth = Math.atan2(z, x)

    if (shape === "ribbon" || shape === "leaf") {
      const twist = y * (shape === "ribbon" ? 2.6 : 0.8)
      const width = shape === "leaf" ? 0.6 * (1 - 0.45 * y * y) : 0.42
      const thickness = shape === "leaf" ? 0.065 : 0.045
      position.setXYZ(
        i,
        x * width * Math.cos(twist) + z * thickness * Math.sin(twist),
        y * 1.6,
        -x * width * Math.sin(twist) + z * thickness * Math.cos(twist),
      )
      continue
    }

    const taper = shape === "drop"
      ? 1 - 0.36 * y
      : shape === "flame"
        ? 0.7 - 0.45 * y
        : 1
    const lobes = shape === "spore"
      ? 1 + 0.12 * Math.sin(azimuth * 6) * Math.sin(y * 8)
      : 1
    position.setXYZ(
      i,
      x * taper * lobes,
      y * (shape === "flame" ? 1.9 : 1),
      z * taper * lobes,
    )
  }

  position.needsUpdate = true
  geometry.computeVertexNormals()
  geometry.computeBoundingSphere()
  geometry.computeBoundingBox()
  return geometry
}

/** Geometry is created on preset changes, never in the animation loop. */
export function particleGeometry(shape: ParticleShape): BufferGeometry {
  if (shape === "ring") {
    return new TorusGeometry(0.85, 0.12, 12, 48)
  }

  if (shape === "reticle") {
    const parts: BufferGeometry[] = [new TorusGeometry(0.7, 0.055, 6, 32)]
    for (let i = 0; i < 4; i++) {
      const tick = new BoxGeometry(0.5, 0.065, 0.065)
      tick.translate(0.9, 0, 0)
      tick.rotateZ(i * Math.PI / 2)
      parts.push(tick)
    }
    return combine(parts)
  }

  if (shape === "flake") {
    const parts: BufferGeometry[] = []
    for (let i = 0; i < 6; i++) {
      const angle = i * Math.PI / 3
      const stem = new BoxGeometry(0.07, 1, 0.07)
      stem.translate(0, 0.45, 0)
      stem.rotateZ(angle)
      parts.push(stem)
      for (const sign of [-1, 1]) {
        const branch = new BoxGeometry(0.055, 0.45, 0.055)
        branch.rotateZ(sign * 0.65)
        branch.translate(sign * 0.13, 0.55, 0)
        branch.rotateZ(angle)
        parts.push(branch)
      }
    }
    return combine(parts)
  }

  if (shape === "shard") {
    const core = new OctahedronGeometry(1, 0).scale(0.56, 1.65, 0.56)
    const satellites: BufferGeometry[] = [core]
    for (let i = 0; i < 3; i++) {
      const chip = new TetrahedronGeometry(0.28, 0)
      chip.scale(0.6, 1.5, 0.7)
      chip.rotateZ(i * 2.0943951)
      chip.translate(Math.cos(i * 2.0943951) * 0.65, -0.15 + i * 0.16, Math.sin(i * 2.0943951) * 0.18)
      satellites.push(chip)
    }
    return combine(satellites)
  }

  if (shape === "splinter") {
    const geometry = new IcosahedronGeometry(1, 1)
    const positions = geometry.getAttribute("position")
    for (let i = 0; i < positions.count; i++) {
      const x = positions.getX(i)
      const y = positions.getY(i)
      const z = positions.getZ(i)
      const serration = 1 + 0.12 * Math.sin(y * 17 + x * 9)
      positions.setXYZ(i, x * 0.42 * serration, y * 1.9, z * 0.16 * serration)
    }
    positions.needsUpdate = true
    geometry.computeVertexNormals()
    geometry.computeBoundingSphere()
    return geometry
  }

  if (shape === "tile") {
    const body = new BoxGeometry(1.6, 1.1, 0.18)
    const bevelLikeRidge = new BoxGeometry(1.42, 0.08, 0.23)
    bevelLikeRidge.translate(0, 0.43, 0)
    return combine([body, bevelLikeRidge])
  }

  return sculptSphere(shape)
}
