const state = {
  data: null,
  view: "overview",
  selected: null,
  filters: {
    q: "",
    priority: "",
    status: "",
  },
  poll: null,
};

const $ = (selector) =>
  document.querySelector(
    selector
  );

const $$ = (selector) =>
  [
    ...document.querySelectorAll(
      selector
    ),
  ];

const esc = (value) =>
  String(
    value ?? ""
  ).replace(
    /[&<>"']/g,
    (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    })[character]
  );

const nice = (value) =>
  String(
    value || ""
  )
    .replaceAll(
      "_",
      " "
    )
    .replace(
      /\b\w/g,
      (character) =>
        character.toUpperCase()
    );

const shortId = (id) =>
  id.length > 28
    ? (
        id.slice(
          0,
          12
        )
        + "…"
        + id.slice(
          -8
        )
      )
    : id;

const fmtDate = (value) => {
  if (!value) {
    return "No due date";
  }

  const date = new Date(
    value
  );

  if (
    Number.isNaN(
      date.valueOf()
    )
  ) {
    return value;
  }

  return (
    new Intl.DateTimeFormat(
      undefined,
      {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }
    )
    .format(
      date
    )
  );
};

async function api(
  path,
  options = {}
) {
  const response = await fetch(
    path,
    {
      headers: {
        "Content-Type":
          "application/json",
        ...(
          options.headers
          || {}
        ),
      },
      ...options,
    }
  );

  const body = await response.json();

  if (!response.ok) {
    throw new Error(
      body.error
      || (
        "HTTP "
        + response.status
      )
    );
  }

  return body;
}

function toast(
  message
) {
  const element = $(
    "#toast"
  );

  element.textContent =
    message;

  element.classList.add(
    "show"
  );

  clearTimeout(
    element._timeout
  );

  element._timeout =
    setTimeout(
      () =>
        element.classList.remove(
          "show"
        ),
      2200
    );
}

async function load() {
  try {
    state.data = await api(
      "/api/state"
    );

    render();

    const healthy = Boolean(
      state.data
      .dashboard
      .health
      .healthy
    );

    const badge = $(
      "#healthBadge"
    );

    badge.textContent =
      healthy
        ? "Engine healthy"
        : "Engine needs attention";

    badge.classList.toggle(
      "good",
      healthy
    );

    $(
      "#updatedAt"
    ).textContent =
      (
        "Updated "
        + new Date()
          .toLocaleTimeString()
      );

  } catch (error) {
    toast(
      error.message
    );

    $(
      "#healthBadge"
    ).textContent =
      "Engine unavailable";
  }
}

function filtered() {
  if (!state.data) {
    return [];
  }

  const query = (
    state.filters.q
    .toLowerCase()
  );

  return state.data.tasks.filter(
    (task) =>
      (
        !state.filters.priority
        || task.priority
        === state.filters.priority
      )
      && (
        !state.filters.status
        || task.status
        === state.filters.status
      )
      && (
        !query
        || [
          task.task_id,
          task.title,
          task.purpose,
          task.owner,
          task.jurisdiction,
          ...(
            task.labels
            || []
          ),
        ]
        .join(
          " "
        )
        .toLowerCase()
        .includes(
          query
        )
      )
  );
}

function metric(
  label,
  value,
  sub = ""
) {
  return `
    <div class="metric">
      <div class="label">
        ${esc(label)}
      </div>
      <div class="value">
        ${esc(value)}
      </div>
      <div class="sub">
        ${esc(sub)}
      </div>
    </div>
  `;
}

function render() {
  if (!state.data) {
    return;
  }

  const dashboard =
    state.data.dashboard;

  $(
    "#metricGrid"
  ).innerHTML = [
    metric(
      "Progress",
      (
        dashboard.progress_percent
        + "%"
      ),
      (
        (
          dashboard
          .counts
          .completed
          || 0
        )
        + " completed"
      )
    ),

    metric(
      "Ready",
      dashboard
      .ready_queue
      .length,
      "executable now"
    ),

    metric(
      "Active",
      (
        (
          dashboard
          .counts
          .active
          || 0
        )
        + (
          dashboard
          .counts
          .leased
          || 0
        )
      ),
      "in motion"
    ),

    metric(
      "Blocked",
      dashboard
      .blocked
      .length,
      "needs intervention"
    ),

    metric(
      "Overdue",
      dashboard
      .overdue
      .length,
      "deadline passed"
    ),
  ].join("");

  renderOverview();
  renderBoard();
  renderFocus();
  renderGraph();
  renderHistory();

  if (state.selected) {
    openTask(
      state.selected,
      false
    );
  }
}

