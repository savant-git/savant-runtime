
"use strict";

(async function () {
  const registry = window.SavantDemoTemplateRegistry;
  const host = document.getElementById("demo-host");

  if (!registry || !host) {
    throw new Error(
      "savant demonstration registry or host unavailable"
    );
  }

  const params = new URLSearchParams(
    window.location.search
  );

  const requestedId = params.get("demo") || "urge";
  const definition = registry.get(requestedId);

  if (!definition) {
    host.textContent =
      "Unknown demonstration: " + requestedId;
    return;
  }

  function sameOriginUrl(value) {
    const url = new URL(
      value,
      document.baseURI
    );

    if (url.origin !== window.location.origin) {
      throw new Error(
        "cross-origin demonstration assets are not permitted"
      );
    }

    return url;
  }

  function loadStyle(source) {
    return new Promise((resolve, reject) => {
      const link = document.createElement("link");

      link.rel = "stylesheet";
      link.href = sameOriginUrl(source).href;
      link.onload = resolve;
      link.onerror = () => {
        reject(new Error(
          "stylesheet unavailable: " + source
        ));
      };

      document.head.append(link);
    });
  }

  function loadScript(source) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");

      script.src = sameOriginUrl(source).href;
      script.async = false;
      script.onload = resolve;
      script.onerror = () => {
        reject(new Error(
          "script unavailable: " + source
        ));
      };

      document.body.append(script);
    });
  }

  function applyLabels(labels) {
    for (const [selector, value] of Object.entries(
      labels
    )) {
      let matches;

      try {
        matches = document.querySelectorAll(selector);
      } catch (error) {
        throw new Error(
          "invalid demonstration label selector: " +
          selector,
          { cause: error }
        );
      }

      for (const node of matches) {
        node.textContent = String(value);
      }
    }
  }

  function applyTokens(tokens) {
    for (const [name, value] of Object.entries(tokens)) {
      if (!/^--[a-z][a-z0-9-]*$/.test(name)) {
        throw new Error(
          "invalid demonstration token: " + name
        );
      }

      if (
        typeof value !== "string" &&
        typeof value !== "number"
      ) {
        throw new TypeError(
          "demonstration token must be text or number"
        );
      }

      document.documentElement.style.setProperty(
        name,
        String(value)
      );
    }
  }

  try {
    const templateUrl = sameOriginUrl(
      definition.template
    );

    const response = await fetch(templateUrl, {
      credentials: "same-origin",
      cache: "no-cache"
    });

    if (!response.ok) {
      throw new Error(
        "template request failed: " + response.status
      );
    }

    const markup = await response.text();

    const parsed = new DOMParser().parseFromString(
      markup,
      "text/html"
    );

    if (!parsed.body) {
      throw new Error(
        "demonstration template has no body"
      );
    }

    const imported = document.importNode(
      parsed.body,
      true
    );

    imported.querySelectorAll(
      "script, link[rel='stylesheet'], base"
    ).forEach((node) => node.remove());

    document.title =
      "savant | " + definition.title;

    document.body.replaceChildren(
      ...Array.from(imported.childNodes)
    );

    document.body.dataset.demo = definition.id;

    applyLabels(definition.labels);
    applyTokens(definition.tokens);

    for (const source of definition.styles) {
      await loadStyle(source);
    }

    for (const source of definition.scripts) {
      await loadScript(source);
    }

    if (definition.setup) {
      await definition.setup({
        id: definition.id,
        root: document.body,
        tokens: definition.tokens
      });
    }

    document.dispatchEvent(
      new CustomEvent("savant-demo:ready", {
        detail: {
          id: definition.id,
          title: definition.title
        }
      })
    );
  } catch (error) {
    document.body.replaceChildren();

    const message = document.createElement("main");
    const heading = document.createElement("h1");
    const explanation = document.createElement("p");

    heading.textContent =
      "Demonstration unavailable";

    explanation.textContent =
      error instanceof Error
        ? error.message
        : "Unknown loading failure";

    message.append(heading, explanation);
    document.body.append(message);

    console.error(
      "savant demonstration initialization failed",
      error
    );
  }
})();
