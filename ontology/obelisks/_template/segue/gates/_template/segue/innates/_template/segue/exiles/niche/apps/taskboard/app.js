"use strict";

const state = {
  tasks: [],
  dashboard: null,
  masterplan: null,
  masterplanIntegrity: null,
  engineState: null,
  living: null,
  fabric: null,
  history: [],
  selectedTask: null,
  selectedSurface: null,
  activeView: "execute",
  flowFilter: "all",
  refreshTimer: null,
  lastFabricHash: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const first = (...values) => values.find(
  (value) => value !== undefined && value !== null && value !== ""
);

const array = (value) => Array.isArray(value) ? value : [];

const object = (value) => (
  value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {}
);

const taskId = (task) => String(
  first(task.id, task.task_id, task.key, "unknown")
);

const taskTitle = (task) => String(
  first(task.title, task.name, task.summary, taskId(task))
);

const taskPurpose = (task) => String(
  first(
    task.purpose,
    task.description,
    task.objective,
    task.completion_condition,
    ""
  )
);

const taskStatus = (task) => String(
  first(task.status, task.state, "unknown")
).toLowerCase();

const taskPriority = (task) => String(
  first(task.priority, "unknown")
).toLowerCase();

const taskDependencies = (task) => array(
  first(
    task.dependencies,
    task.depends_on,
    task.prerequisites,
    []
  )
);

const taskDependents = (task) => array(
  first(
    task.dependents,
    task.unlocks,
    []
  )
);

const taskReceipts = (task) => array(
  first(task.receipts, task.evidence, [])
);

const isTerminal = (task) => {
  const status = taskStatus(task);
  return [
    "complete",
    "completed",
    "done",
    "closed",
    "cancelled",
    "canceled",
    "rejected",
    "skipped",
  ].includes(status);
};

const isBlocked = (task) => {
  const status = taskStatus(task);

  if (status.includes("block")) {
    return true;
  }

  return Boolean(
    first(
      task.blocked,
      task.is_blocked,
      false
    )
  );
};

const isActive = (task) => {
  const status = taskStatus(task);

  return [
    "active",
    "in_progress",
    "in-progress",
    "doing",
    "started",
    "leased",
  ].includes(status);
};

const isReady = (task) => {
  if (isTerminal(task) || isBlocked(task) || isActive(task)) {
    return false;
  }

  if (
    task.ready === true ||
    task.is_ready === true
  ) {
    return true;
  }

  const status = taskStatus(task);

  if ([
    "ready",
    "open",
    "todo",
    "pending",
    "queued",
  ].includes(status)) {
    return true;
  }

  const dependencies = taskDependencies(task);

  if (!dependencies.length) {
    return status !== "unknown";
  }

  return dependencies.every((dependency) => {
    const dependencyId = (
      typeof dependency === "object"
        ? first(dependency.id, dependency.task_id)
        : dependency
    );

    const prerequisite = state.tasks.find(
      (candidate) => taskId(candidate) === String(dependencyId)
    );

    return prerequisite ? isTerminal(prerequisite) : false;
  });
};

const taskVisualState = (task) => {
  if (isTerminal(task)) return "complete";
  if (isBlocked(task)) return "blocked";
  if (isActive(task)) return "active";
  if (isReady(task)) return "ready";
  return "future";
};

const priorityRank = (task) => {
  const priority = taskPriority(task);

  const ranks = {
    critical: 100,
    urgent: 95,
    highest: 90,
    high: 80,
    p0: 100,
    p1: 80,
    medium: 60,
    normal: 50,
    p2: 60,
    low: 30,
    p3: 30,
    lowest: 10,
    p4: 10,
  };

  if (priority in ranks) {
    return ranks[priority];
  }

  const numeric = Number(priority);

  if (Number.isFinite(numeric)) {
    return Math.max(0, 100 - numeric * 10);
  }

  return 50;
};

const descendantUnlockCount = (task) => {
  const direct = taskDependents(task);

  if (direct.length) {
    return direct.length;
  }

  const id = taskId(task);

  return state.tasks.filter(
    (candidate) => taskDependencies(candidate).some((dependency) => {
      const dependencyId = (
        typeof dependency === "object"
          ? first(dependency.id, dependency.task_id)
          : dependency
      );

      return String(dependencyId) === id;
    })
  ).length;
};

const selectNextTask = () => {
  const ready = state.tasks.filter(isReady);

  ready.sort((a, b) => {
    const priorityDifference = priorityRank(b) - priorityRank(a);

    if (priorityDifference) {
      return priorityDifference;
    }

    const unlockDifference = (
      descendantUnlockCount(b) - descendantUnlockCount(a)
    );

    if (unlockDifference) {
      return unlockDifference;
    }

    return taskId(a).localeCompare(taskId(b));
  });

  return ready[0] ?? null;
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    headers: {
      "Accept": "application/json",
      ...(options.body ? {"Content-Type": "application/json"} : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json();

  if (!response.ok) {
    throw new Error(
      first(payload.error, payload.message, `HTTP ${response.status}`)
    );
  }

  return payload;
}

async function loadCore() {
  const results = await Promise.allSettled([
    api("/api/tasks?include_terminal=true"),
    api("/api/dashboard"),
    api("/api/masterplan/summary"),
    api("/api/masterplan/integrity"),
    api("/api/state"),
    api("/api/living"),
    api("/api/living/fabric"),
    api("/api/history"),
  ]);

  const [
    tasksResult,
    dashboardResult,
    masterplanResult,
    masterplanIntegrityResult,
    engineResult,
    livingResult,
    fabricResult,
    historyResult,
  ] = results;

  if (tasksResult.status === "fulfilled") {
    state.tasks = array(tasksResult.value.tasks);
  }

  if (dashboardResult.status === "fulfilled") {
    state.dashboard = dashboardResult.value;
  }

  if (masterplanResult.status === "fulfilled") {
    state.masterplan = masterplanResult.value;
  }

  if (masterplanIntegrityResult.status === "fulfilled") {
    state.masterplanIntegrity = masterplanIntegrityResult.value;
  }

  if (engineResult.status === "fulfilled") {
    state.engineState = engineResult.value;
  }

  if (livingResult.status === "fulfilled") {
    state.living = livingResult.value;
  }

  if (fabricResult.status === "fulfilled") {
    state.fabric = fabricResult.value;
  }

  if (historyResult.status === "fulfilled") {
    state.history = array(historyResult.value.events);
  }

  const successful = results.filter(
    (result) => result.status === "fulfilled"
  ).length;

  setConnection(
    successful > 0 ? "online" : "offline",
    successful > 0 ? "live" : "offline"
  );

  renderAll();

  $("#lastRefresh").textContent = new Date().toLocaleTimeString();
}

function setConnection(status, label) {
  const indicator = $("#connectionIndicator");
  indicator.dataset.state = status;
  $("#connectionLabel").textContent = label;
}


function renderMasterplanIntegrityStatus() {
  const projection =
    document.querySelector("#projection-status");

  if (!projection) {
    return;
  }

  const integrity =
    state.masterplanIntegrity &&
    typeof state.masterplanIntegrity === "object"
      ? state.masterplanIntegrity
      : null;

  if (!integrity) {
    return;
  }

  const graphDigest =
    typeof integrity.source_graph_digest === "string"
      ? integrity.source_graph_digest.slice(0, 12)
      : null;

  const identityCount =
    Number.isFinite(integrity.identity_count)
      ? integrity.identity_count
      : null;

  const lineageCount =
    Number.isFinite(integrity.lineage_count)
      ? integrity.lineage_count
      : null;

  const duplicateCount =
    Number.isFinite(
      integrity.duplicate_identity_group_count
    )
      ? integrity.duplicate_identity_group_count
      : null;

  const components = [
    "masterplan linked",
    graphDigest
      ? `graph ${graphDigest}`
      : null,
    identityCount !== null
      ? `${identityCount} identities`
      : null,
    lineageCount !== null
      ? `${lineageCount} lineage records`
      : null,
    duplicateCount !== null
      ? `${duplicateCount} duplicate identity groups`
      : null,
  ].filter(Boolean);

  const masterplanLabel =
    components.join(" · ");

  const existing =
    typeof projection.textContent === "string"
      ? projection.textContent.trim()
      : "";

  if (
    existing.includes(
      "masterplan linked"
    )
  ) {
    return;
  }

  projection.textContent =
    existing
      ? `${existing} · ${masterplanLabel}`
      : masterplanLabel;
}

function renderAll() {
  renderStatus();
  renderExecute();
  renderFlow();
  renderObjectives();
  renderTimeline();
  renderEvidence();
  renderLiving();
  renderHistory();

  if (state.activeView === "constellation") {
    renderConstellation();
  }

  renderMasterplanIntegrityStatus();
}

function renderStatus() {
  const ready = state.tasks.filter(isReady).length;
  const active = state.tasks.filter(isActive).length;
  const blocked = state.tasks.filter(isBlocked).length;

  $("#readyCount").textContent = ready;
  $("#activeCount").textContent = active;
  $("#blockedCount").textContent = blocked;

  $("#taskEngineStatus").textContent = (
    state.engineState ? "available" : "unknown"
  );

  const fabric = object(state.fabric);

  $("#fabricStatus").textContent = (
    fabric.present === false
      ? "absent"
      : fabric.healthy === true
        ? "healthy"
        : fabric.healthy === false
          ? "degraded"
          : fabric.present
            ? "present"
            : "unknown"
  );

  $("#surfaceCount").textContent = first(
    fabric.surface_count,
    Object.keys(object(fabric.surfaces)).length,
    0
  );
}

function renderExecute() {
  const task = selectNextTask();

  const panel = $("#nextTaskPanel");
  const start = $("#startNextButton");
  const why = $("#whyButton");
  const dependencies = $("#dependenciesButton");
  const impact = $("#impactButton");

  if (!task) {
    panel.innerHTML = `
      <div class="next-task">
        <div class="task-kicker">NO EXECUTABLE TASK RESOLVED</div>
        <div class="task-title">The frontier is quiet.</div>
        <p class="task-purpose">
          Niche cannot currently resolve a ready task from the task state
          available to this projection.
        </p>
      </div>
    `;

    $("#frontierState").textContent = "no ready task";

    [start, why, dependencies, impact].forEach(
      (button) => button.disabled = true
    );

    $("#oracleBody").innerHTML = `
      <p class="muted">
        No recommendation is being fabricated. The task engine state does not
        currently expose a task Niche can legitimately classify as ready.
      </p>
    `;

    $("#unlockHorizon").innerHTML = `
      <p class="muted">No executable task selected.</p>
    `;

    renderBlockers();
    renderFrontier();
    return;
  }

  state.selectedTask = state.selectedTask ?? task;

  const id = taskId(task);
  const status = taskStatus(task);
  const priority = taskPriority(task);
  const dependencyCount = taskDependencies(task).length;
  const unlockCount = descendantUnlockCount(task);

  panel.innerHTML = `
    <article class="next-task" data-task-id="${escapeHtml(id)}">
      <div class="task-kicker">
        <span>${escapeHtml(id)}</span>
        <span>•</span>
        <span>${escapeHtml(status)}</span>
      </div>

      <div class="task-title">${escapeHtml(taskTitle(task))}</div>

      <p class="task-purpose">
        ${escapeHtml(
          taskPurpose(task) ||
          "No purpose text is exposed by the current task record."
        )}
      </p>

      <div class="task-metrics">
        <div class="task-metric">
          <span>Priority</span>
          <strong>${escapeHtml(priority)}</strong>
        </div>

        <div class="task-metric">
          <span>Dependencies</span>
          <strong>${dependencyCount}</strong>
        </div>

        <div class="task-metric">
          <span>Direct unlocks</span>
          <strong>${unlockCount}</strong>
        </div>

        <div class="task-metric">
          <span>Readiness</span>
          <strong>ready</strong>
        </div>

        <div class="task-metric">
          <span>Projection</span>
          <strong>niche</strong>
        </div>
      </div>
    </article>
  `;

  $("#frontierState").textContent = "frontier resolved";
  $("#startNextLabel").textContent = (
    isActive(task) ? "CONTINUE" : "START NEXT"
  );

  [start, why, dependencies, impact].forEach(
    (button) => button.disabled = false
  );

  renderOracle(task);
  renderUnlockHorizon(task);
  renderBlockers();
  renderFrontier(task);
}

function renderOracle(task) {
  const dependencyCount = taskDependencies(task).length;
  const unlocks = descendantUnlockCount(task);
  const priority = priorityRank(task);

  const factors = [
    {
      name: "authoritative priority",
      value: priority,
      label: taskPriority(task),
    },
    {
      name: "dependency readiness",
      value: isReady(task) ? 100 : 0,
      label: isReady(task) ? "ready" : "constrained",
    },
    {
      name: "blocker state",
      value: isBlocked(task) ? 0 : 100,
      label: isBlocked(task) ? "blocked" : "clear",
    },
    {
      name: "downstream unlock",
      value: Math.min(100, unlocks * 20),
      label: String(unlocks),
    },
    {
      name: "prerequisites",
      value: dependencyCount ? 70 : 100,
      label: String(dependencyCount),
    },
  ];

  $("#oracleBody").innerHTML = factors.map((factor) => `
    <div class="oracle-factor">
      <div class="oracle-factor-head">
        <span>${escapeHtml(factor.name)}</span>
        <span>${escapeHtml(factor.label)}</span>
      </div>
      <div class="factor-track">
        <div
          class="factor-fill"
          style="width:${Math.max(0, Math.min(100, factor.value))}%"
        ></div>
      </div>
    </div>
  `).join("") + `
    <p class="muted" style="margin-top:16px">
      Recommendation uses only fields currently exposed to Niche.
      Missing ranking dimensions remain absent rather than inferred as authority.
    </p>
  `;
}

function relatedDependents(task) {
  const explicit = taskDependents(task);

  if (explicit.length) {
    return explicit.map((entry) => {
      const id = (
        typeof entry === "object"
          ? first(entry.id, entry.task_id)
          : entry
      );

      return state.tasks.find(
        (candidate) => taskId(candidate) === String(id)
      ) ?? {id, title: id};
    });
  }

  const id = taskId(task);

  return state.tasks.filter(
    (candidate) => taskDependencies(candidate).some((dependency) => {
      const dependencyId = (
        typeof dependency === "object"
          ? first(dependency.id, dependency.task_id)
          : dependency
      );

      return String(dependencyId) === id;
    })
  );
}

function renderUnlockHorizon(task) {
  const dependents = relatedDependents(task);

  if (!dependents.length) {
    $("#unlockHorizon").innerHTML = `
      <p class="muted">
        No direct downstream task relationship is exposed.
      </p>
    `;
    return;
  }

  $("#unlockHorizon").innerHTML = dependents.slice(0, 7).map(
    (dependent) => `
      <div class="stack-item" data-open-task="${escapeHtml(taskId(dependent))}">
        <strong>${escapeHtml(taskTitle(dependent))}</strong>
        <small>
          ${escapeHtml(taskId(dependent))}
          · ${escapeHtml(taskVisualState(dependent))}
        </small>
      </div>
    `
  ).join("");
}

function renderBlockers() {
  const blockers = state.tasks
    .filter(isBlocked)
    .map((task) => ({
      task,
      weight: descendantUnlockCount(task),
    }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 7);

  if (!blockers.length) {
    $("#blockerRadar").innerHTML = `
      <p class="muted">No blocked tasks are exposed in current state.</p>
    `;
    return;
  }

  $("#blockerRadar").innerHTML = blockers.map(({task, weight}) => `
    <div class="stack-item" data-open-task="${escapeHtml(taskId(task))}">
      <strong>${escapeHtml(taskTitle(task))}</strong>
      <small>
        ${escapeHtml(taskId(task))}
        · downstream weight ${weight}
      </small>
    </div>
  `).join("");
}

function graphTasks(limit = 45) {
  const important = [...state.tasks].sort((a, b) => {
    const stateWeight = {
      active: 100,
      ready: 90,
      blocked: 80,
      future: 40,
      complete: 20,
    };

    return (
      stateWeight[taskVisualState(b)] -
      stateWeight[taskVisualState(a)]
    ) || (
      priorityRank(b) - priorityRank(a)
    );
  });

  return important.slice(0, limit);
}

function renderFrontier(focusTask = null) {
  const svg = $("#frontierSvg");
  const tasks = graphTasks(24);

  drawGraph(svg, tasks, {
    compact: true,
    focusId: focusTask ? taskId(focusTask) : null,
  });
}

function renderConstellation() {
  const svg = $("#constellationSvg");

  drawGraph(svg, graphTasks(70), {
    compact: false,
    focusId: state.selectedTask ? taskId(state.selectedTask) : null,
  });
}

function drawGraph(svg, tasks, options = {}) {
  const width = Math.max(
    600,
    svg.parentElement?.clientWidth || 900
  );

  const height = options.compact
    ? 330
    : Math.max(520, svg.parentElement?.clientHeight || 650);

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const ids = new Set(tasks.map(taskId));

  const columns = options.compact ? 5 : 8;
  const horizontal = width / (columns + 1);
  const rows = Math.ceil(tasks.length / columns);
  const vertical = height / (rows + 1);

  const positions = new Map();

  tasks.forEach((task, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);

    positions.set(taskId(task), {
      x: horizontal * (column + 1),
      y: vertical * (row + 1),
    });
  });

  const edges = [];

  tasks.forEach((task) => {
    const target = positions.get(taskId(task));

    taskDependencies(task).forEach((dependency) => {
      const dependencyId = String(
        typeof dependency === "object"
          ? first(dependency.id, dependency.task_id, "")
          : dependency
      );

      if (!ids.has(dependencyId)) {
        return;
      }

      const source = positions.get(dependencyId);

      if (!source || !target) {
        return;
      }

      edges.push(`
        <path
          class="graph-edge ${
            options.focusId === taskId(task) ||
            options.focusId === dependencyId
              ? "active"
              : ""
          }"
          d="M ${source.x} ${source.y}
             C ${(source.x + target.x) / 2} ${source.y},
               ${(source.x + target.x) / 2} ${target.y},
               ${target.x} ${target.y}"
        />
      `);
    });
  });

  const nodes = tasks.map((task) => {
    const id = taskId(task);
    const point = positions.get(id);
    const visualState = taskVisualState(task);
    const radius = (
      options.focusId === id
        ? 12
        : visualState === "ready"
          ? 9
          : 7
    );

    const label = taskTitle(task);
    const truncated = (
      label.length > 26
        ? `${label.slice(0, 25)}…`
        : label
    );

    return `
      <g
        class="graph-node"
        data-task-node="${escapeHtml(id)}"
        data-state="${escapeHtml(visualState)}"
        transform="translate(${point.x},${point.y})"
      >
        <circle r="${radius}"></circle>
        <text x="15" y="3">${escapeHtml(truncated)}</text>
      </g>
    `;
  });

  svg.innerHTML = `
    <g class="graph-edges">${edges.join("")}</g>
    <g class="graph-nodes">${nodes.join("")}</g>
  `;
}

function flowLane(task) {
  if (isTerminal(task)) return "complete";
  if (isBlocked(task)) return "blocked";
  if (isActive(task)) return "active";
  if (isReady(task)) return "ready";

  const status = taskStatus(task);

  if (
    status.includes("review") ||
    status.includes("evidence") ||
    status.includes("verify")
  ) {
    return "review";
  }

  return "waiting";
}

function renderFlow() {
  const definitions = [
    ["ready", "Ready"],
    ["active", "Active"],
    ["blocked", "Blocked"],
    ["waiting", "Waiting"],
    ["review", "Evidence"],
    ["complete", "Complete"],
  ];

  let tasks = state.tasks;

  if (state.flowFilter !== "all") {
    tasks = tasks.filter(
      (task) => flowLane(task) === state.flowFilter
    );
  }

  $("#flowBoard").innerHTML = definitions.map(([key, label]) => {
    const laneTasks = tasks.filter(
      (task) => flowLane(task) === key
    );

    return `
      <section class="flow-lane" data-lane="${key}">
        <div class="flow-lane-header">
          <span>${label}</span>
          <span>${laneTasks.length}</span>
        </div>

        <div class="flow-cards">
          ${laneTasks.map(renderTaskCard).join("")}
        </div>
      </section>
    `;
  }).join("");
}

function renderTaskCard(task) {
  const id = taskId(task);

  return `
    <article
      class="task-card"
      tabindex="0"
      data-open-task="${escapeHtml(id)}"
      data-state="${escapeHtml(taskVisualState(task))}"
    >
      <div class="task-card-title">
        ${escapeHtml(taskTitle(task))}
      </div>

      <div class="task-card-id">
        ${escapeHtml(id)}
      </div>

      <div class="task-card-meta">
        <span class="meta-token">
          ${escapeHtml(taskPriority(task))}
        </span>

        <span class="meta-token">
          ${taskDependencies(task).length} deps
        </span>

        <span class="meta-token">
          ${descendantUnlockCount(task)} unlock
        </span>
      </div>
    </article>
  `;
}

function objectiveKey(task) {
  return String(
    first(
      task.objective_id,
      task.objective,
      task.root_id,
      task.tranche_id,
      "unscoped"
    )
  );
}

function renderObjectives() {
  const groups = new Map();

  state.tasks.forEach((task) => {
    const key = objectiveKey(task);

    if (!groups.has(key)) {
      groups.set(key, []);
    }

    groups.get(key).push(task);
  });

  $("#objectivesGrid").innerHTML = [...groups.entries()]
    .map(([key, tasks]) => {
      const complete = tasks.filter(isTerminal).length;
      const ready = tasks.filter(isReady).length;
      const active = tasks.filter(isActive).length;
      const blocked = tasks.filter(isBlocked).length;

      return `
        <article class="objective">
          <div class="eyebrow">OBJECTIVE</div>
          <div class="objective-title">${escapeHtml(key)}</div>

          <div class="objective-metrics">
            <div class="objective-metric">
              <span>Established</span>
              <strong>${complete}/${tasks.length}</strong>
            </div>

            <div class="objective-metric">
              <span>Ready</span>
              <strong>${ready}</strong>
            </div>

            <div class="objective-metric">
              <span>Active</span>
              <strong>${active}</strong>
            </div>

            <div class="objective-metric">
              <span>Blocked</span>
              <strong>${blocked}</strong>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function eventTimestamp(event) {
  return first(
    event.timestamp,
    event.created_at,
    event.at,
    event.time,
    event.generated_at,
    ""
  );
}

function eventTitle(event) {
  return String(
    first(
      event.event,
      event.action,
      event.type,
      event.state,
      "recorded event"
    )
  );
}

function renderTimeline() {
  const events = state.history.slice().reverse().slice(0, 100);

  if (!events.length) {
    $("#timeline").innerHTML = `
      <p class="muted">No history events were returned.</p>
    `;
    return;
  }

  $("#timeline").innerHTML = events.map((event) => `
    <article class="timeline-event">
      <div class="timeline-event-time">
        ${escapeHtml(eventTimestamp(event) || "time unavailable")}
      </div>

      <div class="timeline-event-title">
        ${escapeHtml(eventTitle(event))}
      </div>

      <div class="timeline-event-detail">
        ${escapeHtml(
          first(
            event.task_id,
            event.id,
            event.reason,
            ""
          )
        )}
      </div>
    </article>
  `).join("");
}

function renderHistory() {
  const events = state.history.slice().reverse().slice(0, 160);

  $("#historyReplay").innerHTML = events.length
    ? events.map((event, index) => `
        <article class="timeline-event">
          <div class="timeline-event-time">
            ${index === 0 ? "NOW ← " : ""}
            ${escapeHtml(eventTimestamp(event) || "recorded")}
          </div>

          <div class="timeline-event-title">
            ${escapeHtml(eventTitle(event))}
          </div>

          <div class="timeline-event-detail">
            ${escapeHtml(
              first(
                event.task_id,
                event.reason,
                event.id,
                ""
              )
            )}
          </div>
        </article>
      `).join("")
    : `<p class="muted">No immutable history was returned.</p>`;
}

function renderEvidence() {
  const candidates = state.tasks.filter((task) => (
    taskReceipts(task).length ||
    first(task.completion_condition, task.evidence_required)
  ));

  $("#evidenceGrid").innerHTML = candidates.length
    ? candidates.slice(0, 120).map((task) => `
        <article class="evidence-item" data-open-task="${escapeHtml(taskId(task))}">
          <div class="eyebrow">
            ${escapeHtml(taskVisualState(task))}
          </div>

          <h3>${escapeHtml(taskTitle(task))}</h3>

          <p>
            ${escapeHtml(
              first(
                task.completion_condition,
                task.evidence_required,
                `${taskReceipts(task).length} receipt(s)`
              )
            )}
          </p>
        </article>
      `).join("")
    : `
      <p class="muted">
        No task evidence or completion-condition fields are currently exposed.
      </p>
    `;
}

function renderLiving() {
  const fabric = object(state.fabric);
  const surfaces = object(fabric.surfaces);
  const catalog = object(fabric.catalog);
  const changed = new Set(array(fabric.changed_surfaces));

  $("#livingFabricHealth").textContent = (
    fabric.healthy === true
      ? "healthy"
      : fabric.healthy === false
        ? "degraded"
        : "unknown"
  );

  $("#livingSequence").textContent = first(
    fabric.sequence,
    "unknown"
  );

  $("#livingHash").textContent = first(
    fabric.fabric_hash,
    "unknown"
  );

  const classes = new Set();

  Object.entries(catalog).forEach(([, specification]) => {
    const spec = object(specification);
    classes.add(String(first(spec.class, "uncategorized")));
  });

  $("#livingFilters").innerHTML = `
    <button class="quiet-button living-filter" data-living-filter="all">
      All
    </button>
    ${[...classes].sort().map((name) => `
      <button
        class="quiet-button living-filter"
        data-living-filter="${escapeHtml(name)}"
      >
        ${escapeHtml(name)}
      </button>
    `).join("")}
  `;

  const names = new Set([
    ...Object.keys(catalog),
    ...Object.keys(surfaces),
  ]);

  $("#livingField").innerHTML = [...names].sort().map((name) => {
    const specification = object(catalog[name]);
    const envelope = object(surfaces[name]);

    const className = String(
      first(
        specification.class,
        envelope.class,
        "surface"
      )
    );

    const owner = String(
      first(
        specification.owner,
        envelope.owner,
        "owner unknown"
      )
    );

    return `
      <article
        class="living-surface ${changed.has(name) ? "changed" : ""}"
        tabindex="0"
        data-surface="${escapeHtml(name)}"
        data-surface-class="${escapeHtml(className)}"
      >
        <div class="living-surface-class">
          ${escapeHtml(className)}
        </div>

        <div class="living-surface-name">
          ${escapeHtml(name.replaceAll("_", " "))}
        </div>

        <div class="living-surface-owner">
          ${escapeHtml(owner)}
        </div>
      </article>
    `;
  }).join("");

  if (
    state.lastFabricHash &&
    fabric.fabric_hash &&
    state.lastFabricHash !== fabric.fabric_hash
  ) {
    toast("Living fabric changed");
  }

  state.lastFabricHash = fabric.fabric_hash ?? state.lastFabricHash;

  if (state.selectedSurface && names.has(state.selectedSurface)) {
    inspectSurface(state.selectedSurface);
  }
}

function inspectSurface(name) {
  const fabric = object(state.fabric);
  const catalog = object(fabric.catalog);
  const surfaces = object(fabric.surfaces);

  const specification = object(catalog[name]);
  const envelope = object(surfaces[name]);

  state.selectedSurface = name;

  $("#livingInspector").innerHTML = `
    <div class="eyebrow">LIVING SURFACE</div>
    <h2 style="margin-top:7px">
      ${escapeHtml(name.replaceAll("_", " "))}
    </h2>

    ${detailSection("Projection", {
      class: first(specification.class, envelope.class, "unknown"),
      owner: first(specification.owner, envelope.owner, "unknown"),
      mode: first(specification.mode, envelope.mode, "unknown"),
      projection_only: first(
        envelope.projection_only,
        fabric.projection_only,
        true
      ),
      authority_effect: first(
        envelope.authority_effect,
        fabric.authority_effect,
        "none"
      ),
    })}

    ${detailSection("Integrity", {
      digest: first(envelope.digest, envelope.surface_hash, "unknown"),
      changed: array(fabric.changed_surfaces).includes(name),
      sequence: first(fabric.sequence, "unknown"),
      fabric_hash: first(fabric.fabric_hash, "unknown"),
    })}

    ${detailSection("Source", {
      freshness: first(
        envelope.freshness,
        envelope.freshness_state,
        "unknown"
      ),
      source: first(
        envelope.source,
        envelope.source_path,
        envelope.provenance,
        "not exposed"
      ),
      filesystem_authority: first(
        fabric.filesystem_presence_establishes_authority,
        false
      ),
    })}

    <div class="detail-section">
      <h3>Raw projected envelope</h3>
      <pre style="
        white-space:pre-wrap;
        overflow-wrap:anywhere;
        color:var(--text-dim);
        font:9px/1.55 var(--mono);
      ">${escapeHtml(JSON.stringify(envelope, null, 2))}</pre>
    </div>
  `;
}

function detailSection(title, values) {
  return `
    <div class="detail-section">
      <h3>${escapeHtml(title)}</h3>

      ${Object.entries(values).map(([key, value]) => `
        <div class="detail-row">
          <span>${escapeHtml(key)}</span>
          <span>${escapeHtml(
            typeof value === "object"
              ? JSON.stringify(value)
              : value
          )}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function openTask(task) {
  if (!task) {
    return;
  }

  state.selectedTask = task;

  $("#inspectorTaskId").textContent = taskId(task);

  $("#inspectorContent").innerHTML = `
    <div class="inspector-title">
      ${escapeHtml(taskTitle(task))}
    </div>

    <p class="inspector-purpose">
      ${escapeHtml(
        taskPurpose(task) ||
        "No purpose text is exposed for this task."
      )}
    </p>

    ${detailSection("Identity", {
      id: taskId(task),
      state: taskStatus(task),
      priority: taskPriority(task),
      readiness: isReady(task),
      blocked: isBlocked(task),
    })}

    ${detailSection("edifice", {
      objective: first(task.objective_id, task.objective, "unknown"),
      tranche: first(task.tranche_id, task.tranche, "unknown"),
      parent: first(task.parent_id, task.parent, "unknown"),
    })}

    ${detailSection("Causality", {
      dependencies: taskDependencies(task),
      dependents: relatedDependents(task).map(taskId),
      direct_unlock_count: descendantUnlockCount(task),
    })}

    ${detailSection("Completion", {
      condition: first(
        task.completion_condition,
        "not exposed"
      ),
      receipts: taskReceipts(task),
    })}

    ${detailSection("Authority", {
      owner: first(task.owner, "unknown"),
      authority: first(task.authority, "unknown"),
      projection_note:
        "Niche displays task state; this inspector does not establish authority.",
    })}
  `;

  const inspector = $("#taskInspector");
  inspector.classList.add("open");
  inspector.setAttribute("aria-hidden", "false");
}

function closeTask() {
  const inspector = $("#taskInspector");
  inspector.classList.remove("open");
  inspector.setAttribute("aria-hidden", "true");
}

function setView(name) {
  state.activeView = name;

  $$(".mode").forEach((button) => {
    button.classList.toggle(
      "active",
      button.dataset.view === name
    );
  });

  $$("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle(
      "active",
      panel.dataset.viewPanel === name
    );
  });

  if (name === "constellation") {
    requestAnimationFrame(renderConstellation);
  }

  if (name === "living") {
    renderLiving();
  }
}

function commandDefinitions() {
  return [
    {
      label: "Go to next task",
      hint: "execute",
      run: () => {
        setView("execute");
        const task = selectNextTask();
        if (task) openTask(task);
      },
    },
    {
      label: "Open executable frontier",
      hint: "execute",
      run: () => setView("execute"),
    },
    {
      label: "Show ready tasks",
      hint: "flow",
      run: () => {
        state.flowFilter = "ready";
        renderFlow();
        setView("flow");
      },
    },
    {
      label: "Show blockers",
      hint: "flow",
      run: () => {
        state.flowFilter = "blocked";
        renderFlow();
        setView("flow");
      },
    },
    {
      label: "Open constellation",
      hint: "graph",
      run: () => setView("constellation"),
    },
    {
      label: "Open objectives",
      hint: "edifice",
      run: () => setView("objectives"),
    },
    {
      label: "Open execution timeline",
      hint: "history",
      run: () => setView("timeline"),
    },
    {
      label: "Open evidence",
      hint: "proof",
      run: () => setView("evidence"),
    },
    {
      label: "Open living fabric",
      hint: "54 surfaces",
      run: () => setView("living"),
    },
    {
      label: "Replay history",
      hint: "immutable",
      run: () => setView("history"),
    },
    {
      label: "Refresh Niche",
      hint: "reconcile",
      run: () => refresh(),
    },
    {
      label: "Search tasks",
      hint: "/",
      run: () => openSearch(),
    },
  ];
}

function openCommand() {
  closePalettes();

  $("#modalBackdrop").hidden = false;
  $("#commandPalette").hidden = false;

  const input = $("#commandInput");
  input.value = "";

  renderCommands("");
  requestAnimationFrame(() => input.focus());
}

function renderCommands(query) {
  const normalized = query.trim().toLowerCase();

  const commands = commandDefinitions().filter(
    (command) => !normalized ||
      command.label.toLowerCase().includes(normalized) ||
      command.hint.toLowerCase().includes(normalized)
  );

  $("#commandResults").innerHTML = commands.map((command, index) => `
    <button class="command-result" data-command-index="${index}">
      <span>${escapeHtml(command.label)}</span>
      <small>${escapeHtml(command.hint)}</small>
    </button>
  `).join("");

  $("#commandResults")._commands = commands;
}

function openSearch() {
  closePalettes();

  $("#modalBackdrop").hidden = false;
  $("#searchPalette").hidden = false;

  const input = $("#searchInput");
  input.value = "";

  renderSearch("");
  requestAnimationFrame(() => input.focus());
}

function renderSearch(query) {
  const normalized = query.trim().toLowerCase();

  const results = (
    normalized
      ? state.tasks.filter((task) => {
          const haystack = [
            taskId(task),
            taskTitle(task),
            taskPurpose(task),
            taskStatus(task),
            taskPriority(task),
            objectiveKey(task),
            JSON.stringify(taskDependencies(task)),
          ].join(" ").toLowerCase();

          return normalized.split(/\s+/).every(
            (term) => haystack.includes(term)
          );
        })
      : state.tasks.filter(isReady)
  ).slice(0, 60);

  $("#searchResults").innerHTML = results.length
    ? results.map((task) => `
        <button
          class="command-result"
          data-search-task="${escapeHtml(taskId(task))}"
        >
          <span>${escapeHtml(taskTitle(task))}</span>
          <small>
            ${escapeHtml(taskVisualState(task))}
            · ${escapeHtml(taskId(task))}
          </small>
        </button>
      `).join("")
    : `
      <div class="muted" style="padding:12px">
        No matching task.
      </div>
    `;
}

function closePalettes() {
  $("#commandPalette").hidden = true;
  $("#searchPalette").hidden = true;
  $("#modalBackdrop").hidden = true;
}

function toast(message) {
  const element = document.createElement("div");
  element.className = "toast";
  element.textContent = message;

  $("#toastRegion").append(element);

  window.setTimeout(() => {
    element.remove();
  }, 3200);
}

async function guidedExecution() {
  const task = selectNextTask();

  if (!task) {
    toast("No executable task resolved");
    return;
  }

  openTask(task);
  toast(`Next: ${taskTitle(task)}`);
}

function showWhy() {
  const task = selectNextTask();

  if (!task) return;

  setView("execute");
  $("#oracleBody").scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
}

function showDependencies() {
  const task = selectNextTask();

  if (!task) return;

  openTask(task);
}

function showImpact() {
  const task = selectNextTask();

  if (!task) return;

  const dependents = relatedDependents(task);

  toast(
    dependents.length
      ? `${dependents.length} direct downstream task(s) exposed`
      : "No direct downstream task relationship exposed"
  );
}

async function refresh() {
  try {
    await loadCore();
  } catch (error) {
    setConnection("offline", "offline");
    toast(`Refresh failed: ${error.message}`);
  }
}

function bindEvents() {
  $$(".mode").forEach((button) => {
    button.addEventListener("click", () => {
      setView(button.dataset.view);
    });
  });

  $("#commandButton").addEventListener("click", openCommand);
  $("#searchButton").addEventListener("click", openSearch);
  $("#modalBackdrop").addEventListener("click", closePalettes);

  $("#commandInput").addEventListener("input", (event) => {
    renderCommands(event.target.value);
  });

  $("#searchInput").addEventListener("input", (event) => {
    renderSearch(event.target.value);
  });

  $("#commandResults").addEventListener("click", (event) => {
    const button = event.target.closest("[data-command-index]");

    if (!button) return;

    const commands = $("#commandResults")._commands || [];
    const command = commands[Number(button.dataset.commandIndex)];

    closePalettes();

    if (command) {
      command.run();
    }
  });

  $("#searchResults").addEventListener("click", (event) => {
    const button = event.target.closest("[data-search-task]");

    if (!button) return;

    const task = state.tasks.find(
      (candidate) => taskId(candidate) === button.dataset.searchTask
    );

    closePalettes();
    openTask(task);
  });

  $("#closeInspectorButton").addEventListener("click", closeTask);

  $("#startNextButton").addEventListener("click", guidedExecution);
  $("#whyButton").addEventListener("click", showWhy);
  $("#dependenciesButton").addEventListener("click", showDependencies);
  $("#impactButton").addEventListener("click", showImpact);

  $("#fitGraphButton").addEventListener("click", renderConstellation);
  $("#resetGraphButton").addEventListener("click", renderConstellation);

  document.addEventListener("click", (event) => {
    const taskElement = event.target.closest("[data-open-task]");

    if (taskElement) {
      const task = state.tasks.find(
        (candidate) => taskId(candidate) === taskElement.dataset.openTask
      );

      openTask(task);
      return;
    }

    const graphNode = event.target.closest("[data-task-node]");

    if (graphNode) {
      const task = state.tasks.find(
        (candidate) => taskId(candidate) === graphNode.dataset.taskNode
      );

      openTask(task);
      return;
    }

    const surface = event.target.closest("[data-surface]");

    if (surface) {
      inspectSurface(surface.dataset.surface);
      return;
    }

    const livingFilter = event.target.closest("[data-living-filter]");

    if (livingFilter) {
      const filter = livingFilter.dataset.livingFilter;

      $$(".living-surface").forEach((element) => {
        element.hidden = (
          filter !== "all" &&
          element.dataset.surfaceClass !== filter
        );
      });
    }

    const flowFilter = event.target.closest("[data-filter]");

    if (flowFilter) {
      state.flowFilter = flowFilter.dataset.filter;
      renderFlow();
    }
  });

  document.addEventListener("keydown", (event) => {
    const commandShortcut = (
      (event.metaKey || event.ctrlKey) &&
      event.key.toLowerCase() === "k"
    );

    if (commandShortcut) {
      event.preventDefault();
      openCommand();
      return;
    }

    if (
      event.key === "/" &&
      !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)
    ) {
      event.preventDefault();
      openSearch();
      return;
    }

    if (event.key === "Escape") {
      closePalettes();
      closeTask();
    }
  });

  window.addEventListener("resize", () => {
    if (state.activeView === "constellation") {
      renderConstellation();
    }

    if (state.activeView === "execute") {
      renderFrontier(selectNextTask());
    }
  });
}

async function boot() {
  bindEvents();

  try {
    await loadCore();
  } catch (error) {
    setConnection("offline", "offline");

    $("#nextTaskPanel").innerHTML = `
      <div class="next-task">
        <div class="task-kicker">NICHE API UNAVAILABLE</div>
        <div class="task-title">The projection cannot be loaded.</div>
        <p class="task-purpose">
          ${escapeHtml(error.message)}
        </p>
      </div>
    `;
  }

  state.refreshTimer = window.setInterval(
    refresh,
    5000
  );
}

boot();
