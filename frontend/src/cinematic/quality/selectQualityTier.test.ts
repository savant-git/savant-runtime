import { describe, expect, it } from "vitest";
import type { Capabilities } from "../types";
import { selectQualityTier } from "./selectQualityTier";

const capable: Capabilities = {
  webgl2: true,
  webgpu: true,
  reducedMotion: false,
  hardwareConcurrency: 12,
  deviceMemory: 16,
  maxTextureSize: 16384,
  dpr: 2,
  touch: false,
};
describe("quality selection", () => {
  it("selects ultra for capable desktop", () =>
    expect(selectQualityTier(capable)).toBe("ultra"));
  it("selects essential when WebGL2 is unavailable even if WebGPU exists", () =>
    expect(selectQualityTier({ ...capable, webgl2: false })).toBe("essential"));
  it("selects mobile for Moto G-class constraints", () =>
    expect(
      selectQualityTier({
        ...capable,
        hardwareConcurrency: 4,
        deviceMemory: 4,
        maxTextureSize: 4096,
        touch: true,
      }),
    ).toBe("mobile"));
  it("selects reduced motion profile", () =>
    expect(selectQualityTier({ ...capable, reducedMotion: true })).toBe(
      "mobile",
    ));
  it("selects standard between extremes", () =>
    expect(
      selectQualityTier({
        ...capable,
        hardwareConcurrency: 6,
        deviceMemory: 8,
        maxTextureSize: 8192,
      }),
    ).toBe("standard"));
});
