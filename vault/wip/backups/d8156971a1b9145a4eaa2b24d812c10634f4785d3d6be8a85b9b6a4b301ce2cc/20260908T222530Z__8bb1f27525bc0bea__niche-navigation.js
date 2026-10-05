"use strict";
(() => {
  const BUILD = "atlas-r13.4-entry-activation";
  const APPLICATION_URL = `/assets/atlas/application.js?v=${encodeURIComponent(BUILD)}`;

  let atlasApi = null;
  let bootPromise = null;

  function ensureAtlasEntry() {
    const nav = document.querySelector(".nav");
    if (!nav) return null;

    let button = nav.querySelector('[data-view="navigation"]');
    if (!button) {
      button = document.createElement("button");
      button.type = "button";
      button.dataset.view = "navigation";
      button.textContent = "Atlas";
      button.setAttribute("aria-label", "Open Atlas");
      const causal = nav.querySelector('[data-view="causal"]');
      causal ? nav.insertBefore(button, causal) : nav.append(button);
    }

    button.dataset.atlasBuild = BUILD;
    button.dataset.atlasStatus = atlasApi ? "ready" : "loading";
    button.removeAttribute("disabled");
    return button;
  }

  function markFailure(error) {
    const button = ensureAtlasEntry();
    if (button) {
      button.dataset.atlasStatus = "failed";
      button.textContent = "Atlas !";
      button.title = `Atlas failed to initialize: ${String(error?.message || error)}`;
      button.setAttribute("aria-label", "Atlas failed to initialize");
    }

    document.documentElement.dataset.atlasBuild = `${BUILD}-failed`;
    window.dispatchEvent(new CustomEvent("niche:atlas:error", {
      detail: {
        stage: "module-bootstrap",
        message: String(error?.message || error),
        authority_effect: "none",
        projection_only: true
      }
    }));
    console.error("SAVANT Atlas module bootstrap failed", error);
  }

  async function boot() {
    if (atlasApi) return atlasApi;
    if (bootPromise) return bootPromise;

    bootPromise = (async () => {
      const button = ensureAtlasEntry();
      if (button) {
        button.dataset.atlasStatus = "loading";
        button.textContent = "Atlas";
        button.title = "Loading Atlas";
      }

      const mod = await import(APPLICATION_URL);
      const application = mod.createAtlasApplication();
      const installed = application.install();

      if (installed !== true) {
        throw new Error("Atlas application shell did not install.");
      }

      atlasApi = application.api;
      window.NicheAtlas = atlasApi;
      window.NicheNavigation = atlasApi;

      const readyButton = ensureAtlasEntry();
      if (readyButton) {
        readyButton.dataset.atlasStatus = "ready";
        readyButton.textContent = "Atlas";
        readyButton.title = "Open Atlas";
        readyButton.setAttribute("aria-label", "Open Atlas");
      }

      return atlasApi;
    })();

    try {
      return await bootPromise;
    } catch (error) {
      bootPromise = null;
      markFailure(error);
      throw error;
    }
  }

  async function activate(event) {
    const button = event?.target?.closest?.('.nav [data-view="navigation"]');
    if (!button) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    button.dataset.atlasStatus = atlasApi ? "opening" : "loading";

    try {
      const api = await boot();
      const opened = api.open();
      if (opened === false) {
        throw new Error("Atlas activation returned false.");
      }
      button.dataset.atlasStatus = "active";
    } catch (error) {
      markFailure(error);
    }
  }

  /*
   * Navigation activation belongs to this compatibility entry module.
   * It is installed before the modular Atlas graph resolves, so the Atlas
   * control is actionable immediately instead of depending on lifecycle
   * initialization to bind its own launcher.
   */
  document.addEventListener("click", activate, true);

  function start() {
    ensureAtlasEntry();
    boot().catch(() => {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once: true});
  } else {
    start();
  }
})();
