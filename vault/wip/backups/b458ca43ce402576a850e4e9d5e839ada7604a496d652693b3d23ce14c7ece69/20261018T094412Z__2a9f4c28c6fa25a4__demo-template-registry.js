
"use strict";

(function (global) {
  const registry = new Map();

  function validId(value) {
    return typeof value === "string" &&
      /^[a-z][a-z0-9-]*$/.test(value);
  }

  function register(definition) {
    if (!definition || !validId(definition.id)) {
      throw new TypeError(
        "demonstration requires a lowercase identifier"
      );
    }

    if (registry.has(definition.id)) {
      throw new Error(
        "duplicate demonstration: " + definition.id
      );
    }

    if (typeof definition.template !== "string") {
      throw new TypeError(
        "demonstration requires a template"
      );
    }

    const config = Object.freeze({
      id: definition.id,
      title: String(definition.title || definition.id),
      template: definition.template,
      styles: Object.freeze([
        ...(definition.styles || [])
      ]),
      scripts: Object.freeze([
        ...(definition.scripts || [])
      ]),
      labels: Object.freeze({
        ...(definition.labels || {})
      }),
      tokens: Object.freeze({
        ...(definition.tokens || {})
      }),
      setup: typeof definition.setup === "function"
        ? definition.setup
        : null
    });

    registry.set(config.id, config);
    return config;
  }

  function get(id) {
    return registry.get(id) || null;
  }

  function list() {
    return [...registry.keys()];
  }

  register({
    id: "urge",
    title: "urge",
    template: "./urge-demo.html",
    styles: [
      "./urge-demo.css"
    ],
    scripts: [
      "./urge-demo.js"
    ],
    labels: {},
    tokens: {}
  });

  global.SavantDemoTemplateRegistry = Object.freeze({
    register,
    get,
    list
  });
})(window);
