const MOBILE_BREAKPOINT = 900;
const NARROW_BREAKPOINT = 600;

function hasWindow() {
  return typeof window !== "undefined";
}

function mediaMatches(query) {
  return (
    hasWindow() &&
    typeof window.matchMedia === "function" &&
    window.matchMedia(query).matches
  );
}

function getViewport() {
  if (!hasWindow()) {
    return {
      width: 1440,
      height: 900
    };
  }

  return {
    width:
      window.innerWidth ||
      document.documentElement
        .clientWidth ||
      1440,

    height:
      window.innerHeight ||
      document.documentElement
        .clientHeight ||
      900
  };
}

function getMemory() {
  if (
    !hasWindow() ||
    !navigator.deviceMemory
  ) {
    return null;
  }

  return Number(
    navigator.deviceMemory
  );
}

function getCores() {
  if (
    !hasWindow() ||
    !navigator.hardwareConcurrency
  ) {
    return null;
  }

  return Number(
    navigator.hardwareConcurrency
  );
}

function getReducedMotion() {
  return mediaMatches(
    "(prefers-reduced-motion: reduce)"
  );
}

function getReducedData() {
  if (!hasWindow()) {
    return false;
  }

  const connection =
    navigator.connection ||
    navigator.mozConnection ||
    navigator.webkitConnection;

  return Boolean(
    connection?.saveData
  );
}

function getPointerProfile() {
  return {
    coarse: mediaMatches(
      "(pointer: coarse)"
    ),

    hover: mediaMatches(
      "(hover: hover)"
    )
  };
}

function classifyTier({
  width,
  memory,
  cores,
  coarse,
  reducedData
}) {
  if (
    reducedData ||
    width <= NARROW_BREAKPOINT
  ) {
    return "low";
  }

  if (
    memory !== null &&
    memory <= 4
  ) {
    return "low";
  }

  if (
    cores !== null &&
    cores <= 4
  ) {
    return "low";
  }

  if (
    width <=
      MOBILE_BREAKPOINT ||
    coarse
  ) {
    return "medium";
  }

  if (
    memory !== null &&
    memory < 8
  ) {
    return "medium";
  }

  return "high";
}

export function getQualityProfile() {
  const {
    width,
    height
  } = getViewport();

  const memory =
    getMemory();

  const cores =
    getCores();

  const reducedMotion =
    getReducedMotion();

  const reducedData =
    getReducedData();

  const {
    coarse,
    hover
  } =
    getPointerProfile();

  const tier =
    classifyTier({
      width,
      memory,
      cores,
      coarse,
      reducedData
    });

  const mobile =
    width <=
      MOBILE_BREAKPOINT ||
    coarse;

  const narrow =
    width <=
    NARROW_BREAKPOINT;

  if (tier === "low") {
    return {
      tier,
      width,
      height,
      mobile,
      narrow,
      coarse,
      hover,
      reducedMotion,
      reducedData,

      dpr: 1,
      postprocessing: false,
      shadows: false,

      antialias: false,
      powerPreference:
        "high-performance",

      starMultiplier: 0.32,
      dustMultiplier: 0.18,
      particleMultiplier: 0.16,
      asteroidMultiplier: 0.16,

      photons: false,
      bloom: false,
      noise: false,
      vignette: false,

      lensEffects: false,
      focusEffects: false,
      atmosphericEffects: true,
      foregroundEffects: true,

      planetSegments: 40,
      moonSegments: 36,
      detailSegments: 20,

      cityLights: 42,
      moonCraters: 12,

      targetFps: 30
    };
  }

  if (tier === "medium") {
    return {
      tier,
      width,
      height,
      mobile,
      narrow,
      coarse,
      hover,
      reducedMotion,
      reducedData,

      dpr: Math.min(
        hasWindow()
          ? window.devicePixelRatio ||
              1
          : 1,
        1.35
      ),

      postprocessing: true,
      shadows: false,

      antialias: true,
      powerPreference:
        "high-performance",

      starMultiplier: 0.62,
      dustMultiplier: 0.48,
      particleMultiplier: 0.44,
      asteroidMultiplier: 0.45,

      photons: true,
      bloom: true,
      noise: false,
      vignette: true,

      lensEffects: true,
      focusEffects: false,
      atmosphericEffects: true,
      foregroundEffects: true,

      planetSegments: 64,
      moonSegments: 56,
      detailSegments: 28,

      cityLights: 92,
      moonCraters: 22,

      targetFps: 45
    };
  }

  return {
    tier,
    width,
    height,
    mobile,
    narrow,
    coarse,
    hover,
    reducedMotion,
    reducedData,

    dpr: Math.min(
      hasWindow()
        ? window.devicePixelRatio ||
            1
        : 1,
      1.75
    ),

    postprocessing: true,
    shadows: true,

    antialias: true,
    powerPreference:
      "high-performance",

    starMultiplier: 1,
    dustMultiplier: 1,
    particleMultiplier: 1,
    asteroidMultiplier: 1,

    photons: true,
    bloom: true,
    noise: true,
    vignette: true,

    lensEffects: true,
    focusEffects: true,
    atmosphericEffects: true,
    foregroundEffects: true,

    planetSegments: 96,
    moonSegments: 88,
    detailSegments: 36,

    cityLights: 160,
    moonCraters: 32,

    targetFps: 60
  };
}

export function isLowQuality() {
  return (
    getQualityProfile()
      .tier === "low"
  );
}

export function isMobileQuality() {
  return getQualityProfile()
    .mobile;
}