function row(
  task,
  right = ""
) {
  return `
    <div
      class="list-row"
      data-task="${esc(task.task_id)}">
      <div>
        <strong>
          ${esc(
            task.title
            || task.purpose
          )}
        </strong>
        <small>
          ${esc(
            shortId(
              task.task_id
            )
          )}
          ·
          ${esc(task.owner)}
        </small>
      </div>
      <div>
        ${
          right
          || `
            <span
              class="priority-pill ${esc(task.priority)}">
              ${esc(task.priority)}
            </span>
          `
        }
      </div>
    </div>
  `;
}

function renderOverview() {
  const dashboard =
    state.data.dashboard;

  $(
    "#nextWork"
  ).innerHTML =
    dashboard
    .ready_queue
    .length
      ? (
          dashboard
          .ready_queue
          .slice(
            0,
            8
          )
          .map(
            (task) =>
              row(
                task,
                `
                  <span
                    class="priority-pill ${task.priority}">
                    ${task.priority}
                  </span>
                `
              )
          )
          .join("")
        )
      : (
          '<div class="empty">'
          + "No executable tasks."
          + "</div>"
        );

  $(
    "#blockers"
  ).innerHTML =
    dashboard
    .blocked
    .length
      ? (
          dashboard
          .blocked
          .slice(
            0,
            8
          )
          .map(
            (task) =>
              row(
                task,
                `
                  <span class="state-pill">
                    ${
                      task
                      .unsatisfied_dependencies
                      .length
                        ? (
                            task
                            .unsatisfied_dependencies
                            .length
                            + " deps"
                          )
                        : (
                            task
                            .blockers
                            .length
                            + " blockers"
                          )
                    }
                  </span>
                `
              )
          )
          .join("")
        )
      : (
          '<div class="empty">'
          + "Nothing is blocked."
          + "</div>"
        );

  const criticalPath =
    dashboard.critical_path;

  $(
    "#criticalPath"
  ).innerHTML =
    (
      criticalPath.available
      && criticalPath.path.length
    )
      ? (
          `
            <div class="critical-chain">
              ${
                criticalPath.path
                .map(
                  (id, index) =>
                    (
                      (
                        index
                          ? (
                              '<span class="critical-arrow">'
                              + "→"
                              + "</span>"
                            )
                          : ""
                      )
                      + `
                        <button
                          class="critical-node"
                          data-task="${esc(id)}">
                          ${esc(shortId(id))}
                        </button>
                      `
                    )
                )
                .join("")
              }
            </div>
            <div
              class="muted"
              style="margin-top:10px">
              ${
                criticalPath.minutes
              }
              estimated minutes remaining
              along the longest dependency path.
            </div>
          `
        )
      : (
          '<div class="empty">'
          + "No critical path available."
          + "</div>"
        );

  $(
    "#bottlenecks"
  ).innerHTML =
    dashboard
    .bottlenecks
    .length
      ? (
          dashboard
          .bottlenecks
          .slice(
            0,
            8
          )
          .map(
            (item) =>
              `
                <div
                  class="list-row"
                  data-task="${esc(item.task_id)}">
                  <div>
                    <strong>
                      ${esc(
                        shortId(
                          item.task_id
                        )
                      )}
                    </strong>
                    <small>
                      ${
                        item.dependents.length
                      }
                      dependent tasks
                    </small>
                  </div>
                  <span class="state-pill">
                    fan-out
                    ${item.fan_out}
                  </span>
                </div>
              `
          )
          .join("")
        )
      : (
          '<div class="empty">'
          + "No bottlenecks."
          + "</div>"
        );
}

const columns = [
  [
    "proposed",
    "Proposed",
  ],
  [
    "ready",
    "Ready",
  ],
  [
    "active",
    "Active",
  ],
  [
    "blocked",
    "Blocked",
  ],
  [
    "completed",
    "Done",
  ],
];

