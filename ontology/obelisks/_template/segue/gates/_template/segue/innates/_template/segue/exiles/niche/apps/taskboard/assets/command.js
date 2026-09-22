"use strict";

const state = {
  payload: null,
  health: null,
  view: "cockpit",
  depth: 3,
  query: "",
  status: "",
  priority: "",
  system: "",
  workstream: "",
  selected: null,
  topologyScale: 1,
  loading: false,
  lastLoaded: null,
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

const priorityWeight = {
  critical: 5,
  high: 4,
  normal: 3,
  low: 2,
  deferred: 1,
};

const terminalStates =
  new Set([
    "completed",
    "rejected",
    "superseded",
  ]);

function meta(task) {
  return (
    task.extension_slots
    ?.["niche.taskboard"]
    || {}
  );
}

function taskTitle(task) {
  return (
    meta(task).title
    || task.title
    || task.purpose
    || task.task_id
  );
}

function taskSystem(task) {
  return (
    meta(task).system
    || task.jurisdiction
    || "savant"
  );
}

function taskWorkstream(task) {
  return (
    meta(task).workstream
    || taskSystem(task)
  );
}

function taskDepth(task) {
  const value =
    Number(
      meta(task).depth
      || task.extension_slots
        ?.completion
        ?.depth
      || 1
    );

  return (
    Number.isFinite(value)
      ? Math.max(
          1,
          Math.min(
            4,
            value
          )
        )
      : 1
  );
}

function taskRisk(task) {
  return (
    meta(task).risk
    || "unknown"
  );
}

function taskHorizon(task) {
  return (
    meta(task).horizon
    || "backlog"
  );
}

function shortId(value) {
  const parts =
    String(value || "")
      .split(":");

  return (
    parts.length > 2
      ? parts
        .slice(-2)
        .join(":")
      : String(value || "")
  );
}

function fmtDate(value) {
  if (!value) {
    return "none";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return String(value);
  }

  return date.toLocaleString();
}

function nice(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (character) =>
        character.toUpperCase()
    );
}

function isBlocked(task) {
  return (
    task.status === "blocked"
    || (
      task.blockers
      || []
    ).length > 0
    || (
      task.unsatisfied_dependencies
      || []
    ).length > 0
  );
}

function isReady(task) {
  return (
    task.ready === true
    && !terminalStates.has(
      task.status
    )
  );
}

function tasks() {
  return (
    state.payload
    ?.tasks
    || []
  );
}

function dashboard() {
  return (
    state.payload
    ?.dashboard
    || {}
  );
}

function graph() {
  return (
    state.payload
    ?.graph
    || {}
  );
}

