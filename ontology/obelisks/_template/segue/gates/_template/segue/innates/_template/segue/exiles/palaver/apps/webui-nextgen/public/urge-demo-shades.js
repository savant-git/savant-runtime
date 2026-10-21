"use strict";

(function (global) {
  const config = Object.freeze({
    defaultShade: "showcase",
    enableConnected: false,
    studio: "./urge-logo-studio-v7.html"
  });

  const shades = Object.freeze({
    showcase: Object.freeze({
      id: "showcase",
      title: "showcase",
      description: "Interactive logo evolution studio",
      source: config.studio,
      execution: "local",
      public: true
    }),

    connected: Object.freeze({
      id: "connected",
      title: "connected",
      description: "Live Urge session interface",
      source: config.studio,
      execution: "backend-required",
      public: false
    })
  });

  function resolve(id) {
    const shade = shades[id];

    if (!shade) return null;

    if (id === "connected" && !config.enableConnected) {
      return null;
    }

    return shade;
  }

  function list() {
    return Object.values(shades).filter(
      shade => shade.public || config.enableConnected
    );
  }

  const api = Object.freeze({
    config,
    resolve,
    list
  });

  Object.defineProperty(global, "SavantUrgeDemoShades", {
    value: api,
    writable: false,
    configurable: false
  });
})(window);