function boardState(
  task
) {
  if (
    task.status === "accepted"
    && task.ready
  ) {
    return "ready";
  }

  if (
    task.status === "leased"
  ) {
    return "active";
  }

  if (
    task.blockers.length
    || task
    .unsatisfied_dependencies
    .length
  ) {
    return "blocked";
  }

  if (
    [
      "proposed",
      "ready",
      "active",
      "blocked",
      "completed",
    ].includes(
      task.status
    )
  ) {
    return task.status;
  }

  return "proposed";
}

function card(
  task
) {
  return `
    <article
      class="task-card"
      draggable="true"
      data-task="${esc(task.task_id)}">

      <div class="task-card-title">
        ${esc(
          task.title
          || task.purpose
        )}
      </div>

      <div class="card-meta">

        <span
          class="priority-pill ${esc(task.priority)}">
          ${esc(task.priority)}
        </span>

        ${
          (
            task.labels
            || []
          )
          .slice(
            0,
            2
          )
          .map(
            (label) =>
              `
                <span class="label-pill">
                  ${esc(label)}
                </span>
              `
          )
          .join("")
        }

      </div>

      <div class="card-foot">

        <span>
          ${esc(
            task.assignee
            || "unassigned"
          )}
        </span>

        <span
          class="${task.overdue ? "overdue" : ""}">
          ${
            esc(
              task.due_at
                ? fmtDate(
                    task.due_at
                  )
                : ""
            )
          }
        </span>

      </div>

    </article>
  `;
}

function renderBoard() {
  const tasks =
    filtered();

  $(
    "#board"
  ).innerHTML =
    columns
    .map(
      ([
        key,
        label,
      ]) => {
        const items =
          tasks.filter(
            (task) =>
              boardState(
                task
              ) === key
          );

        return `
          <section class="board-column">

            <div class="board-head">
              <strong>
                ${label}
              </strong>
              <span class="count-badge">
                ${items.length}
              </span>
            </div>

            <div
              class="dropzone"
              data-drop="${key}">
              ${
                items
                .map(card)
                .join("")
                || (
                  '<div class="empty">'
                  + "Empty"
                  + "</div>"
                )
              }
            </div>

          </section>
        `;
      }
    )
    .join("");

  bindDrag();
}

function renderFocus() {
  const visibleIds =
    new Set(
      filtered()
      .map(
        (task) =>
          task.task_id
      )
    );

  const ready =
    state.data
    .dashboard
    .ready_queue
    .filter(
      (task) =>
        visibleIds.has(
          task.task_id
        )
    );

  $(
    "#focusList"
  ).innerHTML =
    ready.length
      ? (
          ready
          .map(
            (task, index) =>
              `
                <div
                  class="focus-item"
                  data-task="${esc(task.task_id)}">

                  <div class="focus-rank">
                    ${index + 1}
                  </div>

                  <div>
                    <h3>
                      ${esc(
                        task.title
                        || task.purpose
                      )}
                    </h3>

                    <div class="muted">
                      ${esc(task.priority)}
                      · fan-out
                      ${task.fan_out}
                      ·
                      ${
                        esc(
                          task.due_at
                            ? fmtDate(
                                task.due_at
                              )
                            : "no deadline"
                        )
                      }
                    </div>
                  </div>

                  <button
                    class="button ghost"
                    data-action="activate"
                    data-task="${esc(task.task_id)}">
                    Start
                  </button>

                </div>
              `
          )
          .join("")
        )
      : (
          '<div class="empty">'
          + "No ready work matches "
          + "the current filters."
          + "</div>"
        );
}

