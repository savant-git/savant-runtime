"use strict";

const niche = {
    state: {
        tasks: [],
        dashboard: null,
        engine: null,
        living: null,
        fabric: null,
        history: [],
        selected: null,
        view: "execute",
        paletteIndex: 0,
        paletteItems: [],
        refreshing: false,
        lastTaskDigest: "",
        graph: { scale: 1, x: 0, y: 0 },
    },

    $: (selector, root = document) => root.querySelector(selector),
    $$: (selector, root = document) => [...root.querySelectorAll(selector)],

    escape(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    },

    value(obj, keys, fallback = null) {
        for (const key of keys) {
            if (obj && obj[key] !== undefined && obj[key] !== null) return obj[key];
        }
        return fallback;
    },

    array(value) {
        if (Array.isArray(value)) return value;
        if (value === null || value === undefined || value === "") return [];
        return [value];
    },

    taskId(task) {
        return String(this.value(task, ["task_id", "id", "identity"], ""));
    },

    taskTitle(task) {
        return String(this.value(task, ["title", "name", "purpose", "outcome"], this.taskId(task) || "Untitled task"));
    },

    taskPurpose(task) {
        return String(this.value(task, ["purpose", "outcome", "description"], "Purpose not exposed by current task projection."));
    },

    taskState(task) {
        const raw = String(this.value(task, ["state", "status"], "unknown")).toLowerCase();
        if (["done", "completed", "closed"].includes(raw)) return "complete";
        if (["in_progress", "in-progress", "running", "leased"].includes(raw)) return "active";
        if (["pending", "queued"].includes(raw)) return "waiting";
        return raw;
    },

    priority(task) {
        return String(this.value(task, ["priority"], "unknown")).toLowerCase();
    },

    dependencies(task) {
        return this.array(this.value(task, ["dependencies", "depends_on", "dependency_ids"], []))
            .map(item => typeof item === "object" ? this.taskId(item) || item.id : String(item))
            .filter(Boolean);
    },

    dependents(task) {
        const explicit = this.array(this.value(task, ["dependents", "reverse_dependencies", "dependent_ids"], []))
            .map(item => typeof item === "object" ? this.taskId(item) || item.id : String(item))
            .filter(Boolean);

        if (explicit.length) return explicit;

        const id = this.taskId(task);
        return this.state.tasks
            .filter(candidate => this.dependencies(candidate).includes(id))
            .map(candidate => this.taskId(candidate));
    },

    blockers(task) {
        return this.array(this.value(task, ["blockers", "blocked_by"], []));
    },

    receipts(task) {
        return this.array(this.value(task, ["receipts", "evidence", "evidence_receipts"], []));
    },

    completion(task) {
        return this.value(task, ["completion_condition", "completion", "done_when"], null);
    },

    ancestry(task) {
        const direct = this.array(this.value(task, ["ancestry", "parents", "edifice"], []));
        if (direct.length) return direct.map(String);

        return [
            this.value(task, ["objective"], null),
            this.value(task, ["tranche"], null),
            this.value(task, ["parent_task", "parent_id"], null),
        ].filter(Boolean).map(String);
    },

    objective(task) {
        return String(this.value(task, ["objective", "objective_id"], this.ancestry(task)[0] || "unscoped"));
    },

    isComplete(task) {
        return this.taskState(task) === "complete";
    },

    isReady(task) {
        const state = this.taskState(task);
        const explicit = this.value(task, ["ready", "is_ready", "readiness"], null);

        if (typeof explicit === "boolean") return explicit;
        if (typeof explicit === "string") {
            if (["ready", "true", "yes"].includes(explicit.toLowerCase())) return true;
            if (["blocked", "false", "no"].includes(explicit.toLowerCase())) return false;
        }

        if (["complete", "blocked", "deferred", "superseded", "rejected"].includes(state)) return false;
        if (this.blockers(task).length) return false;

        const byId = new Map(this.state.tasks.map(item => [this.taskId(item), item]));
        return this.dependencies(task).every(id => {
            const dependency = byId.get(id);
            return dependency ? this.isComplete(dependency) : false;
        });
    },

    priorityRank(task) {
        const map = {
            critical: 0,
            urgent: 1,
            highest: 1,
            high: 2,
            medium: 3,
            normal: 3,
            low: 4,
            lowest: 5,
            unknown: 9,
        };
        return map[this.priority(task)] ?? 8;
    },

    nextTask() {
        const ready = this.state.tasks.filter(task => this.isReady(task));

        return ready.sort((a, b) => {
            const priority = this.priorityRank(a) - this.priorityRank(b);
            if (priority) return priority;

            const aUnlock = this.dependents(a).length;
            const bUnlock = this.dependents(b).length;
            if (aUnlock !== bUnlock) return bUnlock - aUnlock;

            return this.taskId(a).localeCompare(this.taskId(b));
        })[0] || null;
    },

    async api(path, options = {}) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 12000);

        try {
            const response = await fetch(path, {
                cache: "no-store",
                headers: {
                    "Accept": "application/json",
                    ...(options.body ? {"Content-Type": "application/json"} : {}),
                    ...(options.headers || {}),
                },
                signal: controller.signal,
                ...options,
            });

            const payload = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(payload.error || `${response.status} ${response.statusText}`);
            }

            return payload;
        } finally {
            clearTimeout(timer);
        }
    },

    async refresh({quiet = false} = {}) {
        if (this.state.refreshing) return;
        this.state.refreshing = true;

        try {
            const results = await Promise.allSettled([
                this.api("/api/tasks?include_terminal=true"),
                this.api("/api/dashboard"),
                this.api("/api/state"),
                this.api("/api/living"),
                this.api("/api/living/fabric"),
                this.api("/api/history"),
            ]);

            const [tasks, dashboard, engine, living, fabric, history] = results;

            if (tasks.status === "fulfilled") {
                this.state.tasks = this.array(tasks.value.tasks);
            }

            if (dashboard.status === "fulfilled") this.state.dashboard = dashboard.value;
            if (engine.status === "fulfilled") this.state.engine = engine.value;
            if (living.status === "fulfilled") this.state.living = living.value;
            if (fabric.status === "fulfilled") this.state.fabric = fabric.value;
            if (history.status === "fulfilled") this.state.history = this.array(history.value.events);

            const failures = results.filter(result => result.status === "rejected");
            this.setConnection(failures.length < results.length, failures);

            this.render();

            if (!quiet && failures.length) {
                this.toast(`${failures.length} projection${failures.length === 1 ? "" : "s"} unavailable`, "error");
            }
        } catch (error) {
            this.setConnection(false, [{reason: error}]);
            if (!quiet) this.toast(error.message || String(error), "error");
        } finally {
            this.state.refreshing = false;
        }
    },

    setConnection(connected, failures = []) {
        const label = this.$("#connectionLabel");
        label.textContent = connected ? (failures.length ? "PARTIAL" : "LIVE") : "OFFLINE";

        const taskGood = Boolean(this.state.tasks);
        this.$("#taskHealthDot").className = taskGood ? "good" : "bad";

        const fabric = this.state.fabric;
        const fabricHealthy = Boolean(
            fabric &&
            (
                fabric.ok === true ||
                fabric.healthy === true ||
                fabric.health?.healthy === true
            )
        );

        this.$("#livingHealthDot").className = fabricHealthy ? "good" : (fabric ? "" : "bad");
        this.$("#taskHealth").textContent = taskGood ? "task engine live" : "task engine unavailable";
        this.$("#livingHealth").textContent = fabricHealthy ? "living fabric healthy" : (fabric ? "living fabric present" : "living fabric unavailable");
    },

    render() {
        this.renderStatus();
        this.renderExecute();
        this.renderFlow();
        this.renderConstellation();
        this.renderObjectives();
        this.renderTimeline();
        this.renderEvidence();
        this.renderLiving();
        this.renderHistory();
        this.renderPaletteResults();
    },

    counts() {
        const counts = {ready: 0, active: 0, blocked: 0, waiting: 0, complete: 0, other: 0};

        for (const task of this.state.tasks) {
            if (this.isReady(task)) counts.ready += 1;

            const state = this.taskState(task);
            if (counts[state] !== undefined) counts[state] += 1;
            else counts.other += 1;
        }

        return counts;
    },

    renderStatus() {
        const counts = this.counts();
        this.$("#statusReady").textContent = `ready ${counts.ready}`;
        this.$("#statusBlocked").textContent = `blocked ${counts.blocked}`;
        this.$("#statusActive").textContent = `active ${counts.active}`;
        this.$("#statusComplete").textContent = `complete ${counts.complete}`;
        this.$("#lastRefresh").textContent = `refreshed ${new Date().toLocaleTimeString()}`;
    },

    renderExecute() {
        const task = this.nextTask();
        const counts = this.counts();

        if (!task) {
            this.$("#nextTitle").textContent = "No executable task exposed";
            this.$("#nextPurpose").textContent = "Niche will not manufacture work merely to populate the interface.";
            this.$("#nextPriority").textContent = "NONE";
            this.$("#ancestry").innerHTML = "";
            this.$("#startNext").disabled = true;
            this.$("#startHint").textContent = "no legitimate ready task";
            this.$("#oracleFactors").innerHTML = this.empty("No ready task to rank.");
            this.$("#oracleExplanation").textContent = "No recommendation can be made from the currently exposed task state.";
        } else {
            this.$("#nextTitle").textContent = this.taskTitle(task);
            this.$("#nextPurpose").textContent = this.taskPurpose(task);
            this.$("#nextPriority").textContent = this.priority(task).toUpperCase();

            this.$("#ancestry").innerHTML = this.ancestry(task)
                .map(item => `<span>${this.escape(item)}</span>`)
                .join("");

            this.$("#startNext").disabled = false;
            this.$("#startHint").textContent = this.taskId(task);

            this.renderOracle(task);
        }

        this.$("#executionMetrics").innerHTML = [
            ["ready", counts.ready],
            ["active", counts.active],
            ["blocked", counts.blocked],
            ["complete", counts.complete],
        ].map(([label, value]) => `
            <div class="metric"><strong>${value}</strong><span>${label}</span></div>
        `).join("");

        const blockers = this.state.tasks
            .filter(task => this.taskState(task) === "blocked" || this.blockers(task).length)
            .sort((a,b) => this.dependents(b).length - this.dependents(a).length)
            .slice(0,5);

        this.$("#blockerRadar").innerHTML = blockers.length
            ? blockers.map(task => `
                <div class="compact-item" data-open-task="${this.escape(this.taskId(task))}">
                    <span>${this.escape(this.taskTitle(task))}</span>
                    <span>${this.dependents(task).length} downstream</span>
                </div>
            `).join("")
            : this.empty("No blockers exposed.");

        const recent = this.state.history.slice(-5).reverse();
        this.$("#recentChanges").innerHTML = recent.length
            ? recent.map(event => `
                <div class="compact-item">
                    <span>${this.escape(this.value(event, ["event", "action", "type"], "change"))}</span>
                    <span>${this.escape(this.value(event, ["task_id", "id"], ""))}</span>
                </div>
            `).join("")
            : this.empty("No history events exposed.");

        const trackTasks = this.state.tasks.slice(0,36);
        this.$("#frontierTrack").innerHTML = trackTasks.map((task, index) => {
            const x = trackTasks.length <= 1 ? 50 : (index / (trackTasks.length - 1)) * 100;
            const state = this.isReady(task) ? "ready" : this.taskState(task);
            return `<i class="frontier-dot ${this.escape(state)}" style="left:${x}%"></i>`;
        }).join("");
    },

    renderOracle(task) {
        const dependencies = this.dependencies(task);
        const blockers = this.blockers(task);
        const dependents = this.dependents(task);

        const factors = [
            ["priority", Math.max(10, 100 - this.priorityRank(task) * 14), this.priority(task)],
            ["readiness", this.isReady(task) ? 100 : 0, this.isReady(task) ? "ready" : "not ready"],
            ["dependencies", dependencies.length ? 72 : 100, String(dependencies.length)],
            ["blockers", blockers.length ? 8 : 100, String(blockers.length)],
            ["unlock", Math.min(100, 20 + dependents.length * 12), String(dependents.length)],
        ];

        this.$("#oracleFactors").innerHTML = factors.map(([label, score, value]) => `
            <div class="factor-row">
                <label>${this.escape(label)}</label>
                <div class="factor-track"><i style="transform:scaleX(${Number(score) / 100})"></i></div>
                <b>${this.escape(value)}</b>
            </div>
        `).join("");

        this.$("#oracleExplanation").textContent =
            `Recommended because it is currently derivable as ready, carries ${this.priority(task)} priority, ` +
            `has ${dependencies.length} direct dependencies, ${blockers.length} exposed blockers, and ` +
            `${dependents.length} direct dependents. Unknown ranking inputs remain unknown.`;
    },

    laneFor(task) {
        if (this.isComplete(task)) return "complete";
        const state = this.taskState(task);
        if (state === "active") return "active";
        if (state === "blocked") return "blocked";
        if (this.isReady(task)) return "ready";
        if (["review", "evidence"].includes(state)) return "review";
        return "waiting";
    },

    renderFlow() {
        const lanes = [
            ["ready", "Ready"],
            ["active", "Active"],
            ["blocked", "Blocked"],
            ["waiting", "Waiting"],
            ["review", "Evidence"],
            ["complete", "Complete"],
        ];

        this.$("#flowBoard").innerHTML = lanes.map(([key, title]) => {
            const tasks = this.state.tasks.filter(task => this.laneFor(task) === key);

            return `
                <section class="lane">
                    <header class="lane-head"><span>${title}</span><b>${tasks.length}</b></header>
                    <div class="lane-body">
                        ${tasks.length ? tasks.map(task => this.taskCard(task)).join("") : this.empty("No tasks")}
                    </div>
                </section>
            `;
        }).join("");
    },

    taskCard(task) {
        const state = this.isReady(task) ? "ready" : this.taskState(task);

        return `
            <article class="task-card" tabindex="0"
                     data-open-task="${this.escape(this.taskId(task))}"
                     data-state="${this.escape(state)}">
                <h3>${this.escape(this.taskTitle(task))}</h3>
                <div class="task-id">${this.escape(this.taskId(task))}</div>
                <div class="task-meta">
                    <span>${this.escape(this.priority(task))}</span>
                    <span>${this.dependencies(task).length} dep · ${this.dependents(task).length} out</span>
                </div>
            </article>
        `;
    },

    renderConstellation() {
        const tasks = this.state.tasks.slice(0,120);
        const nodes = this.$("#graphNodes");
        const edges = this.$("#graphEdges");

        if (!tasks.length) {
            nodes.innerHTML = this.empty("No task topology exposed.");
            edges.innerHTML = "";
            return;
        }

        const width = Math.max(this.$("#graphStage").clientWidth, 800);
        const height = Math.max(this.$("#graphStage").clientHeight, 600);

        const byObjective = new Map();
        for (const task of tasks) {
            const objective = this.objective(task);
            if (!byObjective.has(objective)) byObjective.set(objective, []);
            byObjective.get(objective).push(task);
        }

        const positions = new Map();
        const groups = [...byObjective.entries()];

        groups.forEach(([objective, group], groupIndex) => {
            const centerX = ((groupIndex + 1) / (groups.length + 1)) * width;
            const radius = Math.min(170, 50 + group.length * 5);

            group.forEach((task, index) => {
                const angle = (Math.PI * 2 * index / Math.max(group.length,1)) - Math.PI / 2;
                const depth = Math.floor(index / 10);
                positions.set(this.taskId(task), {
                    x: centerX + Math.cos(angle) * (radius + depth * 22),
                    y: height / 2 + Math.sin(angle) * (radius + depth * 22),
                });
            });
        });

        nodes.innerHTML = tasks.map(task => {
            const pos = positions.get(this.taskId(task));
            const state = this.isReady(task) ? "ready" : this.taskState(task);
            return `
                <button class="graph-node ${this.escape(state)}"
                        data-open-task="${this.escape(this.taskId(task))}"
                        style="left:${pos.x}px;top:${pos.y}px">
                    <strong>${this.escape(this.taskTitle(task))}</strong>
                    <small>${this.escape(state)} · ${this.escape(this.priority(task))}</small>
                </button>
            `;
        }).join("");

        const lines = [];

        for (const task of tasks) {
            const to = positions.get(this.taskId(task));
            if (!to) continue;

            for (const dependencyId of this.dependencies(task)) {
                const from = positions.get(dependencyId);
                if (!from) continue;

                const ready = this.isReady(task) ? "ready" : "";
                lines.push(
                    `<path class="graph-edge ${ready}" d="M ${from.x} ${from.y} C ${from.x} ${(from.y + to.y)/2}, ${to.x} ${(from.y + to.y)/2}, ${to.x} ${to.y}"/>`
                );
            }
        }

        edges.setAttribute("viewBox", `0 0 ${width} ${height}`);
        edges.innerHTML = lines.join("");
    },

    renderObjectives() {
        const groups = new Map();

        for (const task of this.state.tasks) {
            const key = this.objective(task);
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(task);
        }

        const root = this.$("#objectiveGrid");

        if (!groups.size) {
            root.innerHTML = this.empty("No objective projection exposed.");
            return;
        }

        root.innerHTML = [...groups.entries()].map(([objective, tasks]) => {
            const complete = tasks.filter(task => this.isComplete(task)).length;
            const ready = tasks.filter(task => this.isReady(task)).length;
            const blocked = tasks.filter(task => this.taskState(task) === "blocked").length;
            const ratio = tasks.length ? complete / tasks.length : 0;

            return `
                <article class="objective">
                    <span class="eyebrow">OBJECTIVE</span>
                    <h2>${this.escape(objective)}</h2>
                    <div class="objective-stats">
                        <span>${complete}/${tasks.length} complete</span>
                        <span>${ready} ready</span>
                        <span>${blocked} blocked</span>
                    </div>
                    <div class="progress-line"><i style="width:${ratio * 100}%"></i></div>
                </article>
            `;
        }).join("");
    },

    renderTimeline() {
        const events = this.state.history.slice().reverse();
        this.$("#timeline").innerHTML = events.length
            ? events.map(event => this.historyEvent(event, "timeline-event")).join("")
            : this.empty("No immutable history events exposed.");
    },

    historyEvent(event, className) {
        const timestamp = this.value(event, ["created_at", "timestamp", "at", "time"], "");
        const action = this.value(event, ["event", "action", "type"], "event");
        const id = this.value(event, ["task_id", "id"], "");
        const reason = this.value(event, ["reason", "message", "detail"], "");

        return `
            <article class="${className}">
                <time>${this.escape(timestamp)}</time>
                <h3>${this.escape(action)} ${this.escape(id)}</h3>
                <p>${this.escape(reason || "No explanatory text exposed.")}</p>
            </article>
        `;
    },

    renderEvidence() {
        const candidates = this.state.tasks.filter(task =>
            this.receipts(task).length ||
            this.completion(task) ||
            ["review", "evidence", "complete"].includes(this.taskState(task))
        );

        this.$("#evidenceGrid").innerHTML = candidates.length
            ? candidates.map(task => `
                <article class="evidence-card" data-open-task="${this.escape(this.taskId(task))}">
                    <span class="eyebrow">${this.escape(this.taskState(task))}</span>
                    <h3>${this.escape(this.taskTitle(task))}</h3>
                    <p>${this.escape(this.completion(task) || "Completion condition not exposed.")}</p>
                    <div class="living-meta">
                        <span>${this.receipts(task).length} receipt(s)</span>
                        <span>${this.dependencies(task).length} dependencies</span>
                    </div>
                </article>
            `).join("")
            : this.empty("No evidence-bearing tasks exposed.");
    },

    fabricSurfaces() {
        const fabric = this.state.fabric;
        if (!fabric) return [];

        if (Array.isArray(fabric.surfaces)) return fabric.surfaces;

        if (fabric.surfaces && typeof fabric.surfaces === "object") {
            return Object.entries(fabric.surfaces).map(([name, value]) => ({
                name,
                ...(typeof value === "object" && value ? value : {value}),
            }));
        }

        if (fabric.fabric?.surfaces && typeof fabric.fabric.surfaces === "object") {
            return Object.entries(fabric.fabric.surfaces).map(([name, value]) => ({
                name,
                ...(typeof value === "object" && value ? value : {value}),
            }));
        }

        return [];
    },

    renderLiving() {
        const fabric = this.state.fabric;
        const surfaces = this.fabricSurfaces();

        if (!fabric) {
            this.$("#livingGrid").innerHTML = this.empty("Living fabric endpoint unavailable.");
            this.$("#livingSummary").innerHTML = "";
            this.$("#fabricMeta").textContent = "";
            return;
        }

        const changed = this.array(this.value(fabric, ["changed_surfaces"], []));
        const sequence = this.value(fabric, ["sequence"], "?");
        const hash = this.value(fabric, ["fabric_hash", "projection_hash"], "unknown");

        this.$("#fabricMeta").textContent = `sequence ${sequence} · ${String(hash).slice(0,12)}`;

        const fresh = surfaces.filter(surface => String(this.value(surface, ["freshness", "state"], "")).toLowerCase().includes("fresh")).length;
        const stale = surfaces.filter(surface => String(this.value(surface, ["freshness", "state"], "")).toLowerCase().includes("stale")).length;

        this.$("#livingSummary").innerHTML = [
            ["surfaces", surfaces.length || this.value(fabric, ["surface_count"], 0)],
            ["changed", changed.length],
            ["fresh", fresh],
            ["stale", stale],
            ["sequence", sequence],
        ].map(([label, value]) => `
            <div class="metric"><strong>${this.escape(value)}</strong><span>${this.escape(label)}</span></div>
        `).join("");

        this.$("#livingGrid").innerHTML = surfaces.length
            ? surfaces.map(surface => {
                const name = this.value(surface, ["name", "surface"], "surface");
                const owner = this.value(surface, ["owner"], "unknown");
                const freshness = this.value(surface, ["freshness", "staleness"], "unknown");
                const authority = this.value(surface, ["authority_effect", "authority"], "unknown");
                const isChanged = changed.includes(name);

                return `
                    <article class="living-surface ${isChanged ? "changed" : ""}">
                        <span class="eyebrow">${this.escape(authority)}</span>
                        <h3>${this.escape(name)}</h3>
                        <div class="living-meta">
                            <span>owner ${this.escape(owner)}</span>
                            <span>${this.escape(freshness)}</span>
                            ${isChanged ? "<span>changed</span>" : ""}
                        </div>
                    </article>
                `;
            }).join("")
            : this.empty("Fabric is present but its surface collection is not exposed in a recognized representation.");
    },

    renderHistory() {
        const events = this.state.history.slice().reverse();
        this.$("#historyList").innerHTML = events.length
            ? events.map(event => this.historyEvent(event, "history-event")).join("")
            : this.empty("No history exposed.");
    },

    empty(text) {
        return `<div class="empty">${this.escape(text)}</div>`;
    },

    openTask(id) {
        const task = this.state.tasks.find(item => this.taskId(item) === id);
        if (!task) return;

        this.state.selected = task;
        this.$("#inspectorTitle").textContent = this.taskTitle(task);

        const dependencies = this.dependencies(task);
        const dependents = this.dependents(task);
        const blockers = this.blockers(task);
        const receipts = this.receipts(task);

        this.$("#inspectorBody").innerHTML = `
            <section class="inspector-section">
                <h3>IDENTITY</h3>
                <dl class="kv">
                    <dt>id</dt><dd>${this.escape(this.taskId(task))}</dd>
                    <dt>state</dt><dd>${this.escape(this.taskState(task))}</dd>
                    <dt>priority</dt><dd>${this.escape(this.priority(task))}</dd>
                    <dt>ready</dt><dd>${this.isReady(task) ? "yes" : "no"}</dd>
                    <dt>objective</dt><dd>${this.escape(this.objective(task))}</dd>
                </dl>
            </section>

            <section class="inspector-section">
                <h3>PURPOSE</h3>
                <p>${this.escape(this.taskPurpose(task))}</p>
            </section>

            <section class="inspector-section">
                <h3>AUTHORITY</h3>
                <dl class="kv">
                    <dt>owner</dt><dd>${this.escape(this.value(task, ["owner", "jurisdiction"], "unknown"))}</dd>
                    <dt>basis</dt><dd>${this.escape(this.value(task, ["authority_basis", "authority"], "unknown"))}</dd>
                    <dt>provenance</dt><dd>${this.escape(this.value(task, ["provenance", "created_from"], "unknown"))}</dd>
                </dl>
            </section>

            <section class="inspector-section">
                <h3>edifice</h3>
                <p>${this.escape(this.ancestry(task).join(" / ") || "No ancestry exposed.")}</p>
            </section>

            <section class="inspector-section">
                <h3>DEPENDENCIES</h3>
                <p>${this.escape(dependencies.join(", ") || "None exposed.")}</p>
            </section>

            <section class="inspector-section">
                <h3>DEPENDENTS / IMPACT</h3>
                <p>${this.escape(dependents.join(", ") || "None exposed.")}</p>
            </section>

            <section class="inspector-section">
                <h3>BLOCKERS</h3>
                <p>${this.escape(blockers.map(String).join(", ") || "None exposed.")}</p>
            </section>

            <section class="inspector-section">
                <h3>COMPLETION</h3>
                <p>${this.escape(this.completion(task) || "Completion condition not exposed.")}</p>
            </section>

            <section class="inspector-section">
                <h3>EVIDENCE</h3>
                <p>${this.escape(receipts.map(item => typeof item === "object" ? JSON.stringify(item) : String(item)).join("\n") || "No receipts exposed.")}</p>
            </section>

            <section class="inspector-section">
                <h3>ACTIONS</h3>
                <div class="execute-secondary">
                    <button data-transition-task="${this.escape(this.taskId(task))}" data-transition-state="active">Start</button>
                    <button data-transition-task="${this.escape(this.taskId(task))}" data-transition-state="complete">Complete</button>
                    <button data-transition-task="${this.escape(this.taskId(task))}" data-transition-state="blocked">Block</button>
                    <button data-transition-task="${this.escape(this.taskId(task))}" data-transition-state="deferred">Defer</button>
                </div>
            </section>
        `;

        this.$("#inspector").classList.add("open");
        this.$("#inspector").setAttribute("aria-hidden", "false");
    },

    closeInspector() {
        this.$("#inspector").classList.remove("open");
        this.$("#inspector").setAttribute("aria-hidden", "true");
    },

    switchView(view) {
        if (!this.$(`[data-surface="${view}"]`)) return;

        this.state.view = view;
        this.$$(".surface").forEach(surface => surface.classList.toggle("active", surface.dataset.surface === view));
        this.$$("[data-view-target]").forEach(button => button.classList.toggle("active", button.dataset.viewTarget === view));
        this.$("#app").dataset.view = view;

        if (view === "constellation") requestAnimationFrame(() => this.renderConstellation());
    },

    openTransition(task, state = "active") {
        this.state.selected = task;
        this.$("#transitionTitle").textContent = this.taskTitle(task);
        this.$("#transitionDescription").textContent =
            "This changes authoritative task state through the existing Niche transition endpoint. No drag or animation can perform this action.";
        this.$("#transitionState").value = state;
        this.$("#transitionReason").value = "";
        this.$("#transitionReceipts").value = "";

        const dependents = this.dependents(task);
        this.$("#consequencePreview").textContent =
            dependents.length
                ? `Projection: ${dependents.length} direct dependent task(s) may be affected. Actual readiness will be recomputed from returned authoritative state.`
                : "Projection: no direct dependents are currently exposed.";

        this.$("#transitionDialog").hidden = false;
        this.$("#transitionReason").focus();
    },

    closeTransition() {
        this.$("#transitionDialog").hidden = true;
    },

    async applyTransition(event) {
        event.preventDefault();
        const task = this.state.selected;
        if (!task) return;

        const state = this.$("#transitionState").value;
        const reason = this.$("#transitionReason").value.trim();
        const receipts = this.$("#transitionReceipts").value
            .split("\n")
            .map(value => value.trim())
            .filter(Boolean);

        try {
            await this.api(`/api/tasks/${encodeURIComponent(this.taskId(task))}/transition`, {
                method: "POST",
                body: JSON.stringify({state, reason: reason || null, receipts}),
            });

            this.closeTransition();
            this.closeInspector();
            this.toast(`Task transitioned to ${state}`);
            await this.refresh({quiet: true});
        } catch (error) {
            this.toast(error.message || String(error), "error");
        }
    },

    commands() {
        return [
            ["Go to Execute", "view", () => this.switchView("execute")],
            ["Show ready tasks", "flow", () => this.switchView("flow")],
            ["Show blockers", "flow", () => this.switchView("flow")],
            ["Show constellation", "view", () => this.switchView("constellation")],
            ["Show objectives", "view", () => this.switchView("objectives")],
            ["Show timeline", "view", () => this.switchView("timeline")],
            ["Show evidence", "view", () => this.switchView("evidence")],
            ["Open living fabric", "view", () => this.switchView("living")],
            ["Show history", "view", () => this.switchView("history")],
            ["Start next task", "execute", () => {
                const task = this.nextTask();
                if (task) this.openTransition(task, "active");
            }],
            ["Refresh state", "system", () => this.refresh()],
        ];
    },

    openPalette() {
        this.$("#palette").hidden = false;
        this.$("#paletteInput").value = "";
        this.state.paletteIndex = 0;
        this.renderPaletteResults();
        requestAnimationFrame(() => this.$("#paletteInput").focus());
    },

    closePalette() {
        this.$("#palette").hidden = true;
    },

    renderPaletteResults() {
        const input = this.$("#paletteInput");
        if (!input) return;

        const query = input.value.trim().toLowerCase();
        const commands = this.commands()
            .filter(([label]) => !query || label.toLowerCase().includes(query))
            .map(([label, type, run]) => ({label, type, run}));

        const tasks = this.state.tasks
            .filter(task => {
                if (!query) return false;
                return [
                    this.taskId(task),
                    this.taskTitle(task),
                    this.taskPurpose(task),
                    this.objective(task),
                    this.taskState(task),
                    this.priority(task),
                ].join(" ").toLowerCase().includes(query);
            })
            .slice(0,20)
            .map(task => ({
                label: this.taskTitle(task),
                type: `${this.taskState(task)} · ${this.taskId(task)}`,
                run: () => this.openTask(this.taskId(task)),
            }));

        this.state.paletteItems = [...commands, ...tasks].slice(0,30);

        if (this.state.paletteIndex >= this.state.paletteItems.length) this.state.paletteIndex = 0;

        this.$("#paletteResults").innerHTML = this.state.paletteItems.length
            ? this.state.paletteItems.map((item, index) => `
                <button class="palette-result ${index === this.state.paletteIndex ? "selected" : ""}"
                        data-palette-index="${index}">
                    <span>${this.escape(item.label)}</span>
                    <small>${this.escape(item.type)}</small>
                </button>
            `).join("")
            : this.empty("No matching command or task.");
    },

    runPalette(index) {
        const item = this.state.paletteItems[index];
        if (!item) return;
        this.closePalette();
        item.run();
    },

    toast(message, type = "") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        this.$("#toastRegion").appendChild(toast);

        setTimeout(() => toast.remove(), 4200);
    },

    bind() {
        document.addEventListener("click", event => {
            const viewButton = event.target.closest("[data-view-target]");
            if (viewButton) {
                this.switchView(viewButton.dataset.viewTarget);
                return;
            }

            const taskElement = event.target.closest("[data-open-task]");
            if (taskElement) {
                this.openTask(taskElement.dataset.openTask);
                return;
            }

            const transition = event.target.closest("[data-transition-task]");
            if (transition) {
                const task = this.state.tasks.find(item => this.taskId(item) === transition.dataset.transitionTask);
                if (task) this.openTransition(task, transition.dataset.transitionState);
                return;
            }

            const paletteItem = event.target.closest("[data-palette-index]");
            if (paletteItem) {
                this.runPalette(Number(paletteItem.dataset.paletteIndex));
            }
        });

        document.addEventListener("keydown", event => {
            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
                event.preventDefault();
                this.$("#palette").hidden ? this.openPalette() : this.closePalette();
                return;
            }

            if (event.key === "Escape") {
                this.closePalette();
                this.closeInspector();
                this.closeTransition();
                return;
            }

            if (!this.$("#palette").hidden) {
                if (event.key === "ArrowDown") {
                    event.preventDefault();
                    this.state.paletteIndex = Math.min(this.state.paletteIndex + 1, this.state.paletteItems.length - 1);
                    this.renderPaletteResults();
                } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    this.state.paletteIndex = Math.max(this.state.paletteIndex - 1, 0);
                    this.renderPaletteResults();
                } else if (event.key === "Enter") {
                    event.preventDefault();
                    this.runPalette(this.state.paletteIndex);
                }
            }

            const focused = document.activeElement?.closest?.("[data-open-task]");
            if (focused && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault();
                this.openTask(focused.dataset.openTask);
            }
        });

        this.$("#paletteButton").addEventListener("click", () => this.openPalette());
        this.$("#searchButton").addEventListener("click", () => this.openPalette());
        this.$("#paletteInput").addEventListener("input", () => {
            this.state.paletteIndex = 0;
            this.renderPaletteResults();
        });

        this.$("#closeInspector").addEventListener("click", () => this.closeInspector());
        this.$("#cancelTransition").addEventListener("click", () => this.closeTransition());
        this.$("#transitionForm").addEventListener("submit", event => this.applyTransition(event));

        this.$("#startNext").addEventListener("click", () => {
            const task = this.nextTask();
            if (task) this.openTransition(task, "active");
        });

        this.$("#showWhy").addEventListener("click", () => {
            const task = this.nextTask();
            if (task) this.openTask(this.taskId(task));
        });

        this.$("#showDependencies").addEventListener("click", () => {
            const task = this.nextTask();
            if (task) this.openTask(this.taskId(task));
        });

        this.$("#showImpact").addEventListener("click", () => {
            const task = this.nextTask();
            if (task) this.openTask(this.taskId(task));
        });

        this.$("#showEvidence").addEventListener("click", () => this.switchView("evidence"));
        this.$("#fitGraph").addEventListener("click", () => this.renderConstellation());
        this.$("#resetGraph").addEventListener("click", () => this.renderConstellation());

        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) this.refresh({quiet: true});
        });
    },

    async init() {
        this.bind();
        await this.refresh();

        setInterval(() => {
            if (!document.hidden) this.refresh({quiet: true});
        }, 5000);
    },
};

window.addEventListener("DOMContentLoaded", () => niche.init());
