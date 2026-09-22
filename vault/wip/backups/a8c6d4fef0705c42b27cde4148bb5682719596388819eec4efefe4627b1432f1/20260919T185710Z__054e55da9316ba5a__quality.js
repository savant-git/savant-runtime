export function getQualityProfile() {
  if (typeof window === "undefined") {
    return {
      tier: "medium",
      dpr: 1,
      stars: 1800,
      shadows: false,
      postprocessing: false
    };
  }

  const memory = navigator.deviceMemory || 4;
  const cores = navigator.hardwareConcurrency || 4;
  const width = window.innerWidth;
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  if (reducedMotion || memory <= 2 || cores <= 4 || width < 700) {
    return {
      tier: "low",
      dpr: 1,
      stars: 900,
      shadows: false,
      postprocessing: false
    };
  }

  if (memory >= 8 && cores >= 8 && width >= 1200) {
    return {
      tier: "high",
      dpr: Math.min(window.devicePixelRatio, 1.75),
      stars: 3200,
      shadows: true,
      postprocessing: true
    };
  }

  return {
    tier: "medium",
    dpr: Math.min(window.devicePixelRatio, 1.35),
    stars: 1800,
    shadows: false,
    postprocessing: true
  };
}
