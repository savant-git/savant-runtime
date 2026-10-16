"use strict";

/*
 * niche command intelligence
 *
 * deterministic projection intelligence over the existing
 * rendered task surface. this layer owns no task authority
 * and performs no durable task mutation.
 */

(() => {
  const terminal =
    new Set([
      "completed",
      "rejected",
      "superseded",
    ]);

  const state = {
    selected: new Set(),
    mutationObserver: null,
    renderTimer: null,
  };

  const byId = (id) =>
    document.getElementById(id);

  const all = (selector) =>
    Array.from(
      document.querySelectorAll(
        selector
      )
    );

  const clean = (value) =>
    String(
      value == null
        ? ""
        : value
    ).trim();

  const lower = (value) =>
    clean(value).toLowerCase();

  function taskNodes() {
    return all(
      [
        ".work-row",
        ".focus-card",
        ".matrix-card",
      ].join(",")
    );
  }

  function deriveTask(node) {
    const text =
      clean(node.innerText);

    const id =
      clean(
        node.dataset.taskId ||
        node.dataset.id ||
        node.getAttribute(
          "data-task"
        )
      ) ||
      (
        text.match(
          /completion:[a-z0-9:_-]+/i
        ) || []
      )[0] ||
      "";

    const status =
      allPills(node)
        .map(lower)
        .find(
          (value) =>
            [
              "proposed",
              "accepted",
              "ready",
              "leased",
              "active",
              "blocked",
              "deferred",
              "completed",
              "rejected",
              "superseded",
            ].includes(value)
        ) || "";

    const priority =
      allPills(node)
        .map(lower)
        .find(
          (value) =>
            [
              "critical",
              "high",
              "normal",
              "low",
              "deferred",
            ].includes(value)
        ) || "";

    const title =
      clean(
        node.querySelector(
          "h2,strong"
        )?.textContent
      );

    return {
      node,
      id,
      title,
      status,
      priority,
      text,
    };
  }

  function allPills(node) {
    return Array.from(
      node.querySelectorAll(
        ".pill"
      )
    ).map(
      (pill) =>
        pill.textContent
    );
  }

  function uniqueTasks() {
    const seen =
      new Set();

    const result = [];

    taskNodes()
      .map(deriveTask)
      .forEach(
        (task) => {
          const key =
            task.id ||
            `${task.title}|${task.text}`;

          if (
            !key ||
            seen.has(key)
          ) {
            return;
          }

          seen.add(key);
          result.push(task);
        }
      );

    return result;
  }

  function score(task) {
    const priority = {
      critical: 500,
      high: 300,
      normal: 150,
      low: 50,
      deferred: 0,
    };

    const status = {
      ready: 220,
      active: 180,
      leased: 160,
      accepted: 100,
      proposed: 40,
      blocked: -80,
      deferred: -200,
      completed: -500,
      rejected: -600,
      superseded: -600,
    };

    return (
      (
        priority[
          task.priority
        ] || 0
      ) +
      (
        status[
          task.status
        ] || 0
      )
    );
  }

  function reason(task) {
    if (
      terminal.has(
        task.status
      )
    ) {
      return "terminal";
    }

    if (
      task.status ===
      "blocked"
    ) {
      return "requires intervention";
    }

    if (
      task.status ===
      "ready"
    ) {
      return "executable now";
    }

    if (
      task.status ===
      "active" ||
      task.status ===
      "leased"
    ) {
      return "execution in progress";
    }

    if (
      task.priority ===
      "critical"
    ) {
      return "critical authority priority";
    }

    return "non-terminal work";
  }

  function createLens() {
    if (
      byId(
        "intelligenceLens"
      )
    ) {
      return;
    }

    const section =
      document.createElement(
        "section"
      );

    section.id =
      "intelligenceLens";

    section.className =
      "intelligence-lens";

    section.innerHTML = `
      <header class="intelligence-heading">
        <div>
          <span class="eyebrow">
            projection intelligence
          </span>
          <h2>
            decision lens
          </h2>
        </div>

        <button
          id="intelligenceRefresh"
          type="button">
          recalculate
        </button>
      </header>

      <div
        id="intelligenceMetrics"
        class="intelligence-metrics">
      </div>

      <div class="intelligence-grid">
        <section>
          <header>
            <strong>attention frontier</strong>
            <span>projected</span>
          </header>
          <div id="attentionFrontier"></div>
        </section>

        <section>
          <header>
            <strong>state pressure</strong>
            <span>projected</span>
          </header>
          <div id="statePressure"></div>
        </section>

        <section>
          <header>
            <strong>priority pressure</strong>
            <span>projected</span>
          </header>
          <div id="priorityPressure"></div>
        </section>
      </div>
    `;

    const cockpit =
      byId("cockpitView");

    if (cockpit) {
      cockpit.appendChild(
        section
      );
    }

    byId(
      "intelligenceRefresh"
    )?.addEventListener(
      "click",
      render
    );
  }

  function metric(
    label,
    value,
    note
  ) {
    const node =
      document.createElement(
        "div"
      );

    node.className =
      "intelligence-metric";

    const small =
      document.createElement(
        "small"
      );

    small.textContent =
      label;

    const strong =
      document.createElement(
        "strong"
      );

    strong.textContent =
      String(value);

    const span =
      document.createElement(
        "span"
      );

    span.textContent =
      note;

    node.append(
      small,
      strong,
      span
    );

    return node;
  }

  function renderMetrics(
    tasks
  ) {
    const root =
      byId(
        "intelligenceMetrics"
      );

    if (!root) {
      return;
    }

    const nonterminal =
      tasks.filter(
        (task) =>
          !terminal.has(
            task.status
          )
      );

    const executable =
      tasks.filter(
        (task) =>
          task.status ===
          "ready"
      );

    const blocked =
      tasks.filter(
        (task) =>
          task.status ===
          "blocked"
      );

    const critical =
      nonterminal.filter(
        (task) =>
          task.priority ===
          "critical"
      );

    const active =
      tasks.filter(
        (task) =>
          task.status ===
            "active" ||
          task.status ===
            "leased"
      );

    root.replaceChildren(
      metric(
        "visible",
        tasks.length,
        "unique projected work"
      ),
      metric(
        "executable",
        executable.length,
        "ready now"
      ),
      metric(
        "critical",
        critical.length,
        "non-terminal"
      ),
      metric(
        "blocked",
        blocked.length,
        "intervention"
      ),
      metric(
        "in flight",
        active.length,
        "active or leased"
      )
    );
  }

  function taskButton(
    task,
    index
  ) {
    const button =
      document.createElement(
        "button"
      );

    button.type =
      "button";

    button.className =
      "intelligence-task";

    const rank =
      document.createElement(
        "b"
      );

    rank.textContent =
      String(
        index + 1
      );

    const body =
      document.createElement(
        "span"
      );

    const title =
      document.createElement(
        "strong"
      );

    title.textContent =
      task.title ||
      task.id ||
      "task";

    const why =
      document.createElement(
        "small"
      );

    why.textContent =
      [
        task.priority ||
          "priority unknown",
        task.status ||
          "state unknown",
        reason(task),
      ].join(" · ");

    body.append(
      title,
      why
    );

    button.append(
      rank,
      body
    );

    button.addEventListener(
      "click",
      () => {
        task.node
          .scrollIntoView({
            block: "center",
            behavior:
              window.matchMedia(
                "(prefers-reduced-motion: reduce)"
              ).matches
                ? "auto"
                : "smooth",
          });

        task.node.click();
      }
    );

    return button;
  }

  function renderFrontier(
    tasks
  ) {
    const root =
      byId(
        "attentionFrontier"
      );

    if (!root) {
      return;
    }

    const ranked =
      tasks
        .filter(
          (task) =>
            !terminal.has(
              task.status
            )
        )
        .sort(
          (a, b) =>
            score(b) -
              score(a) ||
            a.title.localeCompare(
              b.title
            )
        )
        .slice(
          0,
          8
        );

    root.replaceChildren();

    if (!ranked.length) {
      root.textContent =
        "no projected work";
      return;
    }

    ranked.forEach(
      (task, index) => {
        root.appendChild(
          taskButton(
            task,
            index
          )
        );
      }
    );
  }

  function pressureRows(
    root,
    entries,
    total
  ) {
    root.replaceChildren();

    entries.forEach(
      ([label, count]) => {
        const row =
          document.createElement(
            "div"
          );

        row.className =
          "pressure-row";

        const header =
          document.createElement(
            "header"
          );

        const name =
          document.createElement(
            "span"
          );

        name.textContent =
          label;

        const value =
          document.createElement(
            "strong"
          );

        value.textContent =
          String(count);

        header.append(
          name,
          value
        );

        const track =
          document.createElement(
            "div"
          );

        track.className =
          "pressure-track";

        const fill =
          document.createElement(
            "div"
          );

        fill.className =
          "pressure-fill";

        fill.style.width =
          `${
            total
              ? Math.max(
                  3,
                  (
                    count /
                    total
                  ) * 100
                )
              : 0
          }%`;

        track.appendChild(
          fill
        );

        row.append(
          header,
          track
        );

        root.appendChild(
          row
        );
      }
    );
  }

  function counts(
    tasks,
    field,
    order
  ) {
    const map =
      new Map();

    tasks.forEach(
      (task) => {
        const value =
          task[field] ||
          "unknown";

        map.set(
          value,
          (
            map.get(value) ||
            0
          ) + 1
        );
      }
    );

    return Array.from(
      map.entries()
    ).sort(
      (a, b) => {
        const ai =
          order.indexOf(
            a[0]
          );

        const bi =
          order.indexOf(
            b[0]
          );

        if (
          ai !== -1 ||
          bi !== -1
        ) {
          return (
            (
              ai === -1
                ? 999
                : ai
            ) -
            (
              bi === -1
                ? 999
                : bi
            )
          );
        }

        return (
          b[1] -
          a[1]
        );
      }
    );
  }

  function renderPressure(
    tasks
  ) {
    const nonterminal =
      tasks.filter(
        (task) =>
          !terminal.has(
            task.status
          )
      );

    const status =
      byId(
        "statePressure"
      );

    const priority =
      byId(
        "priorityPressure"
      );

    if (status) {
      pressureRows(
        status,
        counts(
          nonterminal,
          "status",
          [
            "ready",
            "active",
            "leased",
            "blocked",
            "accepted",
            "proposed",
            "deferred",
            "unknown",
          ]
        ),
        nonterminal.length
      );
    }

    if (priority) {
      pressureRows(
        priority,
        counts(
          nonterminal,
          "priority",
          [
            "critical",
            "high",
            "normal",
            "low",
            "deferred",
            "unknown",
          ]
        ),
        nonterminal.length
      );
    }
  }

  function installCompareTray() {
    if (
      byId(
        "compareTray"
      )
    ) {
      return;
    }

    const tray =
      document.createElement(
        "aside"
      );

    tray.id =
      "compareTray";

    tray.className =
      "compare-tray hidden";

    tray.innerHTML = `
      <header>
        <strong>
          compare projection
        </strong>

        <button
          id="compareClear"
          type="button">
          clear
        </button>
      </header>

      <div id="compareBody"></div>
    `;

    document.body.appendChild(
      tray
    );

    byId(
      "compareClear"
    )?.addEventListener(
      "click",
      () => {
        state.selected.clear();
        renderCompare();
      }
    );
  }

  function compareKey(task) {
    return (
      task.id ||
      task.title ||
      task.text
    );
  }

  function toggleCompare(
    task
  ) {
    const key =
      compareKey(task);

    if (
      state.selected.has(key)
    ) {
      state.selected.delete(
        key
      );
    } else {
      if (
        state.selected.size >=
        2
      ) {
        const first =
          state.selected
            .values()
            .next()
            .value;

        state.selected.delete(
          first
        );
      }

      state.selected.add(
        key
      );
    }

    renderCompare();
  }

  function installCompareHooks(
    tasks
  ) {
    tasks.forEach(
      (task) => {
        if (
          task.node.dataset
            .compareHook ===
          "1"
        ) {
          return;
        }

        task.node.dataset
          .compareHook = "1";

        task.node.addEventListener(
          "contextmenu",
          (event) => {
            event.preventDefault();

            toggleCompare(
              deriveTask(
                task.node
              )
            );
          }
        );
      }
    );
  }

  function renderCompare() {
    const tray =
      byId("compareTray");

    const body =
      byId("compareBody");

    if (
      !tray ||
      !body
    ) {
      return;
    }

    const tasks =
      uniqueTasks();

    const selected =
      tasks.filter(
        (task) =>
          state.selected.has(
            compareKey(task)
          )
      );

    tray.classList.toggle(
      "hidden",
      !selected.length
    );

    body.replaceChildren();

    selected.forEach(
      (task) => {
        const card =
          document.createElement(
            "article"
          );

        const title =
          document.createElement(
            "strong"
          );

        title.textContent =
          task.title ||
          task.id ||
          "task";

        const meta =
          document.createElement(
            "span"
          );

        meta.textContent =
          [
            task.priority ||
              "priority unknown",
            task.status ||
              "state unknown",
            `projection score ${score(
              task
            )}`,
          ].join(" · ");

        const why =
          document.createElement(
            "small"
          );

        why.textContent =
          reason(task);

        card.append(
          title,
          meta,
          why
        );

        card.addEventListener(
          "click",
          () =>
            task.node.click()
        );

        body.appendChild(
          card
        );
      }
    );
  }

  function render() {
    createLens();
    installCompareTray();

    const tasks =
      uniqueTasks();

    renderMetrics(
      tasks
    );

    renderFrontier(
      tasks
    );

    renderPressure(
      tasks
    );

    installCompareHooks(
      tasks
    );

    renderCompare();
  }

  function scheduleRender() {
    window.clearTimeout(
      state.renderTimer
    );

    state.renderTimer =
      window.setTimeout(
        render,
        80
      );
  }

  function observe() {
    const main =
      document.querySelector(
        ".command-main"
      );

    if (!main) {
      return;
    }

    state.mutationObserver =
      new MutationObserver(
        scheduleRender
      );

    state.mutationObserver.observe(
      main,
      {
        childList: true,
        subtree: true,
      }
    );
  }

  function boot() {
    render();
    observe();

    byId("refresh")
      ?.addEventListener(
        "click",
        scheduleRender
      );

    document.addEventListener(
      "keydown",
      (event) => {
        if (
          event.key === "c" &&
          !event.ctrlKey &&
          !event.metaKey &&
          !event.altKey &&
          !(
            event.target instanceof
              HTMLInputElement
          ) &&
          !(
            event.target instanceof
              HTMLTextAreaElement
          ) &&
          !(
            event.target instanceof
              HTMLSelectElement
          )
        ) {
          const first =
            uniqueTasks()[0];

          if (first) {
            toggleCompare(
              first
            );
          }
        }
      }
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
