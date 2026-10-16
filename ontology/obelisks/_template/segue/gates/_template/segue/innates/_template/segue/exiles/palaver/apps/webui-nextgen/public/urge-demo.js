"use strict";

(() => {
  const icons = {
    orbit: `
      <circle cx="12" cy="12" r="3"/>
      <ellipse cx="12" cy="12" rx="10" ry="5"
        transform="rotate(-35 12 12)"/>
      <ellipse cx="12" cy="12" rx="10" ry="5"
        transform="rotate(35 12 12)"/>
    `,
    play: `<path d="m8 5 11 7-11 7z"/>`,
    pause: `<rect x="6" y="4" width="4" height="16" rx="1"/>
      <rect x="14" y="4" width="4" height="16" rx="1"/>`,
    stop: `<rect x="5" y="5" width="14" height="14" rx="2"/>`,
    refresh: `<path d="M20 11a8 8 0 0 0-14-5L4 8"/>
      <path d="M4 4v4h4"/>
      <path d="M4 13a8 8 0 0 0 14 5l2-2"/>
      <path d="M20 20v-4h-4"/>`,
    git: `<circle cx="6" cy="4" r="2"/>
      <circle cx="6" cy="20" r="2"/>
      <circle cx="18" cy="6" r="2"/>
      <path d="M6 6v12M6 12c0-4 12-1 12-4"/>`,
    layers: `<path d="m12 3 9 5-9 5-9-5z"/>
      <path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>`,
    network: `<circle cx="12" cy="4" r="2"/>
      <circle cx="5" cy="19" r="2"/>
      <circle cx="19" cy="19" r="2"/>
      <path d="m11 6-5 11m7-11 5 11M7 19h10"/>`,
    hexagon: `<path d="m12 2 9 5v10l-9 5-9-5V7z"/>
      <path d="m12 7 4 2.5v5L12 17l-4-2.5v-5z"/>`,
    messages: `<path d="M4 4h16v11H9l-5 4z"/>
      <path d="M8 8h8M8 11h5"/>`,
    activity: `<path d="M2 12h4l3-7 5 14 3-7h5"/>`,
    info: `<circle cx="12" cy="12" r="10"/>
      <path d="M12 11v6M12 7h.01"/>`,
    shield: `<path d="m12 2 9 4v6c0 5-4 8-9 10-5-2-9-5-9-10V6z"/>
      <path d="m8 12 3 3 5-6"/>`,
    target: `<circle cx="12" cy="12" r="9"/>
      <circle cx="12" cy="12" r="5"/>
      <circle cx="12" cy="12" r="1"/>`
  };

  function icon(name) {
    const content = icons[name] || icons.orbit;

    return `<svg xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.7"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true">${content}</svg>`;
  }

  document.querySelectorAll("[data-icon]").forEach((node) => {
    node.innerHTML = icon(node.dataset.icon);
  });

  const $ = (selector) => document.querySelector(selector);

  const scenarioData = Object.freeze({
    authentication: {
      labels: [
        "Security",
        "Compatibility",
        "Maintainability"
      ],
      weights: [45, 30, 25],
      scores: [.38, .44, .52, .49, .63, .69, .74, .81],
      descriptions: [
        "Baseline assessment",
        "Input validation",
        "Error handling",
        "Compatibility review",
        "Security refinement",
        "Code clarity",
        "Testability",
        "Balanced candidate"
      ]
    },
    interface: {
      labels: [
        "Accessibility",
        "Usability",
        "Consistency"
      ],
      weights: [40, 35, 25],
      scores: [.31, .42, .48, .59, .56, .68, .76, .84],
      descriptions: [
        "Baseline interface",
        "Navigation structure",
        "Focus behavior",
        "Contrast improvements",
        "Layout alternative",
        "Responsive refinement",
        "Interaction feedback",
        "Balanced candidate"
      ]
    },
    architecture: {
      labels: [
        "Modularity",
        "Compatibility",
        "Determinism"
      ],
      weights: [35, 30, 35],
      scores: [.36, .45, .51, .62, .59, .72, .77, .83],
      descriptions: [
        "Baseline architecture",
        "Boundary clarification",
        "Component extraction",
        "Interface stabilization",
        "Alternative composition",
        "Dependency refinement",
        "Deterministic projection",
        "Balanced candidate"
      ]
    }
  });

  const state = {
    status: "ready",
    iteration: 0,
    selected: null,
    scenario: "authentication",
    timer: null,
    events: [],
    motionOff: window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches
  };

  const viewTitles = {
    overview: [
      "Intelligence in motion.",
      "Explore how an objective becomes a sequence of evaluated, traceable improvements."
    ],
    session: [
      "Control the process.",
      "Observe the session lifecycle through a guided local simulation."
    ],
    evolution: [
      "Make improvement visible.",
      "Follow every candidate across a consistent evaluation scale."
    ],
    comparison: [
      "Choose with evidence.",
      "Compare simulated candidates before selecting an outcome."
    ],
    lineage: [
      "Every step has an origin.",
      "Explore the relationship between successive iterations."
    ]
  };

  function data() {
    return scenarioData[state.scenario];
  }

  function score(index) {
    return data().scores[index];
  }

  function formatScore(value) {
    return typeof value === "number"
      ? value.toFixed(2)
      : "Not evaluated";
  }

  function setView(name) {
    if (!viewTitles[name]) return;

    document.querySelectorAll(".view").forEach((view) => {
      view.classList.toggle(
        "active",
        view.id === `view-${name}`
      );
    });

    document.querySelectorAll(".nav-item").forEach((item) => {
      const active = item.dataset.view === name;
      item.classList.toggle("active", active);

      if (active) {
        item.setAttribute("aria-current", "page");
      } else {
        item.removeAttribute("aria-current");
      }
    });

    $("#breadcrumb-view").textContent = name;
    $("#view-title").innerHTML =
      viewTitles[name][0].replace(/\.$/, "<span>.</span>");
    $("#view-description").textContent = viewTitles[name][1];

    window.scrollTo({
      top: 0,
      behavior: state.motionOff ? "instant" : "smooth"
    });
  }

  function addEvent(title, detail) {
    state.events.unshift({
      title,
      detail
    });

    if (state.events.length > 30) {
      state.events.length = 30;
    }

    renderEvents();
  }

  function renderEvents() {
    const list = $("#event-list");
    list.replaceChildren();

    if (!state.events.length) {
      const message = document.createElement("p");
      message.className = "panel-note";
      message.textContent =
        "No simulation events have been recorded.";
      list.append(message);
      return;
    }

    state.events.forEach((event) => {
      const row = document.createElement("div");
      row.className = "event";

      const marker = document.createElement("span");
      marker.className = "event-marker";

      const text = document.createElement("div");
      const heading = document.createElement("strong");
      const detail = document.createElement("small");

      heading.textContent = event.title;
      detail.textContent = event.detail;

      text.append(heading, detail);
      row.append(marker, text);
      list.append(row);
    });
  }

  function renderCriteria() {
    const root = $("#criteria-rows");
    root.replaceChildren();

    data().labels.forEach((label, index) => {
      const row = document.createElement("div");
      row.className = "criterion-row";

      const name = document.createElement("span");
      name.textContent = label;

      const meter = document.createElement("div");
      meter.className = "meter";

      const fill = document.createElement("span");
      fill.style.width = `${data().weights[index]}%`;
      meter.append(fill);

      const value = document.createElement("output");
      value.textContent = `${data().weights[index]}%`;

      row.append(name, meter, value);
      root.append(row);
    });
  }

  function currentBestIndex() {
    if (state.iteration === 0) return null;

    let best = 0;

    for (let i = 1; i < state.iteration; i++) {
      if (score(i) > score(best)) best = i;
    }

    return best;
  }

  function renderStatus() {
    const names = {
      ready: "Ready",
      running: "Running",
      paused: "Paused",
      cancelled: "Cancelled",
      completed: "Completed"
    };

    const label = names[state.status];
    const bestIndex = currentBestIndex();

    $("#session-status").textContent = label;
    $("#session-badge").textContent = label;

    $("#iteration-number").textContent =
      `${String(state.iteration).padStart(2, "0")} / 08`;

    $("#core-iteration").textContent =
      String(state.iteration).padStart(2, "0");

    $("#selected-score").textContent =
      state.selected === null
        ? "Not selected"
        : formatScore(score(state.selected));

    $("#evolution-current").textContent =
      state.iteration
        ? `Iteration ${state.iteration}`
        : "No iteration";

    $("#evolution-best").textContent =
      bestIndex === null
        ? "Not evaluated"
        : formatScore(score(bestIndex));

    $("#evolution-selection").textContent =
      state.selected === null
        ? "None"
        : `Iteration ${state.selected + 1}`;

    $("#progress-fill").style.width =
      `${state.iteration / 8 * 100}%`;

    $("#progress-track").setAttribute(
      "aria-valuenow",
      String(state.iteration)
    );

    const active = state.status === "running";
    const paused = state.status === "paused";

    $("#pause-control").disabled = !active && !paused;
    $("#cancel-control").disabled = !active && !paused;

    $("#pause-control").innerHTML = paused
      ? `${icon("play")} Resume`
      : `${icon("pause")} Pause`;

    $("#run-control").disabled = active || paused;
    $("#run-control").innerHTML =
      `${icon("play")} ${
        state.status === "ready" ? "Start" : "Restart"
      }`;

    $("#start-button").disabled = active || paused;
  }

  function clearTimer() {
    if (state.timer !== null) {
      window.clearInterval(state.timer);
      state.timer = null;
    }
  }

  function reset() {
    clearTimer();

    state.status = "ready";
    state.iteration = 0;
    state.selected = null;
    state.events = [];

    renderAll();
  }

  function tick() {
    if (state.status !== "running") return;

    if (state.iteration >= 8) {
      finish();
      return;
    }

    const index = state.iteration;
    state.iteration++;

    addEvent(
      `Iteration ${state.iteration} evaluated`,
      `${data().descriptions[index]} · illustrative score ${formatScore(score(index))}`
    );

    if (state.iteration >= 8) {
      finish();
    } else {
      renderAll();
    }
  }

  function finish() {
    clearTimer();
    state.status = "completed";

    const best = currentBestIndex();

    state.selected = best;

    addEvent(
      "Demonstration completed",
      `Illustrative candidate ${best + 1} selected with score ${formatScore(score(best))}`
    );

    renderAll();
  }

  function start() {
    clearTimer();

    state.status = "running";
    state.iteration = 0;
    state.selected = null;
    state.events = [];

    addEvent(
      "Simulation started",
      "Using the selected illustrative scenario"
    );

    renderAll();
    setView("session");

    state.timer = window.setInterval(tick, 950);
  }

  function pauseResume() {
    if (state.status === "running") {
      state.status = "paused";
      clearTimer();

      addEvent(
        "Simulation paused",
        `Stopped after iteration ${state.iteration}`
      );
    } else if (state.status === "paused") {
      state.status = "running";

      addEvent(
        "Simulation resumed",
        `Continuing after iteration ${state.iteration}`
      );

      state.timer = window.setInterval(tick, 950);
    }

    renderAll();
  }

  function cancel() {
    if (
      state.status !== "running" &&
      state.status !== "paused"
    ) return;

    clearTimer();
    state.status = "cancelled";

    addEvent(
      "Simulation cancelled",
      "Existing illustrative results remain visible"
    );

    renderAll();
  }

  function selectCandidate(index) {
    if (
      !Number.isInteger(index) ||
      index < 0 ||
      index >= state.iteration
    ) return;

    state.selected = index;

    addEvent(
      "Candidate selected",
      `Iteration ${index + 1} · illustrative score ${formatScore(score(index))}`
    );

    renderAll();
  }

  function svgElement(name, attributes = {}) {
    const node = document.createElementNS(
      "http://www.w3.org/2000/svg",
      name
    );

    Object.entries(attributes).forEach(([key, value]) => {
      node.setAttribute(key, String(value));
    });

    return node;
  }

  function chartText(x, y, text, color = "#91a4aa") {
    const element = svgElement("text", {
      x,
      y,
      fill: color,
      "font-size": 14,
      "font-family": "system-ui",
      "text-anchor": "middle"
    });

    element.textContent = text;
    return element;
  }

  function renderChart() {
    const svg = $("#evolution-chart");
    svg.replaceChildren();

    const left = 95;
    const right = 920;
    const top = 45;
    const bottom = 340;
    const width = right - left;
    const height = bottom - top;

    for (let level = 0; level <= 5; level++) {
      const y = bottom - level / 5 * height;

      svg.append(
        svgElement("line", {
          x1: left,
          y1: y,
          x2: right,
          y2: y,
          stroke: "#2c4249",
          "stroke-width": 1
        })
      );

      svg.append(
        chartText(
          47,
          y + 5,
          (level / 5).toFixed(1)
        )
      );
    }

    const points = data().scores.map((value, index) => ({
      x: left + index / 7 * width,
      y: bottom - value * height,
      value,
      index
    }));

    const path = points
      .map((point, index) =>
        `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
      )
      .join(" ");

    const area = `${path} L ${right} ${bottom} L ${left} ${bottom} Z`;

    const defs = svgElement("defs");
    const gradient = svgElement("linearGradient", {
      id: "chart-fill",
      x1: "0%",
      y1: "0%",
      x2: "0%",
      y2: "100%"
    });

    gradient.append(
      svgElement("stop", {
        offset: "0%",
        "stop-color": "#83c9bd",
        "stop-opacity": ".28"
      }),
      svgElement("stop", {
        offset: "100%",
        "stop-color": "#83c9bd",
        "stop-opacity": "0"
      })
    );

    defs.append(gradient);
    svg.append(defs);

    svg.append(
      svgElement("path", {
        d: area,
        fill: "url(#chart-fill)"
      }),
      svgElement("path", {
        d: path,
        fill: "none",
        stroke: "#83c9bd",
        "stroke-width": 3,
        "stroke-linejoin": "round",
        "stroke-linecap": "round",
        opacity: .4
      })
    );

    const activePoints = points.slice(0, state.iteration);

    if (activePoints.length > 1) {
      svg.append(
        svgElement("path", {
          d: activePoints
            .map((point, index) =>
              `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
            )
            .join(" "),
          fill: "none",
          stroke: "#b1e2d8",
          "stroke-width": 4,
          "stroke-linecap": "round",
          "stroke-linejoin": "round"
        })
      );
    }

    points.forEach((point) => {
      const active = point.index < state.iteration;
      const selected = point.index === state.selected;

      svg.append(
        svgElement("circle", {
          cx: point.x,
          cy: point.y,
          r: selected ? 11 : active ? 8 : 5,
          fill: selected
            ? "#c9ad85"
            : active
              ? "#83c9bd"
              : "#34484e",
          stroke: "#0e171b",
          "stroke-width": 3
        })
      );

      svg.append(
        chartText(
          point.x,
          bottom + 29,
          String(point.index + 1)
        )
      );

      if (active) {
        svg.append(
          chartText(
            point.x,
            point.y - 18,
            formatScore(point.value),
            selected ? "#e0c9a5" : "#b1e2d8"
          )
        );
      }
    });
  }

  function renderCandidates() {
    const root = $("#candidate-grid");
    root.replaceChildren();

    if (state.iteration === 0) {
      const empty = document.createElement("p");
      empty.className = "panel-note";
      empty.textContent =
        "Start the demonstration to generate illustrative candidates.";
      root.append(empty);
    }

    for (let index = 0; index < state.iteration; index++) {
      const card = document.createElement("div");
      card.className = "candidate";

      if (state.selected === index) {
        card.classList.add("selected");
      }

      const art = document.createElement("div");
      art.className = "candidate-symbol";
      art.innerHTML = icon(
        index % 3 === 0
          ? "orbit"
          : index % 3 === 1
            ? "hexagon"
            : "layers"
      );

      const heading = document.createElement("strong");
      heading.textContent = `Iteration ${index + 1}`;

      const description = document.createElement("small");
      description.textContent = data().descriptions[index];

      const value = document.createElement("div");
      value.className = "candidate-score";
      value.textContent = formatScore(score(index));

      const button = document.createElement("button");
      button.className = "button secondary";
      button.textContent =
        state.selected === index ? "Selected" : "Select candidate";
      button.disabled = state.selected === index;
      button.addEventListener(
        "click",
        () => selectCandidate(index)
      );

      card.append(
        art,
        heading,
        description,
        value,
        button
      );

      root.append(card);
    }

    $("#selection-note").textContent =
      state.selected === null
        ? "No candidate has been selected."
        : `Selected iteration ${state.selected + 1}. Selection applies only to this local demonstration.`;
  }

  function renderLineage() {
    const root = $("#lineage-tree");
    root.replaceChildren();

    const origin = document.createElement("div");
    origin.className = "lineage-entry";

    const originText = document.createElement("div");
    const originTitle = document.createElement("strong");
    const originDetail = document.createElement("small");

    originTitle.textContent = "Origin";
    originDetail.textContent = "Initial illustrative objective";

    originText.append(originTitle, originDetail);
    origin.append(originText);
    root.append(origin);

    for (let index = 0; index < state.iteration; index++) {
      const row = document.createElement("div");
      row.className = "lineage-entry";
      row.style.marginLeft =
        `${Math.min(index + 1, 8) * 9}px`;

      const content = document.createElement("div");
      const heading = document.createElement("strong");
      const detail = document.createElement("small");

      heading.textContent = `Iteration ${index + 1}`;

      detail.textContent =
        `${data().descriptions[index]} · ${formatScore(score(index))}` +
        (state.selected === index ? " · selected" : "");

      content.append(heading, detail);
      row.append(content);
      root.append(row);
    }
  }

  function renderAll() {
    renderStatus();
    renderCriteria();
    renderEvents();
    renderChart();
    renderCandidates();
    renderLineage();
  }

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener(
      "click",
      () => setView(button.dataset.view)
    );
  });

  $("#start-button").addEventListener("click", start);
  $("#run-control").addEventListener("click", start);
  $("#reset-button").addEventListener("click", reset);
  $("#pause-control").addEventListener("click", pauseResume);
  $("#cancel-control").addEventListener("click", cancel);

  $("#clear-events").addEventListener("click", () => {
    state.events = [];
    renderEvents();
  });

  $("#scenario").addEventListener("change", (event) => {
    if (
      state.status === "running" ||
      state.status === "paused"
    ) {
      event.target.value = state.scenario;
      return;
    }

    if (!scenarioData[event.target.value]) return;

    state.scenario = event.target.value;
    reset();
  });

  $("#motion-toggle").addEventListener("click", () => {
    state.motionOff = !state.motionOff;

    document.documentElement.classList.toggle(
      "motion-off",
      state.motionOff
    );

    $("#motion-toggle").setAttribute(
      "aria-pressed",
      String(state.motionOff)
    );
  });

  $("#help-toggle").addEventListener("click", () => {
    $("#about-dialog").showModal();
  });

  $("#close-dialog").addEventListener("click", () => {
    $("#about-dialog").close();
  });

  $("#about-dialog").addEventListener("click", (event) => {
    if (event.target === $("#about-dialog")) {
      $("#about-dialog").close();
    }
  });

  document.documentElement.classList.toggle(
    "motion-off",
    state.motionOff
  );

  $("#motion-toggle").setAttribute(
    "aria-pressed",
    String(state.motionOff)
  );

  renderAll();
})();