function renderGraph() {
  const svg = $(
    "#graphSvg"
  );

  const tasks =
    filtered()
    .slice(
      0,
      80
    );

  const ids =
    new Set(
      tasks.map(
        (task) =>
          task.task_id
      )
    );

  const order =
    state.data
    .graph
    .topological_order
    .filter(
      (id) =>
        ids.has(
          id
        )
    );

  const index =
    new Map(
      order.map(
        (id, position) => [
          id,
          position,
        ]
      )
    );

  tasks
  .filter(
    (task) =>
      !index.has(
        task.task_id
      )
  )
  .forEach(
    (task) =>
      index.set(
        task.task_id,
        index.size
      )
  );

  const width = 1200;

  const columns =
    Math.max(
      1,
      Math.ceil(
        Math.sqrt(
          tasks.length
          || 1
        )
      )
    );

  const cellWidth =
    width
    / columns;

  const cellHeight =
    110;

  let definitions = `
    <defs>
      <marker
        id="arrow"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        markerWidth="6"
        markerHeight="6"
        orient="auto-start-reverse">

        <path
          d="M 0 0 L 10 5 L 0 10 z"
          fill="#40506a">
        </path>

      </marker>
    </defs>
  `;

  const positions =
    new Map();

  tasks.forEach(
    (task) => {
      const position =
        index.get(
          task.task_id
        )
        || 0;

      const x =
        30
        + (
          position
          % columns
        )
        * cellWidth;

      const y =
        40
        + Math.floor(
          position
          / columns
        )
        * cellHeight;

      positions.set(
        task.task_id,
        {
          x,
          y,
        }
      );
    }
  );

  let edges = "";

  tasks.forEach(
    (task) =>
      (
        task.dependencies
        || []
      )
      .forEach(
        (dependency) => {
          if (
            !positions.has(
              dependency
            )
            || !positions.has(
              task.task_id
            )
          ) {
            return;
          }

          const source =
            positions.get(
              dependency
            );

          const target =
            positions.get(
              task.task_id
            );

          edges += `
            <path
              class="graph-edge"
              d="
                M ${source.x + 150}
                  ${source.y + 25}
                C ${source.x + 185}
                  ${source.y + 25},
                  ${target.x - 35}
                  ${target.y + 25},
                  ${target.x}
                  ${target.y + 25}
              ">
            </path>
          `;
        }
      )
  );

  const nodes =
    tasks
    .map(
      (task) => {
        const position =
          positions.get(
            task.task_id
          );

        const className =
          task.ready
            ? "ready"
            : (
                task.blockers.length
                || task
                .unsatisfied_dependencies
                .length
              )
              ? "blocked"
              : "";

        return `
          <g
            class="graph-node ${className}"
            data-task="${esc(task.task_id)}"
            transform="
              translate(
                ${position.x},
                ${position.y}
              )
            ">

            <rect
              width="150"
              height="50">
            </rect>

            <text
              x="10"
              y="20">
              ${
                esc(
                  (
                    task.title
                    || task.purpose
                  )
                  .slice(
                    0,
                    19
                  )
                )
              }
            </text>

            <text
              x="10"
              y="37">
              ${esc(task.status)}
              ·
              ${esc(task.priority)}
            </text>

          </g>
        `;
      }
    )
    .join("");

  svg.innerHTML =
    definitions
    + edges
    + nodes;
}

function renderHistory() {
  const events = [
    ...(
      state.data
      .history_tail
      || []
    ),
  ].reverse();

  $(
    "#historyList"
  ).innerHTML =
    events.length
      ? (
          events
          .map(
            (event) =>
              `
                <div
                  class="timeline-item"
                  data-task="${esc(event.task_id)}">

                  <div class="muted">
                    ${esc(fmtDate(event.created_at))}
                  </div>

                  <div class="timeline-dot">
                  </div>

                  <div class="timeline-body">

                    <strong>
                      ${esc(event.event_type)}
                      ·
                      ${
                        esc(
                          shortId(
                            event.task_id
                          )
                        )
                      }
                    </strong>

                    <p>
                      ${esc(event.previous_state || "∅")}
                      →
                      ${
                        esc(
                          event.new_state
                          || event.previous_state
                          || "∅"
                        )
                      }
                    </p>

                  </div>

                </div>
              `
          )
          .join("")
        )
      : (
          '<div class="empty">'
          + "No history yet."
          + "</div>"
        );
}

function findTask(
  id
) {
  return (
    state.data
    ?.tasks
    .find(
      (task) =>
        task.task_id
        === id
    )
  );
}

