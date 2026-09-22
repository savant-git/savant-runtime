"use strict";

const state = {
  completion: null,
  tasks: [],
  depth: 4,
  q: "",
  status: "",
  priority: "",
  horizon: "",
  system: "",
  workstream: "",
};

const $ = (selector) =>
  document.querySelector(selector);

const $$ = (selector) =>
  [...document.querySelectorAll(selector)];

const esc = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const priorityOrder = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
  deferred: 4,
};

function taskMeta(task) {
  const slots =
    task.extension_slots || {};

  return (
    slots["niche.taskboard"]
    || {}
  );
}

function taskDepth(task) {
  const value =
    Number(
      taskMeta(task).depth
      || 1
    );

  return (
    Number.isFinite(value)
    ? value
    : 1
  );
}

function title(task) {
  return (
    taskMeta(task).title
    || task.purpose
    || task.task_id
  );
}

function system(task) {
  return (
    taskMeta(task).system
    || task.jurisdiction
    || "savant"
  );
}

function workstream(task) {
  return (
    taskMeta(task).workstream
    || system(task)
  );
}

function horizon(task) {
  return (
    taskMeta(task).horizon
    || "backlog"
  );
}

function risk(task) {
  return (
    taskMeta(task).risk
    || "unknown"
  );
}

function parentId(task) {
  return (
    taskMeta(task).parent_id
    || null
  );
}

async function request(path) {
  const response =
    await fetch(
      path,
      {
        cache: "no-store",
      }
    );

  if (!response.ok) {
    throw new Error(
      `${response.status} ${response.statusText}`
    );
  }

  return response.json();
}

async function load() {
  const [
    statePayload,
    healthPayload,
  ] = await Promise.all([
    request("/api/state"),
    request("/api/health"),
  ]);

  state.tasks =
    statePayload.tasks
    || [];

  state.completion = {
    graph:
      statePayload.graph
      || {},
    dashboard:
      statePayload.dashboard
      || {},
    health:
      healthPayload
      || {},
  };

  render();
}

function filtered() {
  const query =
    state.q
      .trim()
      .toLowerCase();

  return state.tasks
    .filter(
      (task) =>
        taskDepth(task)
        <= state.depth
    )
    .filter(
      (task) =>
        !state.status
        || task.status
        === state.status
    )
    .filter(
      (task) =>
        !state.priority
        || task.priority
        === state.priority
    )
    .filter(
      (task) =>
        !state.horizon
        || horizon(task)
        === state.horizon
    )
    .filter(
      (task) =>
        !state.system
        || system(task)
        === state.system
    )
    .filter(
      (task) =>
        !state.workstream
        || workstream(task)
        === state.workstream
    )
    .filter(
      (task) => {
        if (!query) {
          return true;
        }

        const haystack = [
          task.task_id,
          title(task),
          task.purpose,
          task.status,
          task.priority,
          system(task),
          workstream(task),
          horizon(task),
          risk(task),
          ...(task.affected_instances || []),
          ...(task.dependencies || []),
        ]
          .join(" ")
          .toLowerCase();

        return haystack.includes(query);
      }
    )
    .sort(
      (a, b) => {
        const priority =
          (
            priorityOrder[a.priority]
            ?? 9
          )
          -
          (
            priorityOrder[b.priority]
            ?? 9
          );

        if (priority) {
          return priority;
        }

        const depth =
          taskDepth(a)
          - taskDepth(b);

        if (depth) {
          return depth;
        }

        return title(a)
          .localeCompare(
            title(b)
          );
      }
    );
}

function setOptions(
  selector,
  values,
  current
) {
  const select =
    $(selector);

  const first =
    select.options[0]
      .outerHTML;

  select.innerHTML =
    first
    + [...values]
      .sort()
      .map(
        (value) =>
          `<option value="${esc(value)}">`
          + `${esc(value)}`
          + "</option>"
      )
      .join("");

  select.value =
    current || "";
}

function populateFacets() {
  const systems =
    new Set();

  const workstreams =
    new Set();

  state.tasks.forEach(
    (task) => {
      systems.add(
        system(task)
      );

      workstreams.add(
        workstream(task)
      );
    }
  );

  setOptions(
    "#systemFilter",
    systems,
    state.system
  );

  setOptions(
    "#workstreamFilter",
    workstreams,
    state.workstream
  );
}

function metric(
  label,
  value,
  detail
) {
  return `
    <article class="completion-metric">
      <span>${esc(label)}</span>
      <strong>${esc(value)}</strong>
      <small>${esc(detail)}</small>
    </article>
  `;
}

