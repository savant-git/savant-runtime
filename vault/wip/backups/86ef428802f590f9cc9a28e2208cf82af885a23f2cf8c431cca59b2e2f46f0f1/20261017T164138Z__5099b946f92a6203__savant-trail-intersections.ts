
import { Vector2 } from "three"

/**
 * Deterministic, presentation-only intersection projection.
 *
 * Four-way junctions are derived from actual moving trail
 * segments. No permanent crossings or fabricated intersections
 * are introduced.
 */

export type TrailSegment = Readonly<{
  id: string
  emitter: string
  start: Vector2
  end: Vector2
}>

export type TrailIntersection = Readonly<{
  id: string
  first: string
  second: string
  position: Vector2
  angle: number
  strength: number
}>

export type IntersectionOptions = Readonly<{
  perpendicularToleranceDegrees?: number
  endpointMargin?: number
  minimumSegmentLength?: number
  maximumIntersections?: number
}>

const defaults = {
  perpendicularToleranceDegrees: 12,
  endpointMargin: 0.08,
  minimumSegmentLength: 0.0001,
  maximumIntersections: 32,
} as const

const radians = Math.PI / 180

function finiteVector(value: Vector2): boolean {
  return (
    Number.isFinite(value.x) &&
    Number.isFinite(value.y)
  )
}

function cross(a: Vector2, b: Vector2): number {
  return a.x * b.y - a.y * b.x
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function normalizedPair(a: string, b: string): string {
  return a < b ? `${a}:${b}` : `${b}:${a}`
}

function intersection(
  first: TrailSegment,
  second: TrailSegment,
  tolerance: number,
  margin: number,
  minimumLength: number,
): TrailIntersection | null {
  if (
    first.emitter === second.emitter ||
    !finiteVector(first.start) ||
    !finiteVector(first.end) ||
    !finiteVector(second.start) ||
    !finiteVector(second.end)
  ) {
    return null
  }

  const directionA = first.end
    .clone()
    .sub(first.start)

  const directionB = second.end
    .clone()
    .sub(second.start)

  const lengthA = directionA.length()
  const lengthB = directionB.length()

  if (
    lengthA < minimumLength ||
    lengthB < minimumLength
  ) {
    return null
  }

  const cosine = clamp(
    Math.abs(
      directionA.dot(directionB) /
      (lengthA * lengthB)
    ),
    0,
    1,
  )

  // A perpendicular crossing has a dot product of zero.
  const deviation = Math.asin(cosine)

  if (deviation > tolerance) {
    return null
  }

  const denominator = cross(directionA, directionB)

  if (Math.abs(denominator) < 1e-10) {
    return null
  }

  const displacement = second.start
    .clone()
    .sub(first.start)

  const alongA = cross(displacement, directionB) /
    denominator

  const alongB = cross(displacement, directionA) /
    denominator

  // Both segments must extend through the junction.
  // Endpoint touches are not four-way intersections.
  if (
    alongA <= margin ||
    alongA >= 1 - margin ||
    alongB <= margin ||
    alongB >= 1 - margin
  ) {
    return null
  }

  const position = first.start
    .clone()
    .addScaledVector(directionA, alongA)

  const centeredness = Math.min(
    alongA,
    1 - alongA,
    alongB,
    1 - alongB,
  ) * 2

  const angularStrength = 1 -
    deviation / Math.max(tolerance, 1e-8)

  return {
    id: normalizedPair(first.id, second.id),
    first: first.id,
    second: second.id,
    position,
    angle: Math.atan2(directionA.y, directionA.x),
    strength: clamp(
      centeredness *
      (0.45 + angularStrength * 0.55),
      0,
      1,
    ),
  }
}

export function projectTrailIntersections(
  segments: readonly TrailSegment[],
  options: IntersectionOptions = {},
): readonly TrailIntersection[] {
  const toleranceDegrees = clamp(
    options.perpendicularToleranceDegrees ??
      defaults.perpendicularToleranceDegrees,
    0,
    45,
  )

  const margin = clamp(
    options.endpointMargin ??
      defaults.endpointMargin,
    0,
    0.49,
  )

  const minimumLength = Math.max(
    0,
    options.minimumSegmentLength ??
      defaults.minimumSegmentLength,
  )

  const maximum = Math.max(
    0,
    Math.floor(
      options.maximumIntersections ??
        defaults.maximumIntersections,
    ),
  )

  const tolerance = toleranceDegrees * radians

  if (
    maximum === 0 ||
    segments.length < 2
  ) {
    return []
  }

  const found: TrailIntersection[] = []
  const seen = new Set<string>()

  for (let i = 0; i < segments.length; i++) {
    for (let j = i + 1; j < segments.length; j++) {
      const result = intersection(
        segments[i],
        segments[j],
        tolerance,
        margin,
        minimumLength,
      )

      if (!result || seen.has(result.id)) {
        continue
      }

      seen.add(result.id)
      found.push(result)
    }
  }

  found.sort(
    (a, b) =>
      b.strength - a.strength ||
      a.id.localeCompare(b.id),
  )

  return found.slice(0, maximum)
}

/**
 * Temporal persistence for a rendering adapter.
 *
 * A junction appears only after a genuine crossing.
 * Once the crossing disappears, its brightness decays.
 */
export class TrailIntersectionField {
  private readonly entries = new Map<
    string,
    {
      intersection: TrailIntersection
      brightness: number
      lastSeen: number
    }
  >()

  constructor(
    private readonly fadeSeconds = 0.18,
  ) {}

  update(
    intersections: readonly TrailIntersection[],
    now: number,
  ): readonly (
    TrailIntersection & {
      opacity: number
    }
  )[] {
    if (!Number.isFinite(now)) {
      return []
    }

    const present = new Set<string>()

    for (const item of intersections) {
      present.add(item.id)

      const previous = this.entries.get(item.id)

      this.entries.set(item.id, {
        intersection: item,
        brightness: previous
          ? Math.max(
              previous.brightness,
              item.strength,
            )
          : item.strength,
        lastSeen: now,
      })
    }

    const output: Array<
      TrailIntersection & {
        opacity: number
      }
    > = []

    for (const [id, entry] of this.entries) {
      const elapsed = Math.max(
        0,
        now - entry.lastSeen,
      )

      const opacity = present.has(id)
        ? entry.brightness
        : entry.brightness *
          Math.exp(
            -elapsed /
            Math.max(this.fadeSeconds, 0.001),
          )

      if (opacity < 0.015) {
        this.entries.delete(id)
        continue
      }

      output.push({
        ...entry.intersection,
        opacity: clamp(opacity, 0, 1),
      })
    }

    return output.sort(
      (a, b) =>
        b.opacity - a.opacity ||
        a.id.localeCompare(b.id),
    )
  }

  clear(): void {
    this.entries.clear()
  }
}
