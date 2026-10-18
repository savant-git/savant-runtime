
"use strict";

/*
 * savant universal demonstration framework
 *
 * shared primitives:
 *   demo definition
 *   shade registry
 *   view composition
 *   navigation
 *   lifecycle
 *   event dispatch
 *
 * demo-specific behavior remains owned by each demo.
 * no production execution is implied.
 */

(function (global) {
  const definitions = new Map();
  const shades = new Map();
  const instances = new Map();

  function assert(condition, message) {
    if (!condition) {
      throw new Error(
        "savant demo framework: " + message
      );
    }
  }

  function normalizeId(value) {
    assert(
      typeof value === "string" &&
      /^[a-z][a-z0-9-]*$/.test(value),
      "invalid identifier"
    );

    return value;
  }

  function element(tag, className, content) {
    const node = document.createElement(tag);

    if (className) {
      node.className = className;
    }

    if (content !== undefined) {
      node.textContent = String(content);
    }

    return node;
  }

  function registerShade(definition) {
    assert(
      definition &&
      typeof definition === "object",
      "shade definition required"
    );

    const id = normalizeId(definition.id);

    assert(
      typeof definition.render === "function",
      "shade requires render()"
    );

    assert(
      !shades.has(id),
      "duplicate shade: " + id
    );

    const shade = Object.freeze({
      id,
      render: definition.render,
      mount: definition.mount || null,
      unmount: definition.unmount || null
    });

    shades.set(id, shade);

    return shade;
  }

  function registerDemo(definition) {
    assert(
      definition &&
      typeof definition === "object",
      "demo definition required"
    );

    const id = normalizeId(definition.id);

    assert(
      !definitions.has(id),
      "duplicate demo: " + id
    );

    assert(
      Array.isArray(definition.views) &&
      definition.views.length > 0,
      "demo requires views"
    );

    const viewIds = new Set();

    const views = definition.views.map((view) => {
      const viewId = normalizeId(view.id);

      assert(
        !viewIds.has(viewId),
        "duplicate view: " + viewId
      );

      viewIds.add(viewId);

      assert(
        typeof view.shade === "string",
        "view requires shade identifier"
      );

      return Object.freeze({
        id: viewId,
        title: String(view.title || viewId),
        description: String(view.description || ""),
        shade: normalizeId(view.shade),
        options: Object.freeze({
          ...(view.options || {})
        })
      });
    });

    const demo = Object.freeze({
      id,
      title: String(definition.title || id),
      subtitle: String(definition.subtitle || ""),
      description: String(definition.description || ""),
      status: String(
        definition.status || "illustrative"
      ),
      views: Object.freeze(views),
      initialView: normalizeId(
        definition.initialView || views[0].id
      ),
      createState:
        typeof definition.createState === "function"
          ? definition.createState
          : () => ({}),
      dispose:
        typeof definition.dispose === "function"
          ? definition.dispose
          : null
    });

    assert(
      viewIds.has(demo.initialView),
      "initial view does not exist"
    );

    definitions.set(id, demo);

    return demo;
  }

  function mount(options) {
    assert(
      options &&
      typeof options === "object",
      "mount options required"
    );

    const demoId = normalizeId(options.demo);

    const definition = definitions.get(demoId);

    assert(
      definition,
      "unknown demo: " + demoId
    );

    const root =
      typeof options.root === "string"
        ? document.querySelector(options.root)
        : options.root;

    assert(
      root instanceof HTMLElement,
      "mount root not found"
    );

    assert(
      !instances.has(root),
      "root already mounted"
    );

    for (const view of definition.views) {
      assert(
        shades.has(view.shade),
        "unregistered shade: " + view.shade
      );
    }

    const state = definition.createState();
    const listeners = new Map();

    let currentView = null;
    let activeCleanup = null;
    let disposed = false;

    root.replaceChildren();
    root.classList.add("savant-demo");
    root.dataset.demo = demoId;
    root.dataset.demoStatus = definition.status;

    const shell = element(
      "div",
      "savant-demo__shell"
    );

    const sidebar = element(
      "aside",
      "savant-demo__sidebar"
    );

    const brand = element(
      "div",
      "savant-demo__brand"
    );

    const symbol = element(
      "span",
      "savant-demo__symbol",
      "s"
    );

    const brandText = element(
      "span",
      "savant-demo__brand-text",
      "savant"
    );

    brand.append(symbol, brandText);

    const identity = element(
      "div",
      "savant-demo__identity"
    );

    identity.append(
      element(
        "span",
        "savant-demo__eyebrow",
        "demonstration"
      ),
      element(
        "h1",
        "savant-demo__title",
        definition.title
      ),
      element(
        "p",
        "savant-demo__subtitle",
        definition.subtitle
      )
    );

    const navigation = element(
      "nav",
      "savant-demo__navigation"
    );

    navigation.setAttribute(
      "aria-label",
      "demonstration views"
    );

    const buttons = new Map();

    const main = element(
      "main",
      "savant-demo__main"
    );

    const header = element(
      "header",
      "savant-demo__header"
    );

    const heading = element(
      "h2",
      "savant-demo__view-title"
    );

    const description = element(
      "p",
      "savant-demo__view-description"
    );

    header.append(heading, description);

    const stage = element(
      "section",
      "savant-demo__stage"
    );

    stage.setAttribute(
      "aria-live",
      "polite"
    );

    const footer = element(
      "footer",
      "savant-demo__footer"
    );

    footer.append(
      element(
        "span",
        "",
        "savant / " + definition.id
      ),
      element(
        "span",
        "",
        definition.status + " demonstration"
      )
    );

    main.append(header, stage, footer);
    sidebar.append(brand, identity, navigation);
    shell.append(sidebar, main);
    root.append(shell);

    function emit(type, detail) {
      const callbacks = listeners.get(type);

      if (callbacks) {
        for (const callback of [...callbacks]) {
          callback(detail);
        }
      }

      root.dispatchEvent(
        new CustomEvent(
          "savant-demo:" + type,
          {
            detail,
            bubbles: true
          }
        )
      );
    }

    function on(type, callback) {
      assert(
        typeof callback === "function",
        "event callback required"
      );

      if (!listeners.has(type)) {
        listeners.set(type, new Set());
      }

      listeners.get(type).add(callback);

      return () => {
        listeners.get(type)?.delete(callback);
      };
    }

    const context = {
      demo: definition,
      state,
      root,
      stage,
      emit,
      on,
      element,
      get view() {
        return currentView;
      }
    };

    function navigate(viewId) {
      assert(
        !disposed,
        "instance has been disposed"
      );

      const view = definition.views.find(
        (candidate) => candidate.id === viewId
      );

      assert(
        view,
        "unknown view: " + viewId
      );

      if (currentView?.id === view.id) {
        return;
      }

      if (activeCleanup) {
        activeCleanup();
        activeCleanup = null;
      }

      const shade = shades.get(view.shade);

      currentView = view;

      heading.textContent = view.title;
      description.textContent = view.description;

      for (const [id, button] of buttons) {
        const active = id === view.id;

        button.classList.toggle(
          "is-active",
          active
        );

        if (active) {
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

      stage.replaceChildren();

      const rendered = shade.render({
        ...context,
        view,
        options: view.options
      });

      if (rendered instanceof Node) {
        stage.append(rendered);
      } else if (rendered !== undefined) {
        stage.append(
          document.createTextNode(
            String(rendered)
          )
        );
      }

      if (shade.mount) {
        const cleanup = shade.mount({
          ...context,
          view,
          options: view.options
        });

        if (typeof cleanup === "function") {
          activeCleanup = cleanup;
        }
      }

      emit("navigate", {
        demo: demoId,
        view: view.id,
        shade: view.shade
      });
    }

    for (const view of definition.views) {
      const button = element(
        "button",
        "savant-demo__nav-item",
        view.title
      );

      button.type = "button";

      button.addEventListener(
        "click",
        () => navigate(view.id)
      );

      navigation.append(button);
      buttons.set(view.id, button);
    }

    const instance = Object.freeze({
      definition,
      state,
      root,
      navigate,
      on,
      emit,
      get currentView() {
        return currentView?.id || null;
      },
      destroy() {
        if (disposed) {
          return;
        }

        if (activeCleanup) {
          activeCleanup();
          activeCleanup = null;
        }

        if (definition.dispose) {
          definition.dispose(context);
        }

        disposed = true;
        listeners.clear();
        instances.delete(root);
        root.replaceChildren();
        root.classList.remove("savant-demo");
        delete root.dataset.demo;
        delete root.dataset.demoStatus;
      }
    });

    instances.set(root, instance);

    navigate(definition.initialView);

    return instance;
  }

  function getDemo(id) {
    return definitions.get(id) || null;
  }

  function getShade(id) {
    return shades.get(id) || null;
  }

  function listDemos() {
    return [...definitions.keys()];
  }

  function listShades() {
    return [...shades.keys()];
  }

  global.SavantDemoFramework = Object.freeze({
    registerShade,
    registerDemo,
    mount,
    getDemo,
    getShade,
    listDemos,
    listShades
  });
})(window);
