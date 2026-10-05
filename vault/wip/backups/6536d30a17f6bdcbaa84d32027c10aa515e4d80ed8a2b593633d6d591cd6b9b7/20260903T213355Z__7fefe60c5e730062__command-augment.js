"use strict";

/*
 * niche command augmentation
 *
 * projection-only interaction layer.
 * does not own task authority, task state, graph authority,
 * masterplan authority, or durable mutation.
 */

(() => {
  const storageKey =
    "savant:niche:command:augment:v1";

  const defaults = Object.freeze({
    density: "comfortable",
    focusMode: false,
    autoRefresh: true,
    refreshSeconds: 10,
    view: "cockpit",
    query: "",
    lastTask: "",
  });

  const runtime = {
    settings: {
      ...defaults,
    },
    timer: null,
    staleTimer: null,
    lastRefresh: Date.now(),
    observer: null,
  };

  function readSettings() {
    try {
      const value =
        JSON.parse(
          localStorage.getItem(
            storageKey
          ) || "{}"
        );

      runtime.settings = {
        ...defaults,
        ...value,
      };
    } catch {
      runtime.settings = {
        ...defaults,
      };
    }
  }

  function saveSettings() {
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify(
          runtime.settings
        )
      );
    } catch {
      return;
    }
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function all(selector) {
    return Array.from(
      document.querySelectorAll(
        selector
      )
    );
  }

  function text(value) {
    return String(
      value == null
        ? ""
        : value
    );
  }

  function normalized(value) {
    return text(value)
      .trim()
      .toLowerCase();
  }

  function toast(message) {
    const node =
      byId("toast");

    if (!node) {
      return;
    }

    node.textContent =
      message;

    node.classList.add(
      "show"
    );

    window.clearTimeout(
      toast.timer
    );

    toast.timer =
      window.setTimeout(
        () => {
          node.classList.remove(
            "show"
          );
        },
        1800
      );
  }

  function clickRefresh() {
    const button =
      byId("refresh");

    if (!button) {
      return;
    }

    runtime.lastRefresh =
      Date.now();

    button.click();
  }

  function markRefresh() {
    runtime.lastRefresh =
      Date.now();

    updateFreshness();
  }

  function updateFreshness() {
    const sync =
      byId("syncState");

    if (!sync) {
      return;
    }

    const age =
      Math.floor(
        (
          Date.now() -
          runtime.lastRefresh
        ) / 1000
      );

    sync.dataset.age =
      String(age);

    if (
      age >
      runtime.settings
        .refreshSeconds * 3
    ) {
      sync.classList.add(
        "augment-stale"
      );

      sync.title =
        `projection may be stale · ${age}s`;
    } else {
      sync.classList.remove(
        "augment-stale"
      );

      sync.title =
        `projection age · ${age}s`;
    }
  }

  function installFreshness() {
    window.clearInterval(
      runtime.staleTimer
    );

    runtime.staleTimer =
      window.setInterval(
        updateFreshness,
        1000
      );

    const refresh =
      byId("refresh");

    if (refresh) {
      refresh.addEventListener(
        "click",
        markRefresh
      );
    }
  }

  function installAutoRefresh() {
    window.clearInterval(
      runtime.timer
    );

    if (
      !runtime.settings
        .autoRefresh
    ) {
      return;
    }

    runtime.timer =
      window.setInterval(
        () => {
          if (
            document.hidden ||
            document.querySelector(
              "dialog[open]"
            ) ||
            !byId("inspector")
              ?.classList
              .contains("hidden")
          ) {
            return;
          }

          clickRefresh();
        },
        Math.max(
          5,
          Number(
            runtime.settings
              .refreshSeconds
          ) || 10
        ) * 1000
      );
  }

  function setDensity(
    density
  ) {
    const valid =
      density === "dense"
        ? "dense"
        : "comfortable";

    runtime.settings.density =
      valid;

    document.documentElement
      .dataset
      .density =
      valid;

    saveSettings();

    updateUtilityButtons();
  }

  function toggleDensity() {
    setDensity(
      runtime.settings
        .density === "dense"
        ? "comfortable"
        : "dense"
    );

    toast(
      runtime.settings
        .density === "dense"
        ? "dense projection"
        : "comfortable projection"
    );
  }

  function setFocusMode(
    enabled
  ) {
    runtime.settings.focusMode =
      Boolean(enabled);

    document.body.classList
      .toggle(
        "augment-focus-mode",
        runtime.settings
          .focusMode
      );

    saveSettings();

    updateUtilityButtons();
  }

  function toggleFocusMode() {
    setFocusMode(
      !runtime.settings
        .focusMode
    );

    toast(
      runtime.settings
        .focusMode
        ? "focus mode"
        : "full command surface"
    );
  }

  function visibleTaskNodes() {
    return all(
      [
        ".work-row",
        ".focus-card",
        ".matrix-card",
        ".signal-card",
        ".history-event",
        ".topology-node",
      ].join(",")
    );
  }

  function applyLocalSearch(
    value
  ) {
    const query =
      normalized(value);

    runtime.settings.query =
      value;

    saveSettings();

    visibleTaskNodes()
      .forEach(
        (node) => {
          const haystack =
            normalized(
              node.textContent
            );

          const visible =
            !query ||
            haystack.includes(
              query
            );

          node.classList.toggle(
            "augment-filtered",
            !visible
          );
        }
      );

    updateSearchCount();
  }

  function updateSearchCount() {
    const search =
      byId("search");

    if (
      !search ||
      !normalized(
        search.value
      )
    ) {
      search?.removeAttribute(
        "data-visible"
      );

      return;
    }

    const nodes =
      visibleTaskNodes();

    const visible =
      nodes.filter(
        (node) =>
          !node.classList
            .contains(
              "augment-filtered"
            )
      ).length;

    search.dataset.visible =
      `${visible}/${nodes.length}`;
  }

  function installSearch() {
    const search =
      byId("search");

    if (!search) {
      return;
    }

    if (
      runtime.settings.query &&
      !search.value
    ) {
      search.value =
        runtime.settings.query;
    }

    search.addEventListener(
      "input",
      () => {
        applyLocalSearch(
          search.value
        );
      }
    );

    applyLocalSearch(
      search.value
    );
  }

  function activeViewName() {
    const active =
      document.querySelector(
        ".command-nav-item.active"
      );

    return (
      active?.dataset.view ||
      runtime.settings.view ||
      "cockpit"
    );
  }

  function rememberView() {
    all(
      ".command-nav-item[data-view]"
    ).forEach(
      (button) => {
        button.addEventListener(
          "click",
          () => {
            runtime.settings.view =
              button.dataset.view ||
              "cockpit";

            saveSettings();
          }
        );
      }
    );
  }

  function restoreView() {
    const view =
      runtime.settings.view;

    if (
      !view ||
      view === "cockpit"
    ) {
      return;
    }

    const button =
      document.querySelector(
        `.command-nav-item[data-view="${CSS.escape(
          view
        )}"]`
      );

    if (button) {
      button.click();
    }
  }

  function openView(view) {
    const button =
      document.querySelector(
        `.command-nav-item[data-view="${CSS.escape(
          view
        )}"]`
      );

    if (button) {
      button.click();

      runtime.settings.view =
        view;

      saveSettings();
    }
  }

  function copyText(
    value,
    label
  ) {
    const payload =
      text(value).trim();

    if (!payload) {
      toast(
        "nothing to copy"
      );

      return;
    }

    navigator.clipboard
      ?.writeText(payload)
      .then(
        () => {
          toast(
            label ||
            "copied"
          );
        },
        () => {
          toast(
            "clipboard unavailable"
          );
        }
      );
  }

  function inspectorPacket() {
    const inspector =
      byId("inspector");

    if (
      !inspector ||
      inspector.classList
        .contains("hidden")
    ) {
      return "";
    }

    const id =
      byId("inspectorId")
        ?.textContent
        ?.trim() || "";

    const title =
      byId("inspectorTitle")
        ?.textContent
        ?.trim() || "";

    const body =
      byId("inspectorBody")
        ?.innerText
        ?.trim() || "";

    return [
      id,
      title,
      body,
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  function copyInspector() {
    copyText(
      inspectorPacket(),
      "task context copied"
    );
  }

  function copyVisible() {
    const view =
      document.querySelector(
        ".command-view.active"
      );

    copyText(
      view?.innerText || "",
      `${activeViewName()} copied`
    );
  }

  function firstVisibleTask() {
    return visibleTaskNodes()
      .find(
        (node) =>
          !node.classList
            .contains(
              "augment-filtered"
            )
      );
  }

  function openFirstVisible() {
    const node =
      firstVisibleTask();

    if (!node) {
      toast(
        "no visible task"
      );

      return;
    }

    node.scrollIntoView({
      behavior:
        window.matchMedia(
          "(prefers-reduced-motion: reduce)"
        ).matches
          ? "auto"
          : "smooth",
      block: "center",
    });

    node.click();
  }

  function installInspectorMemory() {
    const inspector =
      byId("inspector");

    if (!inspector) {
      return;
    }

    runtime.observer =
      new MutationObserver(
        () => {
          if (
            inspector.classList
              .contains("hidden")
          ) {
            return;
          }

          const id =
            byId("inspectorId")
              ?.textContent
              ?.trim();

          if (id) {
            runtime.settings
              .lastTask = id;

            saveSettings();
          }
        }
      );

    runtime.observer.observe(
      inspector,
      {
        attributes: true,
        subtree: true,
        childList: true,
        characterData: true,
      }
    );
  }

  function createUtilityBar() {
    if (
      byId(
        "augmentUtilityBar"
      )
    ) {
      return;
    }

    const bar =
      document.createElement(
        "div"
      );

    bar.id =
      "augmentUtilityBar";

    bar.className =
      "augment-utility-bar";

    bar.innerHTML = `
      <button
        type="button"
        data-augment="focus"
        title="Toggle protected focus mode">
        ◎ focus
      </button>

      <button
        type="button"
        data-augment="density"
        title="Toggle display density">
        ▦ density
      </button>

      <button
        type="button"
        data-augment="copy"
        title="Copy current projection">
        ⧉ copy
      </button>

      <button
        type="button"
        data-augment="refresh"
        title="Refresh projection">
        ↻ sync
      </button>
    `;

    document.body.appendChild(
      bar
    );

    bar.addEventListener(
      "click",
      (event) => {
        const button =
          event.target.closest(
            "[data-augment]"
          );

        if (!button) {
          return;
        }

        const action =
          button.dataset.augment;

        if (
          action === "focus"
        ) {
          toggleFocusMode();
        }

        if (
          action === "density"
        ) {
          toggleDensity();
        }

        if (
          action === "copy"
        ) {
          const inspector =
            byId("inspector");

          if (
            inspector &&
            !inspector.classList
              .contains("hidden")
          ) {
            copyInspector();
          } else {
            copyVisible();
          }
        }

        if (
          action === "refresh"
        ) {
          clickRefresh();
        }
      }
    );

    updateUtilityButtons();
  }

  function updateUtilityButtons() {
    const focus =
      document.querySelector(
        '[data-augment="focus"]'
      );

    const density =
      document.querySelector(
        '[data-augment="density"]'
      );

    if (focus) {
      focus.classList.toggle(
        "active",
        runtime.settings
          .focusMode
      );
    }

    if (density) {
      density.textContent =
        runtime.settings
          .density === "dense"
          ? "▦ dense"
          : "▦ comfort";
    }
  }

  function commandRows() {
    return [
      {
        label:
          "Open cockpit",
        hint:
          "operational synthesis",
        run:
          () =>
            openView(
              "cockpit"
            ),
      },
      {
        label:
          "Open focus queue",
        hint:
          "deterministic executable work",
        run:
          () =>
            openView(
              "focus"
            ),
      },
      {
        label:
          "Open work matrix",
        hint:
          "portfolio projection",
        run:
          () =>
            openView(
              "matrix"
            ),
      },
      {
        label:
          "Open topology",
        hint:
          "dependency geometry",
        run:
          () =>
            openView(
              "topology"
            ),
      },
      {
        label:
          "Open signals",
        hint:
          "derived intelligence",
        run:
          () =>
            openView(
              "signals"
            ),
      },
      {
        label:
          "Open history",
        hint:
          "immutable event chain",
        run:
          () =>
            openView(
              "history"
            ),
      },
      {
        label:
          "Toggle focus mode",
        hint:
          "hide peripheral chrome",
        run:
          toggleFocusMode,
      },
      {
        label:
          "Toggle density",
        hint:
          "comfortable or dense",
        run:
          toggleDensity,
      },
      {
        label:
          "Refresh projection",
        hint:
          "request current Niche state",
        run:
          clickRefresh,
      },
      {
        label:
          "Open first visible task",
        hint:
          "current filtered projection",
        run:
          openFirstVisible,
      },
      {
        label:
          "Copy current view",
        hint:
          "bounded operator context",
        run:
          copyVisible,
      },
    ];
  }

  function installAugmentPalette() {
    if (
      byId(
        "augmentPalette"
      )
    ) {
      return;
    }

    const dialog =
      document.createElement(
        "dialog"
      );

    dialog.id =
      "augmentPalette";

    dialog.className =
      "augment-palette";

    dialog.innerHTML = `
      <div
        class="augment-palette-search">

        <span>⌘</span>

        <input
          id="augmentPaletteInput"
          autocomplete="off"
          spellcheck="false"
          placeholder="Command Niche…">

        <kbd>esc</kbd>
      </div>

      <div
        id="augmentPaletteResults"
        class="augment-palette-results">
      </div>
    `;

    document.body.appendChild(
      dialog
    );

    const input =
      byId(
        "augmentPaletteInput"
      );

    const results =
      byId(
        "augmentPaletteResults"
      );

    function render() {
      const query =
        normalized(
          input.value
        );

      const commands =
        commandRows()
          .filter(
            (command) =>
              !query ||
              normalized(
                [
                  command.label,
                  command.hint,
                ].join(" ")
              ).includes(
                query
              )
          );

      results.replaceChildren();

      commands.forEach(
        (command) => {
          const button =
            document.createElement(
              "button"
            );

          button.type =
            "button";

          button.className =
            "augment-palette-row";

          const strong =
            document.createElement(
              "strong"
            );

          strong.textContent =
            command.label;

          const small =
            document.createElement(
              "small"
            );

          small.textContent =
            command.hint;

          button.append(
            strong,
            small
          );

          button.addEventListener(
            "click",
            () => {
              dialog.close();
              command.run();
            }
          );

          results.appendChild(
            button
          );
        }
      );
    }

    input.addEventListener(
      "input",
      render
    );

    dialog.addEventListener(
      "close",
      () => {
        input.value = "";
      }
    );

    dialog.openAugment =
      () => {
        render();
        dialog.showModal();

        window.setTimeout(
          () => {
            input.focus();
          },
          0
        );
      };
  }

  function openAugmentPalette() {
    const dialog =
      byId("augmentPalette");

    if (
      dialog &&
      !dialog.open
    ) {
      dialog.openAugment?.();
    }
  }

  function installKeyboard() {
    document.addEventListener(
      "keydown",
      (event) => {
        const target =
          event.target;

        const editing =
          target instanceof
            HTMLInputElement ||
          target instanceof
            HTMLTextAreaElement ||
          target instanceof
            HTMLSelectElement ||
          target?.isContentEditable;

        if (
          (
            event.ctrlKey ||
            event.metaKey
          ) &&
          event.key
            .toLowerCase() ===
            "k"
        ) {
          event.preventDefault();
          openAugmentPalette();
          return;
        }

        if (
          editing
        ) {
          return;
        }

        if (
          event.key === "/"
        ) {
          event.preventDefault();

          byId("search")
            ?.focus();

          return;
        }

        if (
          event.key
            .toLowerCase() ===
          "g"
        ) {
          toggleDensity();
          return;
        }

        if (
          event.key
            .toLowerCase() ===
          "f"
        ) {
          toggleFocusMode();
          return;
        }

        if (
          event.key
            .toLowerCase() ===
          "r"
        ) {
          clickRefresh();
          return;
        }

        if (
          event.key
            .toLowerCase() ===
          "n"
        ) {
          openFirstVisible();
          return;
        }

        const viewKeys = {
          "1": "cockpit",
          "2": "focus",
          "3": "matrix",
          "4": "topology",
          "5": "signals",
          "6": "history",
        };

        if (
          viewKeys[
            event.key
          ]
        ) {
          openView(
            viewKeys[
              event.key
            ]
          );
        }
      }
    );
  }

  function installVisibility() {
    document.addEventListener(
      "visibilitychange",
      () => {
        if (
          !document.hidden &&
          runtime.settings
            .autoRefresh
        ) {
          const age =
            Date.now() -
            runtime.lastRefresh;

          if (
            age >
            runtime.settings
              .refreshSeconds *
              2000
          ) {
            clickRefresh();
          }
        }
      }
    );
  }

  function installMutationSearch() {
    const main =
      document.querySelector(
        ".command-main"
      );

    if (!main) {
      return;
    }

    const observer =
      new MutationObserver(
        () => {
          const search =
            byId("search");

          if (
            search &&
            normalized(
              search.value
            )
          ) {
            applyLocalSearch(
              search.value
            );
          }
        }
      );

    observer.observe(
      main,
      {
        childList: true,
        subtree: true,
      }
    );
  }

  function boot() {
    readSettings();

    document.documentElement
      .dataset
      .density =
      runtime.settings
        .density;

    document.body.classList
      .toggle(
        "augment-focus-mode",
        runtime.settings
          .focusMode
      );

    createUtilityBar();
    installAugmentPalette();
    installSearch();
    installKeyboard();
    installVisibility();
    installFreshness();
    installAutoRefresh();
    installInspectorMemory();
    installMutationSearch();
    rememberView();

    window.setTimeout(
      restoreView,
      120
    );
  }

  if (
    document.readyState ===
    "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      boot,
      {
        once: true,
      }
    );
  } else {
    boot();
  }
})();
