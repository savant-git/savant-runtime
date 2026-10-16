import type { SceneQualityTier } from "./savant-scene-budget"

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

const budgets: Readonly<Record<SceneQualityTier, EffectBudget>> = {
  economy: {
    particleDensity: 0.35, particleTrailLength: 0.45,
    reflectionResolution: 0.5, reflectionUpdateInterval: 4,
    electricalBranches: 2, electricalUpdateInterval: 3,
    postprocessingSamples: 4, postprocessingScale: 0.5
  },
  balanced: {
    particleDensity: 0.7, particleTrailLength: 0.75,
    reflectionResolution: 0.75, reflectionUpdateInterval: 2,
    electricalBranches: 4, electricalUpdateInterval: 2,
    postprocessingSamples: 8, postprocessingScale: 0.75
  },
  cinematic: {
    particleDensity: 1, particleTrailLength: 1,
    reflectionResolution: 1, reflectionUpdateInterval: 1,
    electricalBranches: 8, electricalUpdateInterval: 1,
    postprocessingSamples: 16, postprocessingScale: 1
  }
}

export function getEffectBudget(tier: SceneQualityTier): EffectBudget {
  const budget = budgets[tier]
  if (!budget) throw new Error("Unsupported scene quality tier")
  return budget
}
