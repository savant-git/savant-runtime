export const POST = {
  bloom: {
    intensity: 0.85,
    luminanceThreshold: 0.78,
    luminanceSmoothing: 0.35,
  },
  vignette: { offset: 0.18, darkness: 0.66 },
  noiseOpacity: 0.022,
  chromaticOffset: [0.00032, 0.00018] as const,
  depthOfField: { focusDistance: 0.018, focalLength: 0.028, bokehScale: 1.5 },
} as const;