async function api(
  path,
  options = {}
) {
  const response =
    await fetch(
      path,
      {
        cache: "no-store",
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

  const payload =
    await response.json()
      .catch(
        () => ({})
      );

  if (!response.ok) {
    throw new Error(
      payload.error
      || `${response.status} ${response.statusText}`
    );
  }

  return payload;
}

async function load() {
  if (state.loading) {
    return;
  }

  state.loading = true;

  setSync(
    "syncing",
    "busy"
  );

  try {
    const [
      payload,
      health,
    ] = await Promise.all([
      api("/api/state"),
      api("/api/health"),
    ]);

    state.payload =
      payload;

    state.health =
      health;

    state.lastLoaded =
      new Date();

    render();

    setSync(
      "live",
      health.healthy === true
        ? "good"
        : "warn"
    );

  } catch (error) {
    setSync(
      "offline",
      "bad"
    );

    toast(
      error.message
    );

  } finally {
    state.loading = false;
  }
}

function setSync(
  text,
  className
) {
  const element =
    $("#syncState");

  element.textContent =
    text;

  element.className =
    `sync-state ${className}`;
}

function filteredTasks() {
  const query =
    state.query
      .trim()
      .toLowerCase();

  return tasks()
    .filter(
      (task) =>
        taskDepth(task)
        <= state.depth
    )
    .filter(
      (task) =>
        !state.status
        || (
          state.status === "ready"
            ? isReady(task)
            : task.status
              === state.status
        )
    )
    .filter(
      (task) =>
        !state.priority
        || task.priority
          === state.priority
    )
    .filter(
      (task) =>
        !state.system
        || taskSystem(task)
          === state.system
    )
    .filter(
      (task) =>
        !state.workstream
        || taskWorkstream(task)
          === state.workstream
    )
    .filter(
      (task) => {
        if (!query) {
          return true;
        }

        const haystack = [
          task.task_id,
          taskTitle(task),
          task.purpose,
          task.owner,
          task.assignee,
          task.status,
          task.priority,
          taskSystem(task),
          taskWorkstream(task),
          taskRisk(task),
          taskHorizon(task),
          task.completion_condition,
          ...(task.labels || []),
          ...(task.dependencies || []),
          ...(task.blockers || []),
          ...(task.affected_instances || []),
          ...(task.evidence_receipts || []),
          ...(task.implementation_references || []),
        ]
          .join(" ")
          .toLowerCase();

        return haystack.includes(
          query
        );
      }
    );
}

function focusScore(task) {
  let score =
    (
      priorityWeight[
        task.priority
      ]
      || 0
    )
    * 100;

  score +=
    Math.min(
      20,
      Number(
        task.fan_out
        || 0
      )
    )
    * 8;

  if (task.overdue) {
    score += 140;
  }

  if (
    taskRisk(task)
    === "high"
  ) {
    score += 20;
  }

  if (
    taskHorizon(task)
    === "now"
  ) {
    score += 30;
  }

  return score;
}

function readyQueue() {
  const visible =
    new Set(
      filteredTasks()
        .map(
          (task) =>
            task.task_id
        )
    );

  const authoritative =
    dashboard()
      .ready_queue
      || [];

  return authoritative
    .filter(
      (task) =>
        visible.has(
          task.task_id
        )
    );
}

function metric(
  label,
  value,
  detail,
  tone = ""
) {
  return `
    <article
      class="command-metric ${esc(tone)}">

      <span>
        ${esc(label)}
      </span>

      <strong>
        ${esc(value)}
      </strong>

      <small>
        ${esc(detail)}
      </small>

    </article>
  `;
}

function renderMetrics() {
  const all =
    filteredTasks();

  const complete =
    all.filter(
      (task) =>
        task.status
        === "completed"
    ).length;

  const ready =
    all.filter(
      isReady
    ).length;

  const active =
    all.filter(
      (task) =>
        [
          "active",
          "leased",
        ].includes(
          task.status
        )
    ).length;

  const blocked =
    all.filter(
      isBlocked
    ).length;

  const overdue =
    all.filter(
      (task) =>
        task.overdue
    ).length;

  const progress =
    all.length
      ? Math.round(
          (
            complete
            / all.length
          )
          * 100
        )
      : 0;

  $("#metricGrid").innerHTML =
    [
      metric(
        "Progress",
        `${progress}%`,
        `${complete} of ${all.length}`,
        "progress"
      ),

      metric(
        "Ready",
        ready,
        "executable now",
        "ready"
      ),

      metric(
        "Active",
        active,
        "in motion",
        "active"
      ),

      metric(
        "Blocked",
        blocked,
        "requires intervention",
        blocked
          ? "blocked"
          : ""
      ),

      metric(
        "Overdue",
        overdue,
        "deadline exposure",
        overdue
          ? "danger"
          : ""
      ),

      metric(
        "Depth",
        state.depth,
        [
          "",
          "objective",
          "tranche",
          "task",
          "action",
        ][state.depth],
        ""
      ),
    ].join("");
}

function taskPills(task) {
  return `
    <span
      class="pill priority-${esc(task.priority)}">
      ${esc(task.priority)}
    </span>

    <span
      class="pill status-${esc(task.status)}">
      ${esc(task.status)}
    </span>
  `;
}

function workRow(
  task,
  rank = null
) {
  const dependencyCount =
    (
      task.dependencies
      || []
    ).length;

  const blockerCount =
    (
      task.blockers
      || []
    ).length
    + (
      task.unsatisfied_dependencies
      || []
    ).length;

  return `
    <article
      class="work-row"
      data-task="${esc(task.task_id)}">

      ${
        rank !== null
          ? `
            <div class="work-rank">
              ${rank}
            </div>
          `
          : ""
      }

      <div class="work-content">

        <strong>
          ${esc(taskTitle(task))}
        </strong>

        <div class="work-meta">

          <span>
            ${esc(taskSystem(task))}
          </span>

          <span>
            ${esc(taskWorkstream(task))}
          </span>

          ${
            dependencyCount
              ? `
                <span>
                  ${dependencyCount} deps
                </span>
              `
              : ""
          }

          ${
            blockerCount
              ? `
                <span class="danger-text">
                  ${blockerCount} blocked
                </span>
              `
              : ""
          }

          ${
            task.estimate_minutes
              ? `
                <span>
                  ${esc(task.estimate_minutes)}m
                </span>
              `
              : ""
          }

        </div>

      </div>

      <div class="work-state">
        ${taskPills(task)}
      </div>

    </article>
  `;
}

function empty(message) {
  return `
    <div class="command-empty">
      ${esc(message)}
    </div>
  `;
}

function renderNextWork() {
  const ready =
    readyQueue()
      .slice(
        0,
        10
      );

  $("#nextWork").innerHTML =
    ready.length
      ? ready
        .map(
          (task, index) =>
            workRow(
              task,
              index + 1
            )
        )
        .join("")
      : empty(
          "No executable work matches the current scope."
        );
}

function renderBlockers() {
  const blocked =
    filteredTasks()
      .filter(
        isBlocked
      )
      .sort(
        (a, b) =>
          focusScore(b)
          - focusScore(a)
      );

  $("#blockerCount")
    .textContent =
      String(
        blocked.length
      );

  $("#blockerRadar")
    .innerHTML =
      blocked.length
        ? blocked
          .slice(
            0,
            8
          )
          .map(
            (task) =>
              workRow(task)
          )
          .join("")
        : empty(
            "No blockers in this scope."
          );
}

function renderBottlenecks() {
  const bottlenecks =
    dashboard()
      .bottlenecks
      || [];

  $("#bottleneckMap")
    .innerHTML =
      bottlenecks.length
        ? bottlenecks
          .slice(
            0,
            8
          )
          .map(
            (item) => {
              const task =
                tasks().find(
                  (candidate) =>
                    candidate.task_id
                    === item.task_id
                );

              return `
                <article
                  class="signal-row"
                  data-task="${esc(item.task_id)}">

                  <div>
                    <strong>
                      ${esc(
                        task
                          ? taskTitle(task)
                          : shortId(
                              item.task_id
                            )
                      )}
                    </strong>

                    <span>
                      ${
                        (
                          item.dependents
                          || []
                        ).length
                      }
                      downstream dependents
                    </span>
                  </div>

                  <b>
                    ${esc(item.fan_out)}
                  </b>

                </article>
              `;
            }
          )
          .join("")
        : empty(
            "No dependency bottlenecks."
          );
}

function renderCriticalPath() {
  const critical =
    dashboard()
      .critical_path
      || {};

  if (
    !critical.available
    || !(
      critical.path
      || []
    ).length
  ) {
    $("#criticalPath")
      .innerHTML =
        empty(
          "No critical path is available."
        );

    return;
  }

  $("#criticalPath")
    .innerHTML = `
      <div class="critical-path">

        ${
          critical.path
            .map(
              (id, index) => `
                ${
                  index
                    ? '<span class="path-arrow">→</span>'
                    : ""
                }

                <button
                  class="path-node"
                  data-task="${esc(id)}">
                  ${esc(shortId(id))}
                </button>
              `
            )
            .join("")
        }

      </div>

      <div class="critical-summary">
        <strong>
          ${esc(critical.minutes || 0)}
        </strong>
        estimated minutes on the longest dependency chain
      </div>
    `;
}

function systemStats() {
  const values =
    new Map();

  filteredTasks()
    .forEach(
      (task) => {
        const key =
          taskSystem(task);

        if (!values.has(key)) {
          values.set(
            key,
            {
              total: 0,
              completed: 0,
              ready: 0,
              blocked: 0,
              active: 0,
            }
          );
        }

        const item =
          values.get(key);

        item.total += 1;

        if (
          task.status
          === "completed"
        ) {
          item.completed += 1;
        }

        if (isReady(task)) {
          item.ready += 1;
        }

        if (isBlocked(task)) {
          item.blocked += 1;
        }

        if (
          [
            "active",
            "leased",
          ].includes(
            task.status
          )
        ) {
          item.active += 1;
        }
      }
    );

  return [...values.entries()]
    .sort(
      (a, b) =>
        b[1].total
        - a[1].total
    );
}

function renderSystemPulse() {
  const values =
    systemStats();

  $("#systemPulse")
    .innerHTML =
      values.length
        ? values
          .slice(
            0,
            18
          )
          .map(
            ([name, item]) => {
              const percent =
                item.total
                  ? Math.round(
                      (
                        item.completed
                        / item.total
                      )
                      * 100
                    )
                  : 0;

              return `
                <article class="pulse-card">

                  <header>
                    <strong>
                      ${esc(name)}
                    </strong>

                    <span>
                      ${percent}%
                    </span>
                  </header>

                  <div class="pulse-track">
                    <div
                      class="pulse-fill"
                      style="width:${percent}%">
                    </div>
                  </div>

                  <footer>
                    <span>
                      ${item.total} total
                    </span>

                    <span>
                      ${item.ready} ready
                    </span>

                    <span>
                      ${item.blocked} blocked
                    </span>
                  </footer>

                </article>
              `;
            }
          )
          .join("")
        : empty(
            "No system data in this scope."
          );
}

function renderActivity() {
  const events =
    [
      ...(
        state.payload
        ?.history_tail
        || []
      ),
    ]
      .reverse()
      .slice(
        0,
        10
      );

  $("#activityFeed")
    .innerHTML =
      events.length
        ? events
          .map(
            (event) => `
              <article
                class="activity-item"
                data-task="${esc(event.task_id)}">

                <span class="activity-dot">
                </span>

                <div>
                  <strong>
                    ${esc(
                      nice(
                        event.event_type
                      )
                    )}
                  </strong>

                  <span>
                    ${esc(
                      shortId(
                        event.task_id
                      )
                    )}
                  </span>

                  <small>
                    ${esc(
                      fmtDate(
                        event.created_at
                      )
                    )}
                  </small>
                </div>

              </article>
            `
          )
          .join("")
        : empty(
            "No recent events."
          );
}

function renderCockpit() {
  renderMetrics();
  renderNextWork();
  renderBlockers();
  renderBottlenecks();
  renderCriticalPath();
  renderSystemPulse();
  renderActivity();
}

function renderFocus() {
  const ready =
    readyQueue();

  const minutes =
    ready.reduce(
      (total, task) =>
        total
        + Number(
            task.estimate_minutes
            || 0
          ),
      0
    );

  $("#focusSummary")
    .textContent =
      `${ready.length} ready · ${minutes} estimated minutes`;

  $("#focusQueue")
    .innerHTML =
      ready.length
        ? ready
          .map(
            (task, index) => `
              <article
                class="focus-card"
                data-task="${esc(task.task_id)}">

                <div class="focus-number">
                  ${index + 1}
                </div>

                <div class="focus-main">

                  <span class="eyebrow">
                    ${esc(taskSystem(task))}
                    /
                    ${esc(taskWorkstream(task))}
                  </span>

                  <h2>
                    ${esc(taskTitle(task))}
                  </h2>

                  <p>
                    ${esc(
                      task.completion_condition
                      || task.purpose
                    )}
                  </p>

                  <div class="focus-meta">
                    ${taskPills(task)}

                    <span>
                      fan-out
                      ${esc(task.fan_out || 0)}
                    </span>

                    <span>
                      ${esc(task.estimate_minutes || 0)}
                      minutes
                    </span>

                    <span>
                      ${esc(taskHorizon(task))}
                    </span>

                    <span>
                      risk
                      ${esc(taskRisk(task))}
                    </span>
                  </div>

                </div>

                <button
                  class="command-button primary"
                  data-start="${esc(task.task_id)}">
                  Start
                </button>

              </article>
            `
          )
          .join("")
        : empty(
            "The executable queue is empty."
          );
}

function matrixGroup(task) {
  if (
    task.status
    === "completed"
  ) {
    return "completed";
  }

  if (isBlocked(task)) {
    return "blocked";
  }

  if (
    [
      "active",
      "leased",
    ].includes(
      task.status
    )
  ) {
    return "active";
  }

  if (isReady(task)) {
    return "ready";
  }

  return "planned";
}

const matrixColumns = [
  [
    "planned",
    "Planned",
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
    "Completed",
  ],
];

function matrixCard(task) {
  return `
    <article
      class="matrix-card"
      data-task="${esc(task.task_id)}">

      <div class="matrix-card-top">
        ${taskPills(task)}
      </div>

      <strong>
        ${esc(taskTitle(task))}
      </strong>

      <p>
        ${esc(
          task.completion_condition
          || task.purpose
        )}
      </p>

      <footer>
        <span>
          ${esc(taskSystem(task))}
        </span>

        <span>
          d${taskDepth(task)}
        </span>
      </footer>

    </article>
  `;
}

function renderMatrix() {
  const visible =
    filteredTasks();

  $("#visibleCount")
    .textContent =
      `${visible.length} visible`;

  $("#matrix")
    .innerHTML =
      matrixColumns
        .map(
          ([key, label]) => {
            const items =
              visible
                .filter(
                  (task) =>
                    matrixGroup(task)
                    === key
                )
                .sort(
                  (a, b) =>
                    focusScore(b)
                    - focusScore(a)
                );

            return `
              <section class="matrix-column">

                <header>
                  <strong>
                    ${esc(label)}
                  </strong>

                  <span>
                    ${items.length}
                  </span>
                </header>

                <div>
                  ${
                    items.length
                      ? items
                        .map(
                          matrixCard
                        )
                        .join("")
                      : empty(
                          "No tasks"
                        )
                  }
                </div>

              </section>
            `;
          }
        )
        .join("");
}

function renderTopology() {
  const visible =
    filteredTasks()
      .slice(
        0,
        120
      );

  const visibleIds =
    new Set(
      visible.map(
        (task) =>
          task.task_id
      )
    );

  const topological =
    (
      graph()
        .topological_order
      || []
    )
      .filter(
        (id) =>
          visibleIds.has(id)
      );

  const ordered =
    [
      ...topological,
      ...visible
        .map(
          (task) =>
            task.task_id
        )
        .filter(
          (id) =>
            !topological.includes(id)
        ),
    ];

  const taskById =
    new Map(
      visible.map(
        (task) => [
          task.task_id,
          task,
        ]
      )
    );

  const level =
    new Map();

  ordered.forEach(
    (id) => {
      const task =
        taskById.get(id);

      const dependencies =
        (
          task?.dependencies
          || []
        )
          .filter(
            (dependency) =>
              visibleIds.has(
                dependency
              )
          );

      const depth =
        dependencies.length
          ? Math.max(
              ...dependencies.map(
                (dependency) =>
                  (
                    level.get(
                      dependency
                    )
                    || 0
                  )
                  + 1
              )
            )
          : 0;

      level.set(
        id,
        depth
      );
    }
  );

  const groups =
    new Map();

  ordered.forEach(
    (id) => {
      const depth =
        level.get(id)
        || 0;

      if (!groups.has(depth)) {
        groups.set(
          depth,
          []
        );
      }

      groups
        .get(depth)
        .push(id);
    }
  );

  const positions =
    new Map();

  [...groups.entries()]
    .forEach(
      ([depth, ids]) => {
        ids.forEach(
          (id, index) => {
            positions.set(
              id,
              {
                x:
                  70
                  + depth
                  * 310,

                y:
                  70
                  + index
                  * 90,
              }
            );
          }
        );
      }
    );

  let edges = "";

  visible.forEach(
    (task) => {
      const target =
        positions.get(
          task.task_id
        );

      (
        task.dependencies
        || []
      ).forEach(
        (dependency) => {
          const source =
            positions.get(
              dependency
            );

          if (
            !source
            || !target
          ) {
            return;
          }

          edges += `
            <path
              class="topology-edge"
              d="
                M ${source.x + 205}
                  ${source.y + 28}
                C ${source.x + 250}
                  ${source.y + 28},
                  ${target.x - 45}
                  ${target.y + 28},
                  ${target.x}
                  ${target.y + 28}
              ">
            </path>
          `;
        }
      );
    }
  );

  const nodes =
    visible
      .map(
        (task) => {
          const position =
            positions.get(
              task.task_id
            )
            || {
              x: 0,
              y: 0,
            };

          const classes = [
            isReady(task)
              ? "ready"
              : "",

            isBlocked(task)
              ? "blocked"
              : "",

            task.status
              === "completed"
              ? "completed"
              : "",
          ]
            .filter(Boolean)
            .join(" ");

          return `
            <g
              class="topology-node ${classes}"
              data-task="${esc(task.task_id)}"
              transform="
                translate(
                  ${position.x},
                  ${position.y}
                )
              ">

              <rect
                width="205"
                height="56">
              </rect>

              <text
                class="node-title"
                x="12"
                y="22">
                ${esc(
                  taskTitle(task)
                    .slice(
                      0,
                      27
                    )
                )}
              </text>

              <text
                class="node-meta"
                x="12"
                y="41">
                ${esc(task.status)}
                ·
                ${esc(task.priority)}
              </text>

            </g>
          `;
        }
      )
      .join("");

  $("#topologySvg")
    .innerHTML = `
      <defs>
        <marker
          id="topologyArrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse">

          <path
            d="M 0 0 L 10 5 L 0 10 z">
          </path>

        </marker>
      </defs>

      ${edges}
      ${nodes}
    `;

  applyTopologyScale();
}

function signalCard(
  kind,
  title,
  detail,
  count,
  taskId = null
) {
  return `
    <article
      class="signal-card ${esc(kind)}"
      ${
        taskId
          ? `data-task="${esc(taskId)}"`
          : ""
      }>

      <span class="signal-kind">
        ${esc(kind)}
      </span>

      <strong>
        ${esc(title)}
      </strong>

      <p>
        ${esc(detail)}
      </p>

      <b>
        ${esc(count)}
      </b>

    </article>
  `;
}

function deriveSignals() {
  const visible =
    filteredTasks();

  const signals = [];

  const blocked =
    visible.filter(
      isBlocked
    );

  if (blocked.length) {
    signals.push(
      signalCard(
        "intervention",
        "Blocked work",
        "Tasks cannot advance without dependency or explicit blocker resolution.",
        blocked.length,
        blocked[0].task_id
      )
    );
  }

  const overdue =
    visible.filter(
      (task) =>
        task.overdue
    );

  if (overdue.length) {
    signals.push(
      signalCard(
        "deadline",
        "Overdue exposure",
        "Visible work has passed its recorded due time.",
        overdue.length,
        overdue[0].task_id
      )
    );
  }

  const noEvidence =
    visible.filter(
      (task) =>
        task.status
        === "completed"
        && !(
          task.evidence_receipts
          || []
        ).length
    );

  if (noEvidence.length) {
    signals.push(
      signalCard(
        "evidence",
        "Completion evidence gap",
        "Completed tasks without visible evidence receipts require review.",
        noEvidence.length,
        noEvidence[0].task_id
      )
    );
  }

  const highFanOut =
    visible
      .filter(
        (task) =>
          Number(
            task.fan_out
            || 0
          ) >= 3
      )
      .sort(
        (a, b) =>
          Number(
            b.fan_out
            || 0
          )
          -
          Number(
            a.fan_out
            || 0
          )
      );

  if (highFanOut.length) {
    signals.push(
      signalCard(
        "leverage",
        "High-leverage dependency",
        "Completing this work may unlock multiple downstream tasks.",
        highFanOut[0].fan_out,
        highFanOut[0].task_id
      )
    );
  }

  const deferredCritical =
    visible.filter(
      (task) =>
        task.priority
        === "critical"
        && task.status
        === "deferred"
    );

  if (deferredCritical.length) {
    signals.push(
      signalCard(
        "conflict",
        "Critical work deferred",
        "Critical priority and deferred execution state are simultaneously recorded.",
        deferredCritical.length,
        deferredCritical[0].task_id
      )
    );
  }

  const unassigned =
    visible.filter(
      (task) =>
        isReady(task)
        && !task.assignee
    );

  if (unassigned.length) {
    signals.push(
      signalCard(
        "capacity",
        "Ready and unassigned",
        "Executable tasks currently have no assignee.",
        unassigned.length,
        unassigned[0].task_id
      )
    );
  }

  const large =
    visible.filter(
      (task) =>
        Number(
          task.estimate_minutes
          || 0
        ) >= 120
        && taskDepth(task)
        >= 3
        && !terminalStates.has(
          task.status
        )
    );

  if (large.length) {
    signals.push(
      signalCard(
        "decomposition",
        "Large execution unit",
        "A deep task carries a large estimate and may benefit from existing decomposition machinery.",
        large.length,
        large[0].task_id
      )
    );
  }

  const staleBlockers =
    blocked.filter(
      (task) =>
        !(
          task.blockers
          || []
        ).length
        && !(
          task.unsatisfied_dependencies
          || []
        ).length
    );

  if (staleBlockers.length) {
    signals.push(
      signalCard(
        "consistency",
        "Blocked state without cause",
        "A task is marked blocked without a visible blocker or unsatisfied dependency.",
        staleBlockers.length,
        staleBlockers[0].task_id
      )
    );
  }

  if (!signals.length) {
    signals.push(
      signalCard(
        "clear",
        "No derived warnings",
        "The current filtered task surface exposes no deterministic warning conditions.",
        0
      )
    );
  }

  return signals;
}

function renderSignals() {
  $("#signalGrid")
    .innerHTML =
      deriveSignals()
        .join("");
}

function renderHistory() {
  const events =
    [
      ...(
        state.payload
        ?.history_tail
        || []
      ),
    ]
      .reverse();

  $("#historyTimeline")
    .innerHTML =
      events.length
        ? events
          .map(
            (event) => `
              <article
                class="history-event"
                data-task="${esc(event.task_id)}">

                <time>
                  ${esc(
                    fmtDate(
                      event.created_at
                    )
                  )}
                </time>

                <span class="history-dot">
                </span>

                <div>

                  <strong>
                    ${esc(
                      nice(
                        event.event_type
                      )
                    )}
                  </strong>

                  <code>
                    ${esc(event.task_id)}
                  </code>

                  <p>
                    ${esc(
                      event.previous_state
                      || "∅"
                    )}
                    →
                    ${esc(
                      event.new_state
                      || event.previous_state
                      || "∅"
                    )}
                  </p>

                </div>

              </article>
            `
          )
          .join("")
        : empty(
            "No immutable history events are visible."
          );
}

function populateFilters() {
  const systems =
    new Set();

  const workstreams =
    new Set();

  tasks().forEach(
    (task) => {
      systems.add(
        taskSystem(task)
      );

      workstreams.add(
        taskWorkstream(task)
      );
    }
  );

  replaceOptions(
    "#systemFilter",
    systems,
    state.system
  );

  replaceOptions(
    "#workstreamFilter",
    workstreams,
    state.workstream
  );
}

function replaceOptions(
  selector,
  values,
  selected
) {
  const element =
    $(selector);

  const first =
    element.options[0]
      .outerHTML;

  element.innerHTML =
    first
    + [...values]
      .sort()
      .map(
        (value) => `
          <option value="${esc(value)}">
            ${esc(value)}
          </option>
        `
      )
      .join("");

  element.value =
    selected || "";
}

function renderHealth() {
  const healthy =
    state.health
    ?.healthy
    === true;

  const historyValid =
    state.health
    ?.history_chain_valid
    !== false;

  const cycleFree =
    state.health
    ?.cycle_free
    !== false;

  $("#engineHealth")
    .className =
      `engine-health ${
        healthy
          ? "good"
          : "warn"
      }`;

  $("#engineHealth")
    .innerHTML = `
      <div>
        <span class="health-light">
        </span>

        <strong>
          ${
            healthy
              ? "Niche healthy"
              : "Niche attention"
          }
        </strong>
      </div>

      <span>
        ${tasks().length}
        authoritative task primitives
      </span>

      <span>
        ${
          historyValid
            ? "history chain valid"
            : "history chain invalid"
        }
      </span>

      <span>
        ${
          cycleFree
            ? "dependency graph acyclic"
            : "dependency cycle detected"
        }
      </span>
    `;
}

function renderMeta() {
  $("#updatedAt")
    .textContent =
      state.lastLoaded
        ? state.lastLoaded
          .toLocaleString()
        : "";

  const digest =
    graph().digest
    || "";

  $("#graphDigest")
    .textContent =
      digest
        ? digest.slice(
            0,
            20
          )
        : "live";
}

function renderDepth() {
  $$("[data-depth]")
    .forEach(
      (button) =>
        button.classList.toggle(
          "active",
          Number(
            button.dataset.depth
          )
          === state.depth
        )
    );
}

function render() {
  if (!state.payload) {
    return;
  }

  populateFilters();
  renderDepth();
  renderHealth();
  renderMeta();
  renderCockpit();
  renderFocus();
  renderMatrix();
  renderTopology();
  renderSignals();
  renderHistory();

  if (state.selected) {
    const task =
      tasks().find(
        (candidate) =>
          candidate.task_id
          === state.selected
      );

    if (task) {
      openInspector(
        task,
        false
      );
    }
  }
}

function inspectorSection(
  label,
  content
) {
  return `
    <section class="inspector-section">

      <span class="eyebrow">
        ${esc(label)}
      </span>

      ${content}

    </section>
  `;
}

function list(values) {
  if (
    !values
    || !values.length
  ) {
    return `
      <span class="muted">
        none
      </span>
    `;
  }

  return `
    <ul class="inspector-list">
      ${
        values
          .map(
            (value) => `
              <li>
                <code>
                  ${esc(value)}
                </code>
              </li>
            `
          )
          .join("")
      }
    </ul>
  `;
}

function openInspector(
  task,
  show = true
) {
  state.selected =
    task.task_id;

  $("#inspectorId")
    .textContent =
      task.task_id;

  $("#inspectorTitle")
    .textContent =
      taskTitle(task);

  const unsatisfied =
    task.unsatisfied_dependencies
    || [];

  const receipts =
    task.evidence_receipts
    || [];

  $("#inspectorBody")
    .innerHTML =
      inspectorSection(
        "Execution",
        `
          <div class="inspector-grid">

            <div>
              <small>Status</small>
              <strong>
                ${esc(task.status)}
              </strong>
            </div>

            <div>
              <small>Priority</small>
              <strong>
                ${esc(task.priority)}
              </strong>
            </div>

            <div>
              <small>System</small>
              <strong>
                ${esc(taskSystem(task))}
              </strong>
            </div>

            <div>
              <small>Workstream</small>
              <strong>
                ${esc(taskWorkstream(task))}
              </strong>
            </div>

            <div>
              <small>Depth</small>
              <strong>
                ${taskDepth(task)}
              </strong>
            </div>

            <div>
              <small>Risk</small>
              <strong>
                ${esc(taskRisk(task))}
              </strong>
            </div>

            <div>
              <small>Horizon</small>
              <strong>
                ${esc(taskHorizon(task))}
              </strong>
            </div>

            <div>
              <small>Estimate</small>
              <strong>
                ${esc(task.estimate_minutes || 0)}
                min
              </strong>
            </div>

          </div>
        `
      )
      + inspectorSection(
          "Actions",
          `
            <div class="inspector-actions">

              ${
                isReady(task)
                  ? `
                    <button
                      class="command-button primary"
                      data-start="${esc(task.task_id)}">
                      Start
                    </button>
                  `
                  : ""
              }

              ${
                task.status
                !== "completed"
                  ? `
                    <button
                      class="command-button secondary"
                      data-complete="${esc(task.task_id)}">
                      Complete
                    </button>
                  `
                  : ""
              }

              <button
                class="command-button secondary"
                data-copy="${esc(task.task_id)}">
                Copy ID
              </button>

            </div>
          `
        )
      + inspectorSection(
          "Purpose",
          `
            <p>
              ${esc(task.purpose)}
            </p>
          `
        )
      + inspectorSection(
          "Completion condition",
          `
            <p>
              ${esc(
                task.completion_condition
              )}
            </p>
          `
        )
      + inspectorSection(
          "Dependencies",
          list(
            task.dependencies
          )
        )
      + inspectorSection(
          "Unsatisfied dependencies",
          list(
            unsatisfied
          )
        )
      + inspectorSection(
          "Dependents",
          list(
            task.dependents
          )
        )
      + inspectorSection(
          "Blockers",
          list(
            task.blockers
          )
        )
      + inspectorSection(
          "Evidence receipts",
          list(
            receipts
          )
        )
      + inspectorSection(
          "Implementation references",
          list(
            task.implementation_references
          )
        )
      + inspectorSection(
          "Authority basis",
          list(
            task.authority_basis
          )
        )
      + inspectorSection(
          "Compatibility obligations",
          list(
            task.compatibility_obligations
          )
        );

  if (show) {
    $("#inspector")
      .classList
      .remove("hidden");

    $("#scrim")
      .classList
      .remove("hidden");
  }
}

function closeInspector() {
  state.selected =
    null;

  $("#inspector")
    .classList
    .add("hidden");

  $("#scrim")
    .classList
    .add("hidden");
}

async function transition(
  taskId,
  status,
  receipts = []
) {
  await api(
    (
      "/api/tasks/"
      + encodeURIComponent(
          taskId
        )
      + "/transition"
    ),
    {
      method: "POST",

      body:
        JSON.stringify(
          {
            state: status,
            receipts,
          }
        ),
    }
  );

  await load();
}

async function startTask(
  taskId
) {
  try {
    await transition(
      taskId,
      "active"
    );

    toast(
      "Task activated"
    );

  } catch (error) {
    toast(
      error.message
    );
  }
}

async function completeTask(
  taskId
) {
  const receipt =
    window.prompt(
      "Evidence or receipt reference required:"
    );

  if (!receipt) {
    return;
  }

  try {
    await transition(
      taskId,
      "completed",
      [
        receipt,
      ]
    );

    toast(
      "Task completed"
    );

  } catch (error) {
    toast(
      error.message
    );
  }
}

function setView(view) {
  state.view =
    view;

  $$(".command-view")
    .forEach(
      (element) =>
        element.classList.remove(
          "active"
        )
    );

  const target =
    $(
      `#${view}View`
    );

  if (target) {
    target.classList.add(
      "active"
    );
  }

  $$(".command-nav-item")
    .forEach(
      (button) =>
        button.classList.toggle(
          "active",
          button.dataset.view
          === view
        )
    );
}

function openPalette() {
  $("#commandPalette")
    .showModal();

  $("#paletteInput")
    .value = "";

  renderPalette("");

  window.setTimeout(
    () =>
      $("#paletteInput")
        .focus(),
    0
  );
}

function closePalette() {
  $("#commandPalette")
    .close();
}

function paletteCommands() {
  return [
    {
      id: "view-cockpit",
      title: "Open cockpit",
      hint: "1",
      action:
        () =>
          setView(
            "cockpit"
          ),
    },
    {
      id: "view-focus",
      title: "Open focus queue",
      hint: "2",
      action:
        () =>
          setView(
            "focus"
          ),
    },
    {
      id: "view-matrix",
      title: "Open work matrix",
      hint: "3",
      action:
        () =>
          setView(
            "matrix"
          ),
    },
    {
      id: "view-topology",
      title: "Open topology",
      hint: "4",
      action:
        () =>
          setView(
            "topology"
          ),
    },
    {
      id: "view-signals",
      title: "Open signals",
      hint: "5",
      action:
        () =>
          setView(
            "signals"
          ),
    },
    {
      id: "view-history",
      title: "Open history",
      hint: "6",
      action:
        () =>
          setView(
            "history"
          ),
    },
    {
      id: "refresh",
      title: "Refresh Niche state",
      hint: "R",
      action: load,
    },
  ];
}

function renderPalette(query) {
  const normalized =
    query
      .trim()
      .toLowerCase();

  const commands =
    paletteCommands()
      .filter(
        (command) =>
          !normalized
          || command.title
            .toLowerCase()
            .includes(
              normalized
            )
      );

  const taskResults =
    tasks()
      .filter(
        (task) =>
          !normalized
          || [
            task.task_id,
            taskTitle(task),
            taskSystem(task),
            taskWorkstream(task),
          ]
            .join(" ")
            .toLowerCase()
            .includes(
              normalized
            )
      )
      .slice(
        0,
        20
      );

  $("#paletteResults")
    .innerHTML =
      commands
        .map(
          (command) => `
            <button
              class="palette-row"
              data-command="${esc(command.id)}">

              <span>
                ${esc(command.title)}
              </span>

              <kbd>
                ${esc(command.hint)}
              </kbd>

            </button>
          `
        )
        .join("")
      + taskResults
        .map(
          (task) => `
            <button
              class="palette-row"
              data-palette-task="${esc(task.task_id)}">

              <span>
                <strong>
                  ${esc(taskTitle(task))}
                </strong>

                <small>
                  ${esc(taskSystem(task))}
                  ·
                  ${esc(task.status)}
                </small>
              </span>

              <span class="palette-task-mark">
                task
              </span>

            </button>
          `
        )
        .join("");
}

function applyTopologyScale() {
  $("#topologySvg")
    .style.transform =
      `scale(${state.topologyScale})`;
}

function toast(message) {
  const element =
    $("#toast");

  element.textContent =
    message;

  element.classList.add(
    "show"
  );

  window.clearTimeout(
    toast.timer
  );

  toast.timer =
    window.setTimeout(
      () =>
        element.classList.remove(
          "show"
        ),
      2400
    );
}

toast.timer = null;

document.addEventListener(
  "click",
  (event) => {
    const taskElement =
      event.target.closest(
        "[data-task]"
      );

    if (taskElement) {
      const task =
        tasks().find(
          (candidate) =>
            candidate.task_id
            === taskElement.dataset.task
        );

      if (task) {
        openInspector(task);
      }
    }

    const start =
      event.target.closest(
        "[data-start]"
      );

    if (start) {
      event.stopPropagation();

      startTask(
        start.dataset.start
      );
    }

    const complete =
      event.target.closest(
        "[data-complete]"
      );

    if (complete) {
      event.stopPropagation();

      completeTask(
        complete.dataset.complete
      );
    }

    const copy =
      event.target.closest(
        "[data-copy]"
      );

    if (copy) {
      event.stopPropagation();

      navigator.clipboard
        ?.writeText(
          copy.dataset.copy
        )
        .then(
          () =>
            toast(
              "Task ID copied"
            )
        );
    }

    const command =
      event.target.closest(
        "[data-command]"
      );

    if (command) {
      const item =
        paletteCommands()
          .find(
            (candidate) =>
              candidate.id
              === command.dataset.command
          );

      if (item) {
        closePalette();
        item.action();
      }
    }

    const paletteTask =
      event.target.closest(
        "[data-palette-task]"
      );

    if (paletteTask) {
      const task =
        tasks().find(
          (candidate) =>
            candidate.task_id
            === paletteTask
              .dataset
              .paletteTask
        );

      closePalette();

      if (task) {
        openInspector(task);
      }
    }
  }
);

$$(".command-nav-item")
  .forEach(
    (button) =>
      button.addEventListener(
        "click",
        () =>
          setView(
            button.dataset.view
          )
      )
  );

$$("[data-depth]")
  .forEach(
    (button) =>
      button.addEventListener(
        "click",
        () => {
          state.depth =
            Number(
              button.dataset.depth
            );

          render();
        }
      )
  );

$("#refresh")
  .addEventListener(
    "click",
    load
  );

$("#commandButton")
  .addEventListener(
    "click",
    openPalette
  );

$("#closeInspector")
  .addEventListener(
    "click",
    closeInspector
  );

$("#scrim")
  .addEventListener(
    "click",
    closeInspector
  );

$("#focusFirst")
  .addEventListener(
    "click",
    () => {
      const first =
        readyQueue()[0];

      if (first) {
        openInspector(first);
      }
    }
  );

$("#search")
  .addEventListener(
    "input",
    (event) => {
      state.query =
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

$("#paletteInput")
  .addEventListener(
    "input",
    (event) =>
      renderPalette(
        event.target.value
      )
  );

$("#zoomIn")
  .addEventListener(
    "click",
    () => {
      state.topologyScale =
        Math.min(
          2,
          state.topologyScale
          + 0.1
        );

      applyTopologyScale();
    }
  );

$("#zoomOut")
  .addEventListener(
    "click",
    () => {
      state.topologyScale =
        Math.max(
          0.5,
          state.topologyScale
          - 0.1
        );

      applyTopologyScale();
    }
  );

$("#zoomReset")
  .addEventListener(
    "click",
    () => {
      state.topologyScale = 1;

      applyTopologyScale();
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
        document.activeElement
        ?.tagName
      );

    if (
      (
        event.ctrlKey
        || event.metaKey
      )
      && event.key
        .toLowerCase()
        === "k"
    ) {
      event.preventDefault();
      openPalette();
      return;
    }

    if (
      event.key === "/"
      && !editing
    ) {
      event.preventDefault();

      $("#search")
        .focus();

      return;
    }

    if (
      event.key === "Escape"
    ) {
      closeInspector();

      if (
        $("#commandPalette")
          .open
      ) {
        closePalette();
      }

      return;
    }

    if (editing) {
      return;
    }

    const views = {
      "1": "cockpit",
      "2": "focus",
      "3": "matrix",
      "4": "topology",
      "5": "signals",
      "6": "history",
    };

    if (views[event.key]) {
      setView(
        views[event.key]
      );
    }

    if (
      event.key
        .toLowerCase()
        === "r"
    ) {
      load();
    }
  }
);

document.addEventListener(
  "visibilitychange",
  () => {
    if (
      !document.hidden
      && state.lastLoaded
      && (
        Date.now()
        - state.lastLoaded.getTime()
      ) > 15000
    ) {
      load();
    }
  }
);

load();

window.setInterval(
  () => {
    if (!document.hidden) {
      load();
    }
  },
  15000
);