function openTask(
  id,
  show = true
) {
  const task =
    findTask(
      id
    );

  if (!task) {
    return;
  }

  state.selected =
    id;

  $(
    "#drawerId"
  ).textContent =
    task.task_id;

  $(
    "#drawerTitle"
  ).textContent =
    task.title
    || task.purpose;

  $(
    "#drawerBody"
  ).innerHTML = `
    <div class="detail-grid">

      <div class="detail-field">
        <span>Status</span>
        ${esc(task.status)}
      </div>

      <div class="detail-field">
        <span>Priority</span>
        ${esc(task.priority)}
      </div>

      <div class="detail-field">
        <span>Owner</span>
        ${esc(task.owner)}
      </div>

      <div class="detail-field">
        <span>Assignee</span>
        ${esc(task.assignee || "unassigned")}
      </div>

      <div class="detail-field">
        <span>Due</span>
        <div class="${task.overdue ? "overdue" : ""}">
          ${
            esc(
              task.due_at
                ? fmtDate(task.due_at)
                : "none"
            )
          }
        </div>
      </div>

      <div class="detail-field">
        <span>Estimate</span>
        ${esc(task.estimate_minutes)} min
      </div>

    </div>

    <div class="drawer-section">

      <h3>Quick actions</h3>

      <div class="detail-actions">

        ${
          [
            "accepted",
            "ready",
            "active",
            "blocked",
            "deferred",
          ]
          .map(
            (status) =>
              `
                <button
                  class="button ghost"
                  data-transition="${status}">
                  ${nice(status)}
                </button>
              `
          )
          .join("")
        }

        ${
          task.status
          !== "completed"
            ? `
                <button
                  class="button primary"
                  data-transition="completed">
                  Complete
                </button>
              `
            : ""
        }

      </div>

    </div>

    <div class="drawer-section">

      <h3>Edit</h3>

      <label>
        Title
        <input
          id="editTitle"
          value="${esc(task.title)}">
      </label>

      <label>
        Priority
        <select id="editPriority">
          ${
            [
              "critical",
              "high",
              "normal",
              "low",
              "deferred",
            ]
            .map(
              (priority) =>
                `
                  <option
                    ${
                      priority
                      === task.priority
                        ? "selected"
                        : ""
                    }>
                    ${priority}
                  </option>
                `
            )
            .join("")
          }
        </select>
      </label>

      <label>
        Assignee
        <input
          id="editAssignee"
          value="${esc(task.assignee || "")}">
      </label>

      <label>
        Due
        <input
          id="editDue"
          type="datetime-local"
          value="${
            task.due_at
              ? esc(
                  new Date(
                    task.due_at
                  )
                  .toISOString()
                  .slice(
                    0,
                    16
                  )
                )
              : ""
          }">
      </label>

      <label>
        Labels
        <input
          id="editLabels"
          value="${esc((task.labels || []).join(", "))}">
      </label>

      <label>
        Notes
        <textarea
          id="editNotes"
          rows="5">${esc(task.notes || "")}</textarea>
      </label>

      <button
        id="saveTask"
        class="button primary">
        Save changes
      </button>

    </div>

    <div class="drawer-section">

      <h3>Dependencies</h3>

      <div class="dependency-list">

        ${
          (
            task.dependencies
            || []
          )
          .map(
            (dependency) =>
              `
                <button
                  class="dependency-chip"
                  data-task="${esc(dependency)}">
                  ${esc(shortId(dependency))}
                </button>
              `
          )
          .join("")
          || (
            '<span class="muted">'
            + "None"
            + "</span>"
          )
        }

      </div>

    </div>

    <div class="drawer-section">

      <h3>Completion</h3>

      <div class="muted">
        ${esc(task.completion_condition)}
      </div>

    </div>
  `;

  if (show) {
    $(
      "#drawer"
    ).classList.remove(
      "hidden"
    );

    $(
      "#scrim"
    ).classList.remove(
      "hidden"
    );
  }

  bindDrawer(
    task
  );
}

function closeDrawer() {
  state.selected =
    null;

  $(
    "#drawer"
  ).classList.add(
    "hidden"
  );

  $(
    "#scrim"
  ).classList.add(
    "hidden"
  );
}

