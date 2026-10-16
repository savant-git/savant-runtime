import { useEffect, useRef } from "react"
import { useFrame, useThree } from "@react-three/fiber"

export type SceneQualityTier =
  | "economy"
  | "balanced"
  | "cinematic"

export type SceneBudgetProps = {
  active: boolean
  onQualityChange?: (tier: SceneQualityTier) => void
}

const MIN_DPR = 0.75
const MAX_DPR = 2

const SAMPLE_SECONDS = 3
const MIN_FRAMES = 45

const SLOW_FRAME = 0.027
const FAST_FRAME = 0.017

const CHANGE_COOLDOWN = 5
const RECOVERY_COOLDOWN = 12

function clampDpr(value: number): number {
  if (!Number.isFinite(value)) return 1

  return Math.max(
    MIN_DPR,
    Math.min(MAX_DPR, value)
  )
}

export function qualityTier(
  dpr: number,
  cap: number
): SceneQualityTier {
  const ratio =
    clampDpr(dpr) / clampDpr(cap)

  if (ratio < 0.7) return "economy"
  if (ratio < 0.9) return "balanced"

  return "cinematic"
}

type BudgetStats = {
  elapsed: number
  frames: number
  slow: number
  fast: number
  cooldown: number
  cap: number
  tier: SceneQualityTier
}

function resetMeasurements(
  stats: BudgetStats
): void {
  stats.elapsed = 0
  stats.frames = 0
  stats.slow = 0
  stats.fast = 0
  stats.cooldown = 0
}

/**
 * Adaptive presentation budget.
 *
 * Controls renderer pixel ratio without modifying
 * authoritative workspace state.
 */
export function SceneBudget({
  active,
  onQualityChange
}: SceneBudgetProps) {
  const { gl, setDpr } = useThree()

  const visible = useRef(true)
  const reducedMotion = useRef(false)
  const callback = useRef(onQualityChange)

  const stats = useRef<BudgetStats>({
    elapsed: 0,
    frames: 0,
    slow: 0,
    fast: 0,
    cooldown: 0,
    cap: 1,
    tier: "cinematic"
  })

  useEffect(() => {
    callback.current = onQualityChange

    onQualityChange?.(stats.current.tier)
  }, [onQualityChange])

  useEffect(() => {
    const motion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    )

    const publish = (tier: SceneQualityTier) => {
      if (stats.current.tier === tier) return

      stats.current.tier = tier
      callback.current?.(tier)
    }

    const synchronizeResolution = () => {
      const statsValue = stats.current

      statsValue.cap = clampDpr(
        window.devicePixelRatio || 1
      )

      const current = gl.getPixelRatio()
      const next = Math.min(
        current,
        statsValue.cap
      )

      if (next < current - 0.025) {
        setDpr(next)
        resetMeasurements(statsValue)
      }

      publish(
        qualityTier(next, statsValue.cap)
      )
    }

    const synchronizeVisibility = () => {
      visible.current = !document.hidden

      resetMeasurements(stats.current)
    }

    const synchronizeMotion = () => {
      reducedMotion.current = motion.matches

      resetMeasurements(stats.current)
    }

    synchronizeResolution()
    synchronizeVisibility()
    synchronizeMotion()

    window.addEventListener(
      "resize",
      synchronizeResolution,
      { passive: true }
    )

    document.addEventListener(
      "visibilitychange",
      synchronizeVisibility
    )

    motion.addEventListener(
      "change",
      synchronizeMotion
    )

    return () => {
      window.removeEventListener(
        "resize",
        synchronizeResolution
      )

      document.removeEventListener(
        "visibilitychange",
        synchronizeVisibility
      )

      motion.removeEventListener(
        "change",
        synchronizeMotion
      )
    }
  }, [gl, setDpr])

  useFrame((_, delta) => {
    const s = stats.current

    if (
      !active ||
      !visible.current ||
      reducedMotion.current ||
      !Number.isFinite(delta) ||
      delta <= 0 ||
      delta > 0.12
    ) {
      resetMeasurements(s)
      return
    }

    s.elapsed += delta
    s.frames += 1
    s.cooldown += delta

    if (
      s.elapsed < SAMPLE_SECONDS ||
      s.frames < MIN_FRAMES
    ) {
      return
    }

    const average = s.elapsed / s.frames

    s.elapsed = 0
    s.frames = 0

    s.slow =
      average > SLOW_FRAME
        ? s.slow + 1
        : 0

    s.fast =
      average < FAST_FRAME
        ? s.fast + 1
        : 0

    if (s.cooldown < CHANGE_COOLDOWN) {
      return
    }

    const current = gl.getPixelRatio()

    let next = Math.min(
      current,
      s.cap
    )

    if (s.slow >= 2) {
      next = Math.max(
        MIN_DPR,
        next - 0.2
      )
    } else if (
      s.fast >= 4 &&
      s.cooldown >= RECOVERY_COOLDOWN
    ) {
      next = Math.min(
        s.cap,
        next + 0.15
      )
    }

    next = clampDpr(next)

    if (
      Math.abs(next - current) <= 0.025
    ) {
      return
    }

    setDpr(next)

    resetMeasurements(s)

    const tier = qualityTier(
      next,
      s.cap
    )

    if (tier !== s.tier) {
      s.tier = tier
      callback.current?.(tier)
    }
  }, -1)

  return null
}
