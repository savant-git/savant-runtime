
"use strict";

(function (global) {
  const registered = new WeakMap();

  function requireObject(value, name) {
    if (
      !value ||
      typeof value !== "object" ||
      Array.isArray(value)
    ) {
      throw new TypeError(
        "savant demo adapter: " + name +
        " must be an object"
      );
    }

    return value;
  }

  function requireId(value) {
    if (
      typeof value !== "string" ||
      !/^[a-z][a-z0-9-]*$/.test(value)
    ) {
      throw new TypeError(
        "savant demo adapter: invalid demo identifier"
      );
    }

    return value;
  }

  function normalizeViews(value) {
    if (!Array.isArray(value)) {
      throw new TypeError(
        "savant demo adapter: views must be an array"
      );
    }

    const seen = new Set();

    return value.map((entry) => {
      requireObject(entry, "view");

      const id = requireId(entry.id);

      if (seen.has(id)) {
        throw new Error(
          "savant demo adapter: duplicate view " + id
        );
      }

      seen.add(id);

      return Object.freeze({
        id,
        label: String(entry.label || id)
      });
    });
  }

  function connect(config) {
    requireObject(config, "configuration");

    const id = requireId(config.id);
    const documentRef = config.document || document;

    if (!documentRef.documentElement) {
      throw new Error(
        "savant demo adapter: document unavailable"
      );
    }

    const existing = registered.get(documentRef);

    if (existing) {
      if (existing.id !== id) {
        throw new Error(
          "savant demo adapter: document already assigned"
        );
      }

      return existing;
    }

    const views = normalizeViews(config.views || []);

    const selectors = Object.freeze({
      navigation:
        config.navigationSelector ||
        ".navigation",
      button:
        config.buttonSelector ||
        "[data-view]",
      activeClass:
        config.activeClass ||
        "active"
    });

    const root = documentRef.documentElement;
    const navigation = documentRef.querySelector(
      selectors.navigation
    );

    const viewIds = new Set(
      views.map((view) => view.id)
    );

    root.dataset.savantDemo = id;

    const buttons = navigation
      ? [...navigation.querySelectorAll(
          selectors.button
        )]
      : [];

    if (navigation) {
      navigation.dataset.demoNavigation = "";
    }

    for (const button of buttons) {
      const viewId = button.dataset.view;

      if (!viewIds.has(viewId)) {
        continue;
      }

      button.type = "button";
      button.dataset.demoView = viewId;
    }

    let activeView = null;
    let observer = null;
    let disposed = false;

    function resolveActiveView() {
      for (const button of buttons) {
        if (
          button.classList.contains(
            selectors.activeClass
          ) &&
          viewIds.has(button.dataset.view)
        ) {
          return button.dataset.view;
        }
      }

      return null;
    }

    function synchronize() {
      if (disposed) {
        return;
      }

      const next = resolveActiveView();

      for (const button of buttons) {
        if (!viewIds.has(button.dataset.view)) {
          continue;
        }

        if (button.dataset.view === next) {
          button.setAttribute(
            "aria-current",
            "page"
          );
        } else {
          button.removeAttribute(
            "aria-current"
          );
        }
      }

      if (next === activeView) {
        return;
      }

      const previous = activeView;
      activeView = next;

      if (next) {
        documentRef.dispatchEvent(
          new CustomEvent(
            "savant-demo:view-change",
            {
              detail: {
                demo: id,
                view: next,
                previous
              }
            }
          )
        );
      }
    }

    if (
      navigation &&
      typeof MutationObserver === "function"
    ) {
      observer = new MutationObserver(
        synchronize
      );

      observer.observe(navigation, {
        subtree: true,
        attributes: true,
        attributeFilter: [
          "class"
        ]
      });
    }

    synchronize();

    const instance = Object.freeze({
      id,
      views: Object.freeze(views),
      get activeView() {
        return activeView;
      },
      synchronize,
      destroy() {
        if (disposed) {
          return;
        }

        disposed = true;

        if (observer) {
          observer.disconnect();
          observer = null;
        }

        for (const button of buttons) {
          button.removeAttribute(
            "aria-current"
          );
          delete button.dataset.demoView;
        }

        if (navigation) {
          delete navigation.dataset.demoNavigation;
        }

        delete root.dataset.savantDemo;
        registered.delete(documentRef);
      }
    });

    registered.set(documentRef, instance);

    return instance;
  }

  global.SavantDemoUniversalAdapter = Object.freeze({
    connect
  });
})(window);