function renderMetrics(tasks) {
  const active =
    tasks.filter(
      (task) =>
        task.status === "active"
    ).length;

  const ready =
    tasks.filter(
      (task) =>
        task.status === "ready"
        || task.status === "accepted"
    ).length;

  const blocked =
    tasks.filter(
      (task) =>
        task.status === "blocked"
        || (
          task.blockers
          && task.blockers.length
        )
    ).length;

  const completed =
    tasks.filter(
      (task) =>
        task.status === "completed"
    ).length;

  const executable =
    tasks.filter(
      (task) =>
        taskDepth(task) === 4
    ).length;

  $("#metrics").innerHTML =
    [
      metric(
        "Visible",
        tasks.length,
        `depth ≤ ${state.depth}`
      ),
      metric(
        "Ready",
        ready,
        "accepted + ready"
      ),
      metric(
        "Active",
        active,
        "currently executing"
      ),
      metric(
        "Blocked",
        blocked,
        "explicit blockers"
      ),
      metric(
        "Completed",
        completed,
        `${executable} executable actions`
      ),
    ].join("");
}

function statusClass(status) {
  return (
    "status-"
    + String(status || "unknown")
  );
}

function depthLabel(depth) {
  return {
    1: "objective",
    2: "tranche",
    3: "task",
    4: "action",
  }[depth] || "task";
}

function taskCard(task) {
  const depth =
    taskDepth(task);

  const dependencies =
    task.dependencies
    || [];

  const children =
    task.decomposition_children
    || [];

  return `
    <article
      class="completion-task depth-${depth}"
      data-task="${esc(task.task_id)}">

      <div class="completion-task-depth">
        <strong>${depth}</strong>
        <span>${depthLabel(depth)}</span>
      </div>

      <div class="completion-task-main">

        <div class="completion-task-title">
          ${esc(title(task))}
        </div>

        <div class="completion-task-meta">
          <span>
            ${esc(system(task))}
          </span>

          <span>
            ${esc(workstream(task))}
          </span>

          <span>
            ${esc(horizon(task))}
          </span>

          ${
            dependencies.length
              ? `<span>${dependencies.length} deps</span>`
              : ""
          }

          ${
            children.length
              ? `<span>${children.length} children</span>`
              : ""
          }
        </div>

      </div>

      <div class="completion-task-state">

        <span
          class="completion-pill priority-${esc(task.priority)}">
          ${esc(task.priority)}
        </span>

        <span
          class="completion-pill ${statusClass(task.status)}">
          ${esc(task.status)}
        </span>

      </div>

    </article>
  `;
}

function renderTasks(tasks) {
  $("#visibleCount").textContent =
    `${tasks.length} visible`;

  if (!tasks.length) {
    $("#taskTree").innerHTML =
      '<div class="completion-empty">'
      + "No completion work matches these filters."
      + "</div>";

    return;
  }

  $("#taskTree").innerHTML =
    tasks
      .map(taskCard)
      .join("");

  $$("[data-task]")
    .forEach(
      (element) => {
        element.addEventListener(
          "click",
          () => {
            const id =
              element.dataset.task;

            const task =
              state.tasks.find(
                (candidate) =>
                  candidate.task_id
                  === id
              );

            if (task) {
              openDetail(task);
            }
          }
        );
      }
    );
}

function coverage(
  tasks,
  selector,
  extractor
) {
  const counts =
    new Map();

  tasks.forEach(
    (task) => {
      const key =
        extractor(task);

      counts.set(
        key,
        (
          counts.get(key)
          || 0
        )
        + 1
      );
    }
  );

  const maximum =
    Math.max(
      1,
      ...counts.values()
    );

  $(selector).innerHTML =
    [...counts.entries()]
      .sort(
        (a, b) =>
          b[1] - a[1]
      )
      .slice(0, 18)
      .map(
        ([key, count]) => `
          <div class="coverage-row">
            <div class="coverage-label">
              <span>${esc(key)}</span>
              <strong>${count}</strong>
            </div>

            <div class="coverage-track">
              <div
                class="coverage-fill"
                style="width:${
                  Math.max(
                    4,
                    (
                      count
                      / maximum
                    )
                    * 100
                  )
                }%">
              </div>
            </div>
          </div>
        `
      )
      .join("");
}

function renderCoverage(tasks) {
  coverage(
    tasks,
    "#systemCoverage",
    system
  );

  coverage(
    tasks,
    "#workstreamCoverage",
    workstream
  );
}

function list(values) {
  if (!values || !values.length) {
    return '<span class="muted">none</span>';
  }

  return `
    <ul>
      ${
        values
          .map(
            (value) =>
              `<li><code>${esc(value)}</code></li>`
          )
          .join("")
      }
    </ul>
  `;
}

function section(
  label,
  content
) {
  return `
    <section class="detail-section">
      <span class="eyebrow">
        ${esc(label)}
      </span>
      ${content}
    </section>
  `;
}

