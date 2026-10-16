(() => {
  "use strict";

  const state = {
    ready: false,
    initializedAt: null,
    executableEnvironment: "pending",
    causalField: "pending",
    semanticMotion: "pending",
    executionTunnel: "pending",
    consequencePreview: "pending",
    provenanceThread: "pending",
    semanticRuntime: "pending",
    unlockHorizon: "pending",
    blockerRadar: "pending",
    focusCompression: "pending",
    authorityLens: "pending",
    temporalGhost: "pending",
    evidenceGate: "pending",
    dependencyGravity: "pending",
    livingPulse: "pending",
    crossViewContinuity: "pending",
    causalLens: "pending",
    projectionHealth: "pending",
    readinessBoundary: "pending",
    graphics: "pending",
    objectiveGraphics: "pending"
  };

  const loadStylesheet = (id, href) => {
    if (document.getElementById(id)) {
      return Promise.resolve("existing");
    }

    return new Promise(resolve => {
      const link = document.createElement("link");

      link.id = id;
      link.rel = "stylesheet";
      link.href = href;

      link.addEventListener(
        "load",
        () => resolve("loaded"),
        { once: true }
      );

      link.addEventListener(
        "error",
        () => resolve("degraded"),
        { once: true }
      );

      document.head.append(link);
    });
  };

  const loadScript = (id, src) => {
    if (document.getElementById(id)) {
      return Promise.resolve("existing");
    }

    return new Promise(resolve => {
      const script = document.createElement("script");

      script.id = id;
      script.src = src;
      script.defer = true;

      script.addEventListener(
        "load",
        () => resolve("loaded"),
        { once: true }
      );

      script.addEventListener(
        "error",
        () => resolve("degraded"),
        { once: true }
      );

      document.body.append(script);
    });
  };

  const publishSubsystemState = (
    datasetKey,
    value
  ) => {
    document.documentElement.dataset[
      datasetKey
    ] = value;
  };

  const loadPair = async ({
    styleId,
    styleHref,
    scriptId,
    scriptSrc,
    stateKey,
    datasetKey
  }) => {
    const css = await loadStylesheet(
      styleId,
      styleHref
    );

    const js = await loadScript(
      scriptId,
      scriptSrc
    );

    const result =
      css === "degraded" ||
      js === "degraded"
        ? "degraded"
        : "loaded";

    state[stateKey] = result;

    publishSubsystemState(
      datasetKey,
      result
    );

    window.dispatchEvent(
      new CustomEvent(
        "niche:module-load",
        {
          detail: {
            module: stateKey,
            state: result,
            authorityEffect: "none"
          }
        }
      )
    );

    return result;
  };

  const modules = [
    {
      styleId:
        "niche-executable-environment-style",
      styleHref:
        "/assets/niche-executable-environment.css",
      scriptId:
        "niche-executable-environment-script",
      scriptSrc:
        "/assets/niche-executable-environment.js",
      stateKey:
        "executableEnvironment",
      datasetKey:
        "nicheExecutableEnvironment"
    },
    {
      styleId:
        "niche-causal-field-style",
      styleHref:
        "/assets/niche-causal-field.css",
      scriptId:
        "niche-causal-field-script",
      scriptSrc:
        "/assets/niche-causal-field.js",
      stateKey:
        "causalField",
      datasetKey:
        "nicheCausalFieldLoad"
    },
    {
      styleId:
        "niche-motion-style",
      styleHref:
        "/assets/niche-motion.css",
      scriptId:
        "niche-motion-script",
      scriptSrc:
        "/assets/niche-motion.js",
      stateKey:
        "semanticMotion",
      datasetKey:
        "nicheSemanticMotionLoad"
    },
    {
      styleId:
        "niche-execution-tunnel-style",
      styleHref:
        "/assets/niche-execution-tunnel.css",
      scriptId:
        "niche-execution-tunnel-script",
      scriptSrc:
        "/assets/niche-execution-tunnel.js",
      stateKey:
        "executionTunnel",
      datasetKey:
        "nicheExecutionTunnelLoad"
    },
    {
      styleId:
        "niche-consequence-preview-style",
      styleHref:
        "/assets/niche-consequence-preview.css",
      scriptId:
        "niche-consequence-preview-script",
      scriptSrc:
        "/assets/niche-consequence-preview.js",
      stateKey:
        "consequencePreview",
      datasetKey:
        "nicheConsequencePreviewLoad"
    },
    {
      styleId:
        "niche-provenance-thread-style",
      styleHref:
        "/assets/niche-provenance-thread.css",
      scriptId:
        "niche-provenance-thread-script",
      scriptSrc:
        "/assets/niche-provenance-thread.js",
      stateKey:
        "provenanceThread",
      datasetKey:
        "nicheProvenanceThreadLoad"
    },
    {
      styleId:
        "niche-semantic-runtime-style",
      styleHref:
        "/assets/niche-semantic-runtime.css",
      scriptId:
        "niche-semantic-runtime-script",
      scriptSrc:
        "/assets/niche-semantic-runtime.js",
      stateKey:
        "semanticRuntime",
      datasetKey:
        "nicheSemanticRuntimeLoad"
    },
    {
      styleId:
        "niche-unlock-horizon-style",
      styleHref:
        "/assets/niche-unlock-horizon.css",
      scriptId:
        "niche-unlock-horizon-script",
      scriptSrc:
        "/assets/niche-unlock-horizon.js",
      stateKey:
        "unlockHorizon",
      datasetKey:
        "nicheUnlockHorizonLoad"
    },
    {
      styleId:
        "niche-blocker-radar-style",
      styleHref:
        "/assets/niche-blocker-radar.css",
      scriptId:
        "niche-blocker-radar-script",
      scriptSrc:
        "/assets/niche-blocker-radar.js",
      stateKey:
        "blockerRadar",
      datasetKey:
        "nicheBlockerRadarLoad"
    },
    {
      styleId:
        "niche-focus-compression-style",
      styleHref:
        "/assets/niche-focus-compression.css",
      scriptId:
        "niche-focus-compression-script",
      scriptSrc:
        "/assets/niche-focus-compression.js",
      stateKey:
        "focusCompression",
      datasetKey:
        "nicheFocusCompressionLoad"
    },
    {
      styleId:
        "niche-authority-lens-style",
      styleHref:
        "/assets/niche-authority-lens.css",
      scriptId:
        "niche-authority-lens-script",
      scriptSrc:
        "/assets/niche-authority-lens.js",
      stateKey:
        "authorityLens",
      datasetKey:
        "nicheAuthorityLensLoad"
    },
    {
      styleId:
        "niche-temporal-ghost-style",
      styleHref:
        "/assets/niche-temporal-ghost.css",
      scriptId:
        "niche-temporal-ghost-script",
      scriptSrc:
        "/assets/niche-temporal-ghost.js",
      stateKey:
        "temporalGhost",
      datasetKey:
        "nicheTemporalGhostLoad"
    },
    {
      styleId:
        "niche-evidence-gate-style",
      styleHref:
        "/assets/niche-evidence-gate.css",
      scriptId:
        "niche-evidence-gate-script",
      scriptSrc:
        "/assets/niche-evidence-gate.js",
      stateKey:
        "evidenceGate",
      datasetKey:
        "nicheEvidenceGateLoad"
    },
    {
      styleId:
        "niche-dependency-gravity-style",
      styleHref:
        "/assets/niche-dependency-gravity.css",
      scriptId:
        "niche-dependency-gravity-script",
      scriptSrc:
        "/assets/niche-dependency-gravity.js",
      stateKey:
        "dependencyGravity",
      datasetKey:
        "nicheDependencyGravityLoad"
    },
    {
      styleId:
        "niche-living-pulse-style",
      styleHref:
        "/assets/niche-living-pulse.css",
      scriptId:
        "niche-living-pulse-script",
      scriptSrc:
        "/assets/niche-living-pulse.js",
      stateKey:
        "livingPulse",
      datasetKey:
        "nicheLivingPulseLoad"
    },
    {
      styleId:
        "niche-cross-view-continuity-style",
      styleHref:
        "/assets/niche-cross-view-continuity.css",
      scriptId:
        "niche-cross-view-continuity-script",
      scriptSrc:
        "/assets/niche-cross-view-continuity.js",
      stateKey:
        "crossViewContinuity",
      datasetKey:
        "nicheCrossViewContinuityLoad"
    },
    {
      styleId:
        "niche-causal-lens-style",
      styleHref:
        "/assets/niche-causal-lens.css",
      scriptId:
        "niche-causal-lens-script",
      scriptSrc:
        "/assets/niche-causal-lens.js",
      stateKey:
        "causalLens",
      datasetKey:
        "nicheCausalLensLoad"
    },
    {
      styleId:
        "niche-projection-health-style",
      styleHref:
        "/assets/niche-projection-health.css",
      scriptId:
        "niche-projection-health-script",
      scriptSrc:
        "/assets/niche-projection-health.js",
      stateKey:
        "projectionHealth",
      datasetKey:
        "nicheProjectionHealthLoad"
    },
    {
      styleId:
        "niche-readiness-boundary-style",
      styleHref:
        "/assets/niche-readiness-boundary.css",
      scriptId:
        "niche-readiness-boundary-script",
      scriptSrc:
        "/assets/niche-readiness-boundary.js",
      stateKey:
        "readinessBoundary",
      datasetKey:
        "nicheReadinessBoundaryLoad"
    },
    {
      styleId:
        "niche-graphics-style",
      styleHref:
        "/assets/niche-graphics.css",
      scriptId:
        "niche-graphics-script",
      scriptSrc:
        "/assets/niche-graphics.js",
      stateKey:
        "graphics",
      datasetKey:
        "nicheGraphicsLoad"
    },
    {
      styleId:
        "niche-objective-graphics-style",
      styleHref:
        "/assets/niche-objective-graphics.css",
      scriptId:
        "niche-objective-graphics-script",
      scriptSrc:
        "/assets/niche-objective-graphics.js",
      stateKey:
        "objectiveGraphics",
      datasetKey:
        "nicheObjectiveGraphicsLoad"
    }
  ];

  const initialize = () => {
    if (state.ready) {
      return;
    }

    state.ready = true;
    state.initializedAt =
      new Date().toISOString();

    document.documentElement.dataset
      .nicheFrontend = "ready";

    window.dispatchEvent(
      new CustomEvent(
        "niche:frontend-ready",
        {
          detail: {
            initializedAt:
              state.initializedAt,
            moduleCount:
              modules.length,
            authorityEffect: "none"
          }
        }
      )
    );

    modules.forEach(module => {
      void loadPair(module);
    });
  };

  window.NicheBootstrap =
    Object.freeze({
      state: () => ({
        ...state,
        moduleCount:
          modules.length,
        authorityEffect: "none"
      })
    });

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      initialize,
      { once: true }
    );
  } else {
    initialize();
  }
})();