function bindDrawer(
  task
) {
  $$(
    "[data-transition]"
  ).forEach(
    (button) =>
      button.onclick =
        async () => {
          let receipts = [];

          if (
            button.dataset.transition
            === "completed"
          ) {
            const receipt =
              prompt(
                (
                  "Evidence or receipt "
                  + "reference required "
                  + "to complete:"
                )
              );

            if (!receipt) {
              return;
            }

            receipts = [
              receipt
            ];
          }

          try {
            await api(
              (
                "/api/tasks/"
                + encodeURIComponent(
                    task.task_id
                  )
                + "/transition"
              ),
              {
                method:
                  "POST",

                body:
                  JSON.stringify(
                    {
                      state:
                        button.dataset
                        .transition,

                      receipts,
                    }
                  ),
              }
            );

            toast(
              "Task transitioned"
            );

            await load();

          } catch (error) {
            toast(
              error.message
            );
          }
        }
  );

  $(
    "#saveTask"
  ).onclick =
    async () => {
      try {
        const due =
          $(
            "#editDue"
          ).value;

        await api(
          (
            "/api/tasks/"
            + encodeURIComponent(
                task.task_id
              )
          ),
          {
            method:
              "PATCH",

            body:
              JSON.stringify(
                {
                  title:
                    $(
                      "#editTitle"
                    ).value,

                  priority:
                    $(
                      "#editPriority"
                    ).value,

                  assignee:
                    (
                      $(
                        "#editAssignee"
                      ).value
                      || null
                    ),

                  due_at:
                    (
                      due
                        ? new Date(
                            due
                          ).toISOString()
                        : null
                    ),

                  labels:
                    $(
                      "#editLabels"
                    )
                    .value
                    .split(
                      ","
                    )
                    .map(
                      (value) =>
                        value.trim()
                    )
                    .filter(
                      Boolean
                    ),

                  notes:
                    $(
                      "#editNotes"
                    ).value,
                }
              ),
          }
        );

        toast(
          "Task updated"
        );

        await load();

      } catch (error) {
        toast(
          error.message
        );
      }
    };
}

function bindDrag() {
  let dragged = null;

  $$(
    ".task-card"
  ).forEach(
    (card) => {
      card.addEventListener(
        "dragstart",
        () => {
          dragged =
            card.dataset.task;

          card.classList.add(
            "dragging"
          );
        }
      );

      card.addEventListener(
        "dragend",
        () =>
          card.classList.remove(
            "dragging"
          )
      );
    }
  );

  $$(
    ".dropzone"
  ).forEach(
    (zone) => {
      zone.addEventListener(
        "dragover",
        (event) => {
          event.preventDefault();

          zone.classList.add(
            "dragover"
          );
        }
      );

      zone.addEventListener(
        "dragleave",
        () =>
          zone.classList.remove(
            "dragover"
          )
      );

      zone.addEventListener(
        "drop",
        async (event) => {
          event.preventDefault();

          zone.classList.remove(
            "dragover"
          );

          if (!dragged) {
            return;
          }

          const target =
            zone.dataset.drop;

          try {
            if (
              target
              === "completed"
            ) {
              const receipt =
                prompt(
                  (
                    "Evidence or receipt "
                    + "reference required "
                    + "to complete:"
                  )
                );

              if (!receipt) {
                return;
              }

              await api(
                (
                  "/api/tasks/"
                  + encodeURIComponent(
                      dragged
                    )
                  + "/transition"
                ),
                {
                  method:
                    "POST",

                  body:
                    JSON.stringify(
                      {
                        state:
                          "completed",

                        receipts: [
                          receipt
                        ],
                      }
                    ),
                }
              );

            } else {
              await api(
                (
                  "/api/tasks/"
                  + encodeURIComponent(
                      dragged
                    )
                  + "/transition"
                ),
                {
                  method:
                    "POST",

                  body:
                    JSON.stringify(
                      {
                        state:
                          target,
                      }
                    ),
                }
              );
            }

            await load();

          } catch (error) {
            toast(
              error.message
            );
          }
        }
      );
    }
  );
}

function setView(
  view
) {
  state.view =
    view;

  $$(
    ".view"
  ).forEach(
    (element) =>
      element.classList.remove(
        "active"
      )
  );

  $(
    "#"
    + view
    + "View"
  ).classList.add(
    "active"
  );

  $$(
    ".nav-item"
  ).forEach(
    (button) =>
      button.classList.toggle(
        "active",
        button.dataset.view
        === view
      )
  );
}

document.addEventListener(
  "click",
  (event) => {
    const task =
      event.target.closest(
        "[data-task]"
      );

    if (
      task
      && !event.target.closest(
        "[data-action]"
      )
    ) {
      openTask(
        task.dataset.task
      );
    }

    const action =
      event.target.closest(
        '[data-action="activate"]'
      );

    if (action) {
      event.stopPropagation();

      api(
        (
          "/api/tasks/"
          + encodeURIComponent(
              action.dataset.task
            )
          + "/transition"
        ),
        {
          method:
            "POST",

          body:
            JSON.stringify(
              {
                state:
                  "active",
              }
            ),
        }
      )
      .then(
        load
      )
      .catch(
        (error) =>
          toast(
            error.message
          )
      );
    }
  }
);

