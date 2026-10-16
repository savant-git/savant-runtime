import { useEffect, useRef } from "react"
import { useFrame, useThree } from "@react-three/fiber"

export type SceneQualityTier = "economy" | "balanced" | "cinematic"

export type SceneBudgetProps = {
  active: boolean
  onQualityChange?: (tier: SceneQualityTier) => void
}

const MIN_DPR = 0.75
const MAX_DPR = 2
const SAMPLE_SECONDS = 3
const MIN_FRAMES = 45

function qualityTier(dpr: number, cap: number): SceneQualityTier {
  const ratio = dpr / Math.max(cap, MIN_DPR)
  return ratio < 0.7 ? "economy" : ratio < 0.9 ? "balanced" : "cinematic"
}

/** Presentation-only frame-time controller. No authoritative state is changed. */
export function SceneBudget({ active, onQualityChange }: SceneBudgetProps) {
  const { gl, setDpr } = useThree()
  const visible = useRef(true)
  const reducedMotion = useRef(false)
  const callback = useRef(onQualityChange)
  const stats = useRef({
    elapsed: 0,
    frames: 0,
    slow: 0,
    fast: 0,
    cooldown: 0,
    cap: 1,
    tier: "cinematic" as SceneQualityTier
  })

  useEffect(() => {
    callback.current = onQualityChange
  }, [onQualityChange])

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)")
    const refresh = () => {
      stats.current.cap = Math.max(MIN_DPR, Math.min(MAX_DPR, window.devicePixelRatio || 1))
    }
    const reset = () => {
      stats.current.elapsed = 0
      stats.current.frames = 0
      stats.current.slow = 0
      stats.current.fast = 0
    }
    const visibility = () => {
      visible.current = !document.hidden
      reset()
    }
    const updateMotion = () => {
      reducedMotion.current = motion.matches
      reset()
    }

    refresh()
    visibility()
    updateMotion()
    window.addEventListener("resize", refresh, { passive: true })
    document.addEventListener("visibilitychange", visibility)
    motion.addEventListener("change", updateMotion)
    return () => {
      window.removeEventListener("resize", refresh)
      document.removeEventListener("visibilitychange", visibility)
      motion.removeEventListener("change", updateMotion)
    }
  }, [])

  useFrame((_, delta) => {
    const s = stats.current
    if (!active || !visible.current || reducedMotion.current || delta <= 0 || delta > 0.12) {
      s.elapsed = 0
      s.frames = 0
      s.slow = 0
      s.fast = 0
      return
    }

    s.elapsed += delta
    s.frames += 1
    s.cooldown += delta
    if (s.elapsed < SAMPLE_SECONDS || s.frames < MIN_FRAMES) return

    const average = s.elapsed / s.frames
    s.elapsed = 0
    s.frames = 0
    s.slow = average > 0.027 ? s.slow + 1 : 0
    s.fast = average < 0.017 ? s.fast + 1 : 0
    if (s.cooldown < 5) return

    const current = gl.getPixelRatio()
    let next = current > s.cap + 0.025 ? s.cap : current
    if (next === current && s.slow >= 2) next = Math.max(MIN_DPR, current - 0.2)
    else if (next === current && s.fast >= 4 && s.cooldown >= 12) {
      next = Math.min(s.cap, current + 0.15)
    }

    if (Math.abs(next - current) <= 0.025) return
    setDpr(next)
    s.cooldown = 0
    s.slow = 0
    s.fast = 0

    const tier = qualityTier(next, s.cap)
    if (tier !== s.tier) {
      s.tier = tier
      callback.current?.(tier)
    }
  }, -1)

  return null
}
