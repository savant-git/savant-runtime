"use strict";

/*
 * niche command session intelligence
 *
 * local operator continuity only.
 * no task authority.
 * no server mutation.
 * no canon mutation.
 */

(() => {
  const key =
    "savant:niche:command:session:v1";

  const maximumRecent = 12;
  const maximumPinned = 12;

  const state = {
    recent: [],
    pinned: [],
    observer: null,
    selectedId: "",
  };

  const byId = (id) =>
    document.getElementById(id);

  const clean = (value) =>
    String(
      value == null
        ? ""
        : value
    ).trim();

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
        () =>
          node.classList.remove(
            "show"
          ),
        1600
      );
  }

  function load() {
    try {
      const payload =
        JSON.parse(
          localStorage.getItem(
            key
          ) || "{}"
        );

      state.recent =
        Array.isArray(
          payload.recent
        )
          ? payload.recent
          : [];

      state.pinned =
        Array.isArray(
          payload.pinned
        )
          ? payload.pinned
          : [];
    } catch {
      state.recent = [];
      state.pinned = [];
    }
  }

  function save() {
    try {
      localStorage.setItem(
        key,
        JSON.stringify({
          recent:
            state.recent.slice(
              0,
              maximumRecent
            ),
          pinned:
            state.pinned.slice(
              0,
              maximumPinned
            ),
        })
      );
    } catch {
      return;
    }
  }

  function currentTask() {
    const inspector =
      byId("inspector");

    if (
      !inspector ||
      inspector.classList
        .contains("hidden")
    ) {
      return null;
    }

    const id =
      clean(
        byId("inspectorId")
          ?.textContent
      );

    if (!id) {
      return null;
    }

    return {
      id,
      title:
        clean(
          byId(
            "inspectorTitle"
          )?.textContent
        ) || id,
      seenAt:
        new Date()
          .toISOString(),
    };
  }

  function remember(task) {
    if (!task?.id) {
      return;
    }

    state.recent =
      [
        task,
        ...state.recent.filter(
          (entry) =>
            entry.id !==
            task.id
        ),
      ].slice(
        0,
        maximumRecent
      );

    save();
    render();
  }

  function isPinned(id) {
    return state.pinned
      .some(
        (entry) =>
          entry.id === id
      );
  }

  function togglePin(task) {
    if (!task?.id) {
      return;
    }

    if (
      isPinned(
        task.id
      )
    ) {
      state.pinned =
        state.pinned.filter(
          (entry) =>
            entry.id !==
            task.id
        );

      toast(
        "task unpinned"
      );
    } else {
      state.pinned =
        [
          {
            id: task.id,
            title:
              task.title ||
              task.id,
            pinnedAt:
              new Date()
                .toISOString(),
          },
          ...state.pinned,
        ].slice(
          0,
          maximumPinned
        );

      toast(
        "task pinned"
      );
    }

    save();
    render();
  }

  function findTaskNode(
    id
  ) {
    const candidates =
      Array.from(
        document.querySelectorAll(
          [
            ".work-row",
            ".focus-card",
            ".matrix-card",
            ".signal-card",
          ].join(",")
        )
      );

    return candidates.find(
      (node) => {
        const explicit =
          clean(
            node.dataset
              .taskId ||
            node.dataset.id ||
            node.getAttribute(
              "data-task"
            )
          );

        if (
          explicit === id
        ) {
          return true;
        }

        return clean(
          node.textContent
        ).includes(id);
      }
    );
  }

  function openTask(id) {
    const node =
      findTaskNode(id);

    if (!node) {
      const search =
        byId("search");

      if (search) {
        search.value = id;

        search.dispatchEvent(
          new Event(
            "input",
            {
              bubbles: true,
            }
          )
        );
      }

      window.setTimeout(
        () => {
          const resolved =
            findTaskNode(id);

          if (resolved) {
            resolved.click();

            resolved.scrollIntoView({
              block: "center",
              behavior:
                window.matchMedia(
                  "(prefers-reduced-motion: reduce)"
                ).matches
                  ? "auto"
                  : "smooth",
            });
          } else {
            toast(
              "task not visible"
            );
          }
        },
        60
      );

      return;
    }

    node.click();

    node.scrollIntoView({
      block: "center",
      behavior:
        window.matchMedia(
          "(prefers-reduced-motion: reduce)"
        ).matches
          ? "auto"
          : "smooth",
    });
  }

  function createSurface() {
    if (
      byId(
        "sessionIntelligence"
      )
    ) {
      return;
    }

    const section =
      document.createElement(
        "section"
      );

    section.id =
      "sessionIntelligence";

    section.className =
      "sidebar-block session-intelligence";

    section.innerHTML = `
      <div class="sidebar-heading session-heading">
        <span>continuity</span>

        <button
          id="sessionClear"
          type="button"
          title="Clear local recent-task history">
          clear
        </button>
      </div>

      <div class="session-tabs">
        <button
          class="active"
          data-session-tab="pinned"
          type="button">
          pinned
        </button>

        <button
          data-session-tab="recent"
          type="button">
          recent
        </button>
      </div>

      <div
        id="sessionList"
        class="session-list"
        data-session-view="pinned">
      </div>
    `;

    const health =
      byId(
        "engineHealth"
      );

    if (health) {
      health.before(
        section
      );
    } else {
      document.querySelector(
        ".command-sidebar"
      )?.appendChild(
        section
      );
    }

    section.addEventListener(
      "click",
      (event) => {
        const tab =
          event.target.closest(
            "[data-session-tab]"
          );

        if (tab) {
          section
            .querySelectorAll(
              "[data-session-tab]"
            )
            .forEach(
              (button) =>
                button.classList
                  .toggle(
                    "active",
                    button ===
                      tab
                  )
            );

          const list =
            byId(
              "sessionList"
            );

          if (list) {
            list.dataset
              .sessionView =
              tab.dataset
                .sessionTab;

            render();
          }

          return;
        }

        const task =
          event.target.closest(
            "[data-session-task]"
          );

        if (task) {
          openTask(
            task.dataset
              .sessionTask
          );
        }
      }
    );

    byId(
      "sessionClear"
    )?.addEventListener(
      "click",
      () => {
        state.recent = [];
        save();
        render();

        toast(
          "recent history cleared"
        );
      }
    );
  }

  function sessionEntry(
    entry,
    pinned
  ) {
    const button =
      document.createElement(
        "button"
      );

    button.type =
      "button";

    button.className =
      "session-entry";

    button.dataset
      .sessionTask =
      entry.id;

    const marker =
      document.createElement(
        "span"
      );

    marker.className =
      "session-marker";

    marker.textContent =
      pinned
        ? "◆"
        : "·";

    const body =
      document.createElement(
        "span"
      );

    const title =
      document.createElement(
        "strong"
      );

    title.textContent =
      entry.title ||
      entry.id;

    const id =
      document.createElement(
        "small"
      );

    id.textContent =
      entry.id;

    body.append(
      title,
      id
    );

    button.append(
      marker,
      body
    );

    return button;
  }

  function render() {
    createSurface();

    const list =
      byId(
        "sessionList"
      );

    if (!list) {
      return;
    }

    const pinned =
      list.dataset
        .sessionView !==
      "recent";

    const source =
      pinned
        ? state.pinned
        : state.recent;

    list.replaceChildren();

    if (!source.length) {
      const empty =
        document.createElement(
          "div"
        );

      empty.className =
        "session-empty";

      empty.textContent =
        pinned
          ? "no pinned work"
          : "no recent work";

      list.appendChild(
        empty
      );

      return;
    }

    source.forEach(
      (entry) => {
        list.appendChild(
          sessionEntry(
            entry,
            pinned
          )
        );
      }
    );
  }

  function installInspectorPin() {
    const inspector =
      byId("inspector");

    const header =
      inspector?.querySelector(
        ".inspector-header"
      );

    if (
      !header ||
      byId(
        "sessionPinTask"
      )
    ) {
      return;
    }

    const button =
      document.createElement(
        "button"
      );

    button.id =
      "sessionPinTask";

    button.type =
      "button";

    button.className =
      "session-pin";

    button.textContent =
      "◇";

    button.title =
      "Pin task locally";

    header.prepend(
      button
    );

    button.addEventListener(
      "click",
      () => {
        const task =
          currentTask();

        togglePin(task);
        updatePin();
      }
    );
  }

  function updatePin() {
    const button =
      byId(
        "sessionPinTask"
      );

    const task =
      currentTask();

    if (
      !button ||
      !task
    ) {
      return;
    }

    const pinned =
      isPinned(
        task.id
      );

    button.textContent =
      pinned
        ? "◆"
        : "◇";

    button.classList.toggle(
      "active",
      pinned
    );

    button.title =
      pinned
        ? "Unpin task locally"
        : "Pin task locally";
  }

  function syncInspector() {
    installInspectorPin();

    const task =
      currentTask();

    if (!task) {
      state.selectedId =
        "";

      return;
    }

    if (
      task.id !==
      state.selectedId
    ) {
      state.selectedId =
        task.id;

      remember(task);
    }

    updatePin();
  }

  function observeInspector() {
    const inspector =
      byId("inspector");

    if (!inspector) {
      return;
    }

    state.observer =
      new MutationObserver(
        () => {
          window.clearTimeout(
            syncInspector.timer
          );

          syncInspector.timer =
            window.setTimeout(
              syncInspector,
              30
            );
        }
      );

    state.observer.observe(
      inspector,
      {
        attributes: true,
        childList: true,
        subtree: true,
        characterData: true,
      }
    );
  }

  function installKeyboard() {
    document.addEventListener(
      "keydown",
      (event) => {
        const editing =
          event.target instanceof
            HTMLInputElement ||
          event.target instanceof
            HTMLTextAreaElement ||
          event.target instanceof
            HTMLSelectElement ||
          event.target
            ?.isContentEditable;

        if (editing) {
          return;
        }

        if (
          event.key
            .toLowerCase() ===
            "p" &&
          currentTask()
        ) {
          event.preventDefault();

          togglePin(
            currentTask()
          );

          updatePin();
        }
      }
    );
  }

  function boot() {
    load();
    createSurface();
    render();
    installInspectorPin();
    observeInspector();
    installKeyboard();

    window.setTimeout(
      syncInspector,
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
