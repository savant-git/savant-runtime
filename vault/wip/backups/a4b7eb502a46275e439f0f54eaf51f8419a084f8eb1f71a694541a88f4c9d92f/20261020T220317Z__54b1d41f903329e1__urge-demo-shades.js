"use strict";

(function (global) {
  const shades = Object.freeze({
    showcase: Object.freeze({
      id: "showcase",
      title: "urge / showcase",
      description: "interactive logo evolution studio",
      source: "./urge-logo-studio-v7.html",
      execution: "local",
      public: true
    }),

    connected: Object.freeze({
      id: "connected",
      title: "urge / connected",
      description: "studio with live session controls",
      source: "./urge-logo-studio-v7.html",
      execution: "backend-required",
      public: false
    })
  });

  function resolve(name) {
    return shades[name] || null;
  }

  function list() {
    return Object.values(shades);
  }

  Object.defineProperty(global, "SavantUrgeDemoShades", {
    value: Object.freeze({ resolve, list }),
    writable: false,
    configurable: false
  });
})(window);
