import type { Capabilities, QualityTier } from "../types";

export function selectQualityTier(c: Capabilities): QualityTier {
  if (!c.webgl2) return "essential";
  if (c.reducedMotion) return "mobile";
  const constrained =
    (c.deviceMemory !== null && c.deviceMemory <= 4) ||
    c.hardwareConcurrency <= 4 ||
    c.maxTextureSize < 8192;
  if (constrained) return "mobile";
  if (
    (c.deviceMemory ?? 8) >= 8 &&
    c.hardwareConcurrency >= 8 &&
    c.maxTextureSize >= 16384 &&
    c.dpr <= 2.5
  )
    return "ultra";
  return "standard";
}
