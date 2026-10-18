import { useEffect, useRef } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { getEffectBudget, type EffectBudget } from "./savant-effect-budgets"

export type SceneQualityTier = "economy" | "balanced" | "cinematic"

export type SceneBudgetProps = {
  active: boolean
  onQualityChange?: (tier: SceneQualityTier) => void
  onEffectBudgetChange?: (budget: EffectBudget) => void
}

const MIN_DPR = 1
const MAX_DPR = 1.75
const SAMPLE_SECONDS = 3
const MIN_FRAMES = 45

function clampDpr(value: number): number {
  return Number.isFinite(value) ? Math.max(MIN_DPR, Math.min(MAX_DPR, value)) : 1
}

export function qualityTier(dpr: number, cap: number): SceneQualityTier {
  const ratio = clampDpr(dpr) / clampDpr(cap)
  return ratio < 0.7 ? "economy" : ratio < 0.9 ? "balanced" : "cinematic"
}

/** Presentation-only frame-time controller; never changes authoritative workspace state. */
export function SceneBudget({ active, onQualityChange, onEffectBudgetChange }: SceneBudgetProps) {
  const { gl, setDpr } = useThree()
  const visible = useRef(true)
  const reducedMotion = useRef(false)
  const qualityCallback = useRef(onQualityChange)
  const budgetCallback = useRef(onEffectBudgetChange)
  const stats = useRef({
    elapsed: 0, frames: 0, slow: 0, fast: 0, cooldown: 0,
    cap: 1, tier: "cinematic" as SceneQualityTier
  })

  const reset = () => {
      const s = stats.current
      s.elapsed = 0; s.frames = 0; s.slow = 0; s.fast = 0; s.cooldown = 0
    }
  const publish = (tier: SceneQualityTier) => {
    if (stats.current.tier === tier) return
    stats.current.tier = tier
    qualityCallback.current?.(tier)
    budgetCallback.current?.(getEffectBudget(tier))
  }

  useEffect(() => {
    qualityCallback.current = onQualityChange
    budgetCallback.current = onEffectBudgetChange
    onQualityChange?.(stats.current.tier)
    onEffectBudgetChange?.(getEffectBudget(stats.current.tier))
  }, [onQualityChange, onEffectBudgetChange])

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)")
    const resolution = () => {
      const s = stats.current
      s.cap = clampDpr(window.devicePixelRatio || 1)
      const current = gl.getPixelRatio()
      const next = Math.min(current, s.cap)
      if (next < current - 0.025) { setDpr(next); reset() }
      publish(qualityTier(next, s.cap))
    }
    const visibility = () => { visible.current = !document.hidden; reset() }
    const updateMotion = () => { reducedMotion.current = motion.matches; reset() }
    resolution(); visibility(); updateMotion()
    window.addEventListener("resize", resolution, { passive: true })
    document.addEventListener("visibilitychange", visibility)
    motion.addEventListener("change", updateMotion)
    return () => {
      window.removeEventListener("resize", resolution)
      document.removeEventListener("visibilitychange", visibility)
      motion.removeEventListener("change", updateMotion)
    }
  }, [gl, setDpr])

  useFrame((_, delta) => {
    const s = stats.current
    if (!active || !visible.current || reducedMotion.current || !Number.isFinite(delta) || delta <= 0 || delta > 0.5) {
      s.elapsed = 0; s.frames = 0; s.slow = 0; s.fast = 0; s.cooldown = 0
      return
    }
    s.elapsed += delta; s.frames += 1; s.cooldown += delta
    if (s.elapsed < SAMPLE_SECONDS || s.frames < MIN_FRAMES) return
    const average = s.elapsed / s.frames
    s.elapsed = 0; s.frames = 0
    s.slow = average > 0.027 ? s.slow + 1 : 0
    s.fast = average < 0.017 ? s.fast + 1 : 0
    if (s.cooldown < 5) return
    const current = gl.getPixelRatio()
    let next = Math.min(current, s.cap)
    if (s.slow >= 2) next = Math.max(MIN_DPR, next - 0.2)
    else if (s.fast >= 4 && s.cooldown >= 12) next = Math.min(s.cap, next + 0.15)
    next = clampDpr(next)
    if (Math.abs(next - current) <= 0.025) {
      if(s.slow>=2&&current<=MIN_DPR+.025&&s.tier!=="economy"){
        publish(s.tier==="cinematic"?"balanced":"economy");reset()
      }else if(s.fast>=4&&s.cooldown>=12&&s.tier!=="cinematic"){
        publish(s.tier==="economy"?"balanced":"cinematic");reset()
      }
      return
    }
    setDpr(next); reset()
    publish(qualityTier(next, s.cap))
  }, -1)
  return null
}