$$(
  ".nav-item"
).forEach(
  (button) =>
    button.onclick =
      () =>
        setView(
          button.dataset.view
        )
);

$(
  "#refresh"
).onclick =
  load;

$(
  "#newTask"
).onclick =
  () =>
    $(
      "#taskDialog"
    ).showModal();

$(
  "#closeDialog"
).onclick =
  () =>
    $(
      "#taskDialog"
    ).close();

$(
  "#cancelDialog"
).onclick =
  () =>
    $(
      "#taskDialog"
    ).close();

$(
  "#closeDrawer"
).onclick =
  closeDrawer;

$(
  "#scrim"
).onclick =
  closeDrawer;

$(
  "#priorityFilter"
).onchange =
  (event) => {
    state.filters.priority =
      event.target.value;

    render();
  };

$(
  "#statusFilter"
).onchange =
  (event) => {
    state.filters.status =
      event.target.value;

    render();
  };

let searchTimer;

$(
  "#search"
).oninput =
  (event) => {
    clearTimeout(
      searchTimer
    );

    searchTimer =
      setTimeout(
        () => {
          state.filters.q =
            event.target.value;

          render();
        },
        120
      );
  };

$(
  "#taskForm"
).addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    const form =
      new FormData(
        event.target
      );

    const due =
      form.get(
        "due_at"
      );

    const payload = {
      title:
        form.get(
          "title"
        ),

      purpose:
        form.get(
          "title"
        ),

      priority:
        form.get(
          "priority"
        ),

      status:
        form.get(
          "status"
        ),

      owner:
        form.get(
          "owner"
        ),

      jurisdiction:
        form.get(
          "jurisdiction"
        ),

      estimate_minutes:
        Number(
          form.get(
            "estimate_minutes"
          )
          || 30
        ),

      due_at:
        (
          due
            ? new Date(
                due
              ).toISOString()
            : null
        ),

      labels:
        String(
          form.get(
            "labels"
          )
          || ""
        )
        .split(
          ","
        )
        .map(
          (value) =>
            value.trim()
        )
        .filter(
          Boolean
        ),

      dependencies:
        String(
          form.get(
            "dependencies"
          )
          || ""
        )
        .split(
          ","
        )
        .map(
          (value) =>
            value.trim()
        )
        .filter(
          Boolean
        ),

      completion_condition:
        form.get(
          "completion_condition"
        ),

      notes:
        form.get(
          "notes"
        ),

      authority_basis: [
        "current-user-directive",
      ],
    };

    try {
      await api(
        "/api/tasks",
        {
          method:
            "POST",

          body:
            JSON.stringify(
              payload
            ),
        }
      );

      $(
        "#taskDialog"
      ).close();

      event.target.reset();

      toast(
        "Task created"
      );

      await load();

    } catch (error) {
      toast(
        error.message
      );
    }
  }
);

document.addEventListener(
  "keydown",
  (event) => {
    const editing =
      [
        "INPUT",
        "TEXTAREA",
        "SELECT",
      ].includes(
        document
        .activeElement
        .tagName
      );

    if (
      event.key === "/"
      && !editing
    ) {
      event.preventDefault();

      $(
        "#search"
      ).focus();
    }

    if (
      event.key === "n"
      && !editing
    ) {
      $(
        "#taskDialog"
      ).showModal();
    }

    if (
      event.key === "r"
      && !editing
    ) {
      load();
    }

    if (
      event.key
      === "Escape"
    ) {
      closeDrawer();
    }

    if (
      [
        "1",
        "2",
        "3",
        "4",
        "5",
      ].includes(
        event.key
      )
      && !editing
    ) {
      setView(
        [
          "overview",
          "board",
          "focus",
          "graph",
          "history",
        ][
          Number(
            event.key
          )
          - 1
        ]
      );
    }
  }
);

load();

state.poll =
  setInterval(
    () => {
      if (
        !document.hidden
      ) {
        load();
      }
    },
    10000
  );