function openDetail(task) {
  $("#detailId").textContent =
    task.task_id;

  $("#detailTitle").textContent =
    title(task);

  const meta =
    taskMeta(task);

  $("#detailBody").innerHTML =
    section(
      "Classification",
      `
        <div class="detail-grid">
          <div>
            <small>System</small>
            <strong>${esc(system(task))}</strong>
          </div>
          <div>
            <small>Workstream</small>
            <strong>${esc(workstream(task))}</strong>
          </div>
          <div>
            <small>Depth</small>
            <strong>${taskDepth(task)}</strong>
          </div>
          <div>
            <small>Horizon</small>
            <strong>${esc(horizon(task))}</strong>
          </div>
          <div>
            <small>Risk</small>
            <strong>${esc(risk(task))}</strong>
          </div>
          <div>
            <small>Priority</small>
            <strong>${esc(task.priority)}</strong>
          </div>
        </div>
      `
    )
    + section(
      "Purpose",
      `<p>${esc(task.purpose)}</p>`
    )
    + section(
      "Completion condition",
      `<p>${esc(task.completion_condition)}</p>`
    )
    + section(
      "Parent",
      parentId(task)
        ? `<code>${esc(parentId(task))}</code>`
        : '<span class="muted">root objective</span>'
    )
    + section(
      "Dependencies",
      list(task.dependencies)
    )
    + section(
      "Children",
      list(task.decomposition_children)
    )
    + section(
      "Affected instances",
      list(task.affected_instances)
    )
    + section(
      "Blockers",
      list(task.blockers)
    )
    + section(
      "Evidence receipts",
      list(task.evidence_receipts)
    )
    + section(
      "Implementation references",
      list(task.implementation_references)
    )
    + section(
      "Authority basis",
      list(task.authority_basis)
    )
    + section(
      "Projection metadata",
      `
        <pre>${esc(
          JSON.stringify(
            meta,
            null,
            2
          )
        )}</pre>
      `
    );

  $("#detail")
    .classList
    .remove("hidden");

  $("#scrim")
    .classList
    .remove("hidden");
}

function closeDetail() {
  $("#detail")
    .classList
    .add("hidden");

  $("#scrim")
    .classList
    .add("hidden");
}

function renderHealth() {
  const health =
    state.completion
      ?.health
      || {};

  const healthy =
    health.healthy === true;

  $("#health").className =
    "health-card "
    + (
      healthy
        ? "good"
        : ""
    );

  $("#health").innerHTML =
    `
      <strong>
        ${healthy ? "Healthy" : "Attention"}
      </strong>
      <br>
      ${state.tasks.length} task primitives
      <br>
      ${
        health.history_chain_valid === false
          ? "history chain invalid"
          : "immutable history"
      }
    `;
}

function renderMeta() {
  const graph =
    state.completion
      ?.graph
      || {};

  $("#generatedAt").textContent =
    new Date()
      .toLocaleString();

  $("#digest").textContent =
    graph.digest
      ? graph.digest.slice(0, 20)
      : "live";
}

function renderDepth() {
  $$("[data-depth]")
    .forEach(
      (button) => {
        button.classList.toggle(
          "active",
          Number(
            button.dataset.depth
          )
          === state.depth
        );
      }
    );
}

function render() {
  populateFacets();

  const tasks =
    filtered();

  renderDepth();
  renderMetrics(tasks);
  renderTasks(tasks);
  renderCoverage(tasks);
  renderHealth();
  renderMeta();
}

function bind() {
  $("#refresh")
    .addEventListener(
      "click",
      load
    );

  $("#search")
    .addEventListener(
      "input",
      (event) => {
        state.q =
          event.target.value;

        render();
      }
    );

  $("#statusFilter")
    .addEventListener(
      "change",
      (event) => {
        state.status =
          event.target.value;

        render();
      }
    );

  $("#priorityFilter")
    .addEventListener(
      "change",
      (event) => {
        state.priority =
          event.target.value;

        render();
      }
    );

  $("#horizonFilter")
    .addEventListener(
      "change",
      (event) => {
        state.horizon =
          event.target.value;

        render();
      }
    );

  $("#systemFilter")
    .addEventListener(
      "change",
      (event) => {
        state.system =
          event.target.value;

        render();
      }
    );

  $("#workstreamFilter")
    .addEventListener(
      "change",
      (event) => {
        state.workstream =
          event.target.value;

        render();
      }
    );

  $$("[data-depth]")
    .forEach(
      (button) => {
        button.addEventListener(
          "click",
          () => {
            state.depth =
              Number(
                button.dataset.depth
              );

            render();
          }
        );
      }
    );

  $("#closeDetail")
    .addEventListener(
      "click",
      closeDetail
    );

  $("#scrim")
    .addEventListener(
      "click",
      closeDetail
    );

  document.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape"
      ) {
        closeDetail();
      }

      if (
        event.key === "/"
        && document.activeElement
        !== $("#search")
      ) {
        event.preventDefault();

        $("#search").focus();
      }

      if (
        event.key >= "1"
        && event.key <= "4"
        && document.activeElement
        !== $("#search")
      ) {
        state.depth =
          Number(event.key);

        render();
      }
    }
  );
}

bind();

load()
  .catch(
    (error) => {
      $("#health").textContent =
        error.message;

      console.error(error);
    }
  );

window.setInterval(
  () => {
    load().catch(
      console.error
    );
  },
  10000
);
