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
    provenanceThread: "pending"
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

    return result;
  };

  const loadExecutableEnvironment = () =>
    loadPair({
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
    });

  const loadCausalField = () =>
    loadPair({
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
    });

  const loadSemanticMotion = () =>
    loadPair({
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
    });

  const loadExecutionTunnel = () =>
    loadPair({
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
    });

  const loadConsequencePreview = () =>
    loadPair({
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
    });

  const loadProvenanceThread = () =>
    loadPair({
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
    });

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
            authorityEffect: "none"
          }
        }
      )
    );

    void loadExecutableEnvironment();
    void loadCausalField();
    void loadSemanticMotion();
    void loadExecutionTunnel();
    void loadConsequencePreview();
    void loadProvenanceThread();
  };

  window.NicheBootstrap =
    Object.freeze({
      state: () => ({
        ready: state.ready,
        initializedAt:
          state.initializedAt,
        executableEnvironment:
          state.executableEnvironment,
        causalField:
          state.causalField,
        semanticMotion:
          state.semanticMotion,
        executionTunnel:
          state.executionTunnel,
        consequencePreview:
          state.consequencePreview,
        provenanceThread:
          state.provenanceThread,
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
