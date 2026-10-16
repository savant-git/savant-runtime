import type { Capabilities } from "../types";

export function detectCapabilities(): Capabilities {
  const canvas = document.createElement("canvas");
  const gl = canvas.getContext("webgl2", {
    failIfMajorPerformanceCaveat: true,
  });
  const nav = navigator as Navigator & { deviceMemory?: number; gpu?: unknown };
  return {
    webgl2: gl !== null,
    webgpu: Boolean(nav.gpu),
    reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
    hardwareConcurrency: nav.hardwareConcurrency || 2,
    deviceMemory: nav.deviceMemory ?? null,
    maxTextureSize: gl?.getParameter(gl.MAX_TEXTURE_SIZE) ?? 0,
    dpr: Math.min(devicePixelRatio || 1, 3),
    touch: matchMedia("(pointer: coarse)").matches,
  };
}
