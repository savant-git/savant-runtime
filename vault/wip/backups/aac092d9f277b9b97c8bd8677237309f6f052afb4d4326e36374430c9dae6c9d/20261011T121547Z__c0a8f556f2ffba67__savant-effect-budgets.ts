import type {
  SceneQualityTier
} from "./savant-scene-budget"

export type EffectBudget = Readonly<{
  particleDensity: number
  particleTrailLength: number
  reflectionResolution: number
  reflectionUpdateInterval: number
  electricalBranches: number
  electricalUpdateInterval: number
  postprocessingSamples: number
  postprocessingScale: number
}>

const BUDGETS: Readonly<
  Record<SceneQualityTier, EffectBudget>
> = {
  economy: {
    particleDensity: 0.35,
    particleTrailLength: 0.45,
    reflectionResolution: 0.5,
    reflectionUpdateInterval: 4,
    electricalBranches: 2,
    electricalUpdateInterval: 3,
    postprocessingSamples: 4,
    postprocessingScale: 0.5
  },

  balanced: {
    particleDensity: 0.7,
    particleTrailLength: 0.75,
    reflectionResolution: 0.75,
    reflectionUpdateInterval: 2,
    electricalBranches: 4,
    electricalUpdateInterval: 2,
    postprocessingSamples: 8,
    postprocessingScale: 0.75
  },

  cinematic: {
    particleDensity: 1,
    particleTrailLength: 1,
    reflectionResolution: 1,
    reflectionUpdateInterval: 1,
    electricalBranches: 8,
    electricalUpdateInterval: 1,
    postprocessingSamples: 16,
    postprocessingScale: 1
  }
}

export type EffectSubsystem =
  | "particles"
  | "reflections"
  | "electrical"
  | "postprocessing"

export type EffectBudgetOverrides = Readonly<
  Partial<Record<EffectSubsystem, boolean>>
>

export function getEffectBudget(
  tier: SceneQualityTier,
  enabled: EffectBudgetOverrides = {}
): EffectBudget {
  const base = BUDGETS[tier]

  if (!base) {
    throw new Error(
      "Unsupported scene quality tier"
    )
  }

  return {
    particleDensity:
      enabled.particles === false
        ? 0
        : base.particleDensity,

    particleTrailLength:
      enabled.particles === false
        ? 0
        : base.particleTrailLength,

    reflectionResolution:
      enabled.reflections === false
        ? 0
        : base.reflectionResolution,

    reflectionUpdateInterval:
      base.reflectionUpdateInterval,

    electricalBranches:
      enabled.electrical === false
        ? 0
        : base.electricalBranches,

    electricalUpdateInterval:
      base.electricalUpdateInterval,

    postprocessingSamples:
      enabled.postprocessing === false
        ? 0
        : base.postprocessingSamples,

    postprocessingScale:
      enabled.postprocessing === false
        ? 0
        : base.postprocessingScale
  }
}

export function shouldUpdateEffect(
  frame: number,
  interval: number
): boolean {
  if (
    !Number.isSafeInteger(frame) ||
    frame < 0 ||
    !Number.isSafeInteger(interval) ||
    interval < 1
  ) {
    return false
  }

  return frame % interval === 0
}

export function budgetedCount(
  requested: number,
  fraction: number
): number {
  if (
    !Number.isFinite(requested) ||
    !Number.isFinite(fraction)
  ) {
    return 0
  }

  return Math.max(
    0,
    Math.floor(
      Math.max(0, requested) *
      Math.min(1, Math.max(0, fraction))
    )
  )
}
