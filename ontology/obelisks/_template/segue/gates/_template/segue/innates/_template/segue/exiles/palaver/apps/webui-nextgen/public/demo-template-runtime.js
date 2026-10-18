
"use strict";

(async function () {
  const registry = window.SavantDemoTemplateRegistry;
  const host = document.getElementById("demo-host");

  if (!registry || !host) {
    throw new Error(
      "savant demo template: registry or host unavailable"
    );
  }

  const params = new URLSearchParams(
    window.location.search
  );

  const demoId = params.get("demo") || "urge";
  const definition = registry.get(demoId);

  function renderError(message) {
    host.replaceChildren();

    const section = document.createElement("section");
    const heading = document.createElement("h1");
    const detail = document.createElement("p");

    section.className = "demo-host__error";
    heading.textContent = "Demonstration unavailable";
    detail.textContent = String(message);

    section.append(heading, detail);
    host.append(section);
  }

  if (!definition) {
    renderError(
      "Unknown demonstration: " + demoId
    );
    return;
  }

  function resolveAsset(source) {
    const url = new URL(
      source,
      document.baseURI
    );

    if (url.origin !== window.location.origin) {
      throw new Error(
        "Cross-origin demonstration assets are not permitted"
      );
    }

    return url;
  }

  function validateTokens(tokens) {
    const result = {};

    for (const [name, value] of Object.entries(
      tokens || {}
    )) {
      if (!/^--[a-z][a-z0-9-]*$/.test(name)) {
        throw new Error(
          "Invalid demonstration token: " + name
        );
      }

      if (
        typeof value !== "string" &&
        typeof value !== "number"
      ) {
        throw new TypeError(
          "Invalid demonstration token value"
        );
      }

      result[name] = String(value);
    }

    return result;
  }

  function validateLabels(labels) {
    const result = {};

    for (const [selector, value] of Object.entries(
      labels || {}
    )) {
      if (typeof selector !== "string") {
        throw new TypeError(
          "Invalid demonstration label selector"
        );
      }

      document.createDocumentFragment()
        .querySelector(selector);

      result[selector] = String(value);
    }

    return result;
  }

  try {
    const template = resolveAsset(
      definition.template
    );

    const styles = definition.styles.map(
      (source) => resolveAsset(source).href
    );

    const scripts = definition.scripts.map(
      (source) => resolveAsset(source).href
    );

    const tokens = validateTokens(
      definition.tokens
    );

    const labels = validateLabels(
      definition.labels
    );

    const response = await fetch(
      template,
      {
        credentials: "same-origin",
        cache: "no-cache"
      }
    );

    if (!response.ok) {
      throw new Error(
        "Template unavailable: HTTP " +
        response.status
      );
    }

    const markup = await response.text();

    const parsed = new DOMParser().parseFromString(
      markup,
      "text/html"
    );

    if (!parsed.body || !parsed.head) {
      throw new Error(
        "Invalid demonstration document"
      );
    }

    /*
     * Preserve the original document lifecycle.
     *
     * Legacy demos may initialize through
     * DOMContentLoaded and rely on their own
     * document, styles, navigation, and events.
     *
     * An iframe provides that lifecycle without
     * rewriting or duplicating their behavior.
     */

    const frame = document.createElement("iframe");

    frame.className = "demo-host__frame";
    frame.title =
      "savant " + definition.title + " demonstration";

    frame.setAttribute(
      "aria-label",
      frame.title
    );

    frame.setAttribute(
      "referrerpolicy",
      "same-origin"
    );

    frame.setAttribute(
      "sandbox",
      "allow-scripts allow-same-origin allow-forms allow-modals"
    );

    const base = parsed.createElement("base");
    base.href = template.href;

    parsed.head.prepend(base);

    /*
     * The template owns its original scripts
     * and styles. Do not execute duplicates.
     */

    const existingStyles = new Set(
      [...parsed.querySelectorAll(
        'link[rel="stylesheet"][href]'
      )].map((link) => {
        return new URL(
          link.getAttribute("href"),
          template
        ).href;
      })
    );

    const existingScripts = new Set(
      [...parsed.querySelectorAll(
        "script[src]"
      )].map((script) => {
        return new URL(
          script.getAttribute("src"),
          template
        ).href;
      })
    );

    for (const source of styles) {
      if (existingStyles.has(source)) {
        continue;
      }

      const link = parsed.createElement("link");
      link.rel = "stylesheet";
      link.href = source;

      parsed.head.append(link);
    }

    for (const source of scripts) {
      if (existingScripts.has(source)) {
        continue;
      }

      const script = parsed.createElement("script");
      script.src = source;
      script.defer = true;

      parsed.head.append(script);
    }

    /*
     * Apply configuration before the original
     * scripts initialize.
     */

    for (const [selector, value] of Object.entries(
      labels
    )) {
      for (const node of parsed.querySelectorAll(
        selector
      )) {
        node.textContent = value;
      }
    }

    for (const [name, value] of Object.entries(
      tokens
    )) {
      parsed.documentElement.style.setProperty(
        name,
        value
      );
    }

    const title =
      "savant | " + definition.title;

    document.title = title;
    parsed.title = title;

    host.replaceChildren(frame);

    let loaded = false;

    frame.addEventListener(
      "load",
      async () => {
        if (loaded) {
          return;
        }

        loaded = true;

        const childWindow = frame.contentWindow;
        const childDocument = frame.contentDocument;

        if (!childWindow || !childDocument) {
          renderError(
            "Demonstration document unavailable"
          );
          return;
        }

        try {
          if (definition.setup) {
            await definition.setup({
              id: definition.id,
              root: childDocument.body,
              window: childWindow,
              document: childDocument,
              frame,
              tokens
            });
          }

          document.dispatchEvent(
            new CustomEvent(
              "savant-demo:ready",
              {
                detail: {
                  id: definition.id,
                  title: definition.title,
                  frame
                }
              }
            )
          );
        } catch (error) {
          console.error(
            "savant demonstration setup failed",
            error
          );

          renderError(
            error instanceof Error
              ? error.message
              : "Demonstration setup failed"
          );
        }
      },
      { once: true }
    );

    frame.srcdoc =
      "<!doctype html>\n" +
      parsed.documentElement.outerHTML;
  } catch (error) {
    console.error(
      "savant demonstration initialization failed",
      error
    );

    renderError(
      error instanceof Error
        ? error.message
        : "Unknown demonstration failure"
    );
  }
})();
