export const CINEMATIC = {
  duration: 18.5,
  reducedMotionDuration: 3.5,
  skipAvailableAt: 2,
  assetTimeoutMs: 12_000,
  transitionDuration: 1.2,
  deterministicSeed: 71326,
  readinessTimeoutMs: 20_000,
  acts: {
    signal: [0, 3.1],
    fracture: [3.1, 7.1],
    awakening: [7.1, 12.1],
    forge: [12.1, 16.2],
    recognition: [16.2, 18.5],
  },
} as const;

export const smooth = (start: number, end: number, value: number) => {
  const t = Math.min(1, Math.max(0, (value - start) / (end - start)));
  return t * t * (3 - 2 * t);
};
