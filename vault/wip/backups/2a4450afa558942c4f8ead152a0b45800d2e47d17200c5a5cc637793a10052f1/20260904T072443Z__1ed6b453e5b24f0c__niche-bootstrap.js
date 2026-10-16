(() => {
  "use strict";

  const state = {
    ready: false,
    initializedAt: null,
    executableEnvironment: "pending",
    causalField: "pending"
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

      link.addEventListener("load", () => resolve("loaded"), { once: true });
      link.addEventListener("error", () => resolve("degraded"), { once: true });

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

      script.addEventListener("load", () => resolve("loaded"), { once: true });
      script.addEventListener("error", () => resolve("degraded"), { once: true });

      document.body.append(script);
    });
  };

  const loadExecutableEnvironment = async () => {
    const css = await loadStylesheet(
      "niche-executable-environment-style",
      "/assets/niche-executable-environment.css"
    );

    const js = await loadScript(
      "niche-executable-environment-script",
      "/assets/niche-executable-environment.js"
    );

    state.executableEnvironment =
      css === "degraded" || js === "degraded"
        ? "degraded"
        : "loaded";

    document.documentElement.dataset.nicheExecutableEnvironment =
      state.executableEnvironment;
  };

  const loadCausalField = async () => {
    const css = await loadStylesheet(
      "niche-causal-field-style",
      "/assets/niche-causal-field.css"
    );

    const js = await loadScript(
      "niche-causal-field-script",
      "/assets/niche-causal-field.js"
    );

    state.causalField =
      css === "degraded" || js === "degraded"
        ? "degraded"
        : "loaded";

    document.documentElement.dataset.nicheCausalFieldLoad =
      state.causalField;
  };

  const initialize = () => {
    if (state.ready) {
      return;
    }

    state.ready = true;
    state.initializedAt = new Date().toISOString();

    document.documentElement.dataset.nicheFrontend = "ready";

    window.dispatchEvent(
      new CustomEvent("niche:frontend-ready", {
        detail: {
          initializedAt: state.initializedAt,
          authorityEffect: "none"
        }
      })
    );

    void loadExecutableEnvironment();
    void loadCausalField();
  };

  window.NicheBootstrap = Object.freeze({
    state: () => ({
      ready: state.ready,
      initializedAt: state.initializedAt,
      executableEnvironment: state.executableEnvironment,
      causalField: state.causalField,
      authorityEffect: "none"
    })
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
