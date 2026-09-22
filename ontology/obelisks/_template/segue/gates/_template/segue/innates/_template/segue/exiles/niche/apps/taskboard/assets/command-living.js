(() => {
    "use strict";

    const endpoint = "/api/living";
    const pollIntervalMs = 3000;
    const maxPulseSamples = 48;

    const state = {
        payload: null,
        previousSequence: null,
        updatedAt: null,
        failures: 0,
        timer: null,
        loading: false,
        selectedEngine: "living_state",
        pulse: []
    };

    const numberFormatter = new Intl.NumberFormat();

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function number(value) {
        const parsed = Number(value);

        if (!Number.isFinite(parsed)) {
            return "0";
        }

        return numberFormatter.format(parsed);
    }

    function booleanLabel(value) {
        if (value === true) {
            return "yes";
        }

        if (value === false) {
            return "no";
        }

        return "unknown";
    }

    function shortHash(value) {
        const text = String(value ?? "");

        if (!text) {
            return "none";
        }

        if (text.length <= 16) {
            return text;
        }

        return `${text.slice(0, 8)}…${text.slice(-8)}`;
    }

    function bytes(value) {
        let size = Number(value);

        if (!Number.isFinite(size) || size < 0) {
            return "0 B";
        }

        const units = ["B", "KiB", "MiB", "GiB", "TiB"];
        let unit = 0;

        while (size >= 1024 && unit < units.length - 1) {
            size /= 1024;
            unit += 1;
        }

        const precision = size >= 100 || unit === 0 ? 0 : 1;

        return `${size.toFixed(precision)} ${units[unit]}`;
    }

    function duration(seconds) {
        const value = Number(seconds);

        if (!Number.isFinite(value) || value < 0) {
            return "unknown";
        }

        if (value < 60) {
            return `${Math.round(value)}s`;
        }

        if (value < 3600) {
            return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
        }

        if (value < 86400) {
            const hours = Math.floor(value / 3600);
            const minutes = Math.floor((value % 3600) / 60);

            return `${hours}h ${minutes}m`;
        }

        const days = Math.floor(value / 86400);
        const hours = Math.floor((value % 86400) / 3600);

        return `${days}d ${hours}h`;
    }

    function ageFromUnixNs(value) {
        const ns = Number(value);

        if (!Number.isFinite(ns) || ns <= 0) {
            return "unknown";
        }

        const timestampMs = ns / 1000000;
        const ageSeconds = Math.max(
            0,
            (Date.now() - timestampMs) / 1000
        );

        if (ageSeconds < 5) {
            return "now";
        }

        return `${duration(ageSeconds)} ago`;
    }

    function object(value) {
        return value && typeof value === "object" && !Array.isArray(value)
            ? value
            : {};
    }

    function array(value) {
        return Array.isArray(value) ? value : [];
    }

    function firstDefined(...values) {
        for (const value of values) {
            if (value !== undefined && value !== null) {
                return value;
            }
        }

        return null;
    }

    function countObject(value) {
        return Object.keys(object(value)).length;
    }

    function normalizeServices(engine) {
        const services = object(engine.services);
        const records = firstDefined(
            services.records,
            services.services,
            []
        );

        return {
            known: Number(firstDefined(
                services.known,
                services.known_count,
                array(records).length
            )) || 0,

            active: Number(firstDefined(
                services.active,
                services.active_count,
                array(records).filter((record) => {
                    const item = object(record);

                    return (
                        item.active === true ||
                        item.active_state === "active"
                    );
                }).length
            )) || 0,

            records: array(records)
        };
    }

    function normalizeFilesystem(engine) {
        const filesystem = object(engine.filesystem);

        return {
            files: Number(firstDefined(
                filesystem.files,
                filesystem.file_count,
                0
            )) || 0,

            sourceCandidates: Number(firstDefined(
                filesystem.source_candidates,
                filesystem.source_candidate_count,
                0
            )) || 0,

            bytes: Number(firstDefined(
                filesystem.bytes,
                filesystem.total_bytes,
                0
            )) || 0,

            symlinks: Number(firstDefined(
                filesystem.symlink_count,
                filesystem.symlinks,
                0
            )) || 0,

            failures: Number(firstDefined(
                filesystem.failure_count,
                filesystem.failures,
                0
            )) || 0,

            evidenceClasses: object(
                firstDefined(
                    filesystem.evidence_classes,
                    {}
                )
            )
        };
    }

    function normalizeGovernance(engine) {
        return {
            ledgerPresent: firstDefined(
                engine.ledger_present,
                false
            ) === true,

            ledgerEvents: Number(firstDefined(
                engine.ledger_events,
                0
            )) || 0,

            currentRecords: Number(firstDefined(
                engine.current_records,
                0
            )) || 0,

            streams: object(
                firstDefined(
                    engine.streams,
                    {}
                )
            ),

            streamCount: Number(firstDefined(
                engine.stream_count,
                countObject(engine.streams)
            )) || 0,

            conflictCount: Number(firstDefined(
                engine.conflict_count,
                array(engine.conflicts).length
            )) || 0,

            conflicts: array(engine.conflicts),

            graph: object(engine.graph)
        };
    }

    function normalizeGraph(governance) {
        const graph = object(governance.graph);

        const nodes = firstDefined(
            graph.nodes,
            0
        );

        const edges = firstDefined(
            graph.edges,
            0
        );

        return {
            nodes: Array.isArray(nodes)
                ? nodes.length
                : Number(nodes) || 0,

            edges: Array.isArray(edges)
                ? edges.length
                : Number(edges) || 0,

            records: array(graph.records)
        };
    }

    function engineDotClass(present, healthy) {
        if (!present) {
            return "unknown";
        }

        if (healthy === true) {
            return "healthy";
        }

        if (healthy === false) {
            return "unhealthy";
        }

        return "unknown";
    }

    function metric(label, value, detail) {
        return `
            <div class="living-metric">
                <span>${escapeHtml(label)}</span>
                <strong>${escapeHtml(value)}</strong>
                <small>${escapeHtml(detail)}</small>
            </div>
        `;
    }

    function line(label, value, valueClass = "") {
        return `
            <div class="living-line">
                <span>${escapeHtml(label)}</span>
                <strong class="${escapeHtml(valueClass)}">
                    ${escapeHtml(value)}
                </strong>
            </div>
        `;
    }

    function codeLine(label, value) {
        return `
            <div class="living-line">
                <span>${escapeHtml(label)}</span>
                <code title="${escapeHtml(value)}">
                    ${escapeHtml(value)}
                </code>
            </div>
        `;
    }

    function empty(message) {
        return `
            <div class="living-empty">
                ${escapeHtml(message)}
            </div>
        `;
    }

    function deltaRecords(records) {
        const values = array(records).slice(0, 8);

        if (!values.length) {
            return empty("none");
        }

        return `
            <div class="living-delta-records">
                ${values.map((record) => {
                    const value = typeof record === "string"
                        ? record
                        : firstDefined(
                            object(record).path,
                            object(record).name,
                            JSON.stringify(record)
                        );

                    return `
                        <code title="${escapeHtml(value)}">
                            ${escapeHtml(value)}
                        </code>
                    `;
                }).join("")}
            </div>
        `;
    }

    function deltaGroup(label, records) {
        const values = array(records);

        return `
            <div class="living-delta-group">
                <header>
                    <span>${escapeHtml(label)}</span>
                    <strong>${number(values.length)}</strong>
                </header>
                ${deltaRecords(values)}
            </div>
        `;
    }

    function servicesMarkup(services) {
        if (!services.records.length) {
            return empty("No service records projected.");
        }

        return services.records.slice(0, 12).map((record) => {
            const service = object(record);

            const name = firstDefined(
                service.name,
                service.unit,
                service.service,
                "unknown"
            );

            const active = (
                service.active === true ||
                service.active_state === "active"
            );

            const detail = [
                firstDefined(
                    service.active_state,
                    active ? "active" : "unknown"
                ),
                firstDefined(
                    service.sub_state,
                    service.substate,
                    ""
                )
            ].filter(Boolean).join(" / ");

            return `
                <div class="living-service">
                    <span class="living-dot ${
                        active ? "healthy" : "unknown"
                    }"></span>

                    <div>
                        <strong>${escapeHtml(name)}</strong>
                        <small>${escapeHtml(detail)}</small>
                    </div>
                </div>
            `;
        }).join("");
    }

    function capabilitiesMarkup(capabilities) {
        const values = object(capabilities);
        const entries = Object.entries(values);

        if (!entries.length) {
            return empty("No capability projection.");
        }

        return `
            <div class="living-capabilities">
                ${entries.map(([name, enabled]) => `
                    <div class="living-capability">
                        <span class="living-dot ${
                            enabled ? "healthy" : "unknown"
                        }"></span>

                        <span>${escapeHtml(name)}</span>

                        <strong class="${
                            enabled ? "living-good" : ""
                        }">
                            ${escapeHtml(
                                enabled ? "available" : "fallback"
                            )}
                        </strong>
                    </div>
                `).join("")}
            </div>
        `;
    }

    function streamsMarkup(streams) {
        const entries = Object.entries(object(streams));

        if (!entries.length) {
            return empty("No governance streams projected.");
        }

        return `
            <div class="living-streams">
                ${entries.map(([name, count]) => `
                    <span>
                        ${escapeHtml(name)}
                        ·
                        ${escapeHtml(number(count))}
                    </span>
                `).join("")}
            </div>
        `;
    }

    function systemMarkup(system) {
        const host = object(system);

        const memory = object(
            firstDefined(
                host.memory,
                {}
            )
        );

        const disk = object(
            firstDefined(
                host.disk,
                {}
            )
        );

        const load = firstDefined(
            host.load,
            host.load_average,
            host.loadavg,
            []
        );

        const loadText = Array.isArray(load)
            ? load.slice(0, 3).map((item) => {
                const parsed = Number(item);

                return Number.isFinite(parsed)
                    ? parsed.toFixed(2)
                    : String(item);
            }).join(" / ")
            : String(load ?? "unknown");

        const memoryUsed = firstDefined(
            memory.used,
            memory.used_bytes,
            null
        );

        const memoryTotal = firstDefined(
            memory.total,
            memory.total_bytes,
            null
        );

        const diskUsed = firstDefined(
            disk.used,
            disk.used_bytes,
            null
        );

        const diskTotal = firstDefined(
            disk.total,
            disk.total_bytes,
            null
        );

        return [
            line(
                "uptime",
                duration(
                    firstDefined(
                        host.uptime_seconds,
                        host.uptime,
                        null
                    )
                )
            ),
            line(
                "load",
                loadText || "unknown"
            ),
            line(
                "memory",
                memoryTotal !== null
                    ? `${bytes(memoryUsed)} / ${bytes(memoryTotal)}`
                    : "unknown"
            ),
            line(
                "disk",
                diskTotal !== null
                    ? `${bytes(diskUsed)} / ${bytes(diskTotal)}`
                    : "unknown"
            )
        ].join("");
    }

    function pulseClass(sample) {
        const bucket = Math.max(
            1,
            Math.min(
                10,
                Number(sample.bucket) || 1
            )
        );

        return [
            "living-pulse-bar",
            `living-pulse-height-${bucket}`,
            sample.changed ? "changed" : ""
        ].filter(Boolean).join(" ");
    }

    function pulseMarkup() {
        if (!state.pulse.length) {
            return empty("Waiting for sequence samples.");
        }

        return `
            <div class="living-pulse">
                ${state.pulse.map((sample) => `
                    <span
                        class="${pulseClass(sample)}"
                        title="sequence ${escapeHtml(sample.sequence)}">
                    </span>
                `).join("")}
            </div>
        `;
    }

    function updatePulse(sequence) {
        const parsed = Number(sequence);

        if (!Number.isFinite(parsed)) {
            return;
        }

        const changed = (
            state.previousSequence !== null &&
            parsed !== state.previousSequence
        );

        const previous = state.pulse.length
            ? state.pulse[state.pulse.length - 1].sequence
            : parsed;

        const distance = Math.max(
            0,
            Math.abs(parsed - Number(previous))
        );

        const bucket = changed
            ? Math.min(10, Math.max(4, distance + 4))
            : 2;

        state.pulse.push({
            sequence: parsed,
            changed,
            bucket
        });

        if (state.pulse.length > maxPulseSamples) {
            state.pulse.splice(
                0,
                state.pulse.length - maxPulseSamples
            );
        }

        state.previousSequence = parsed;
    }

    function createObservatory() {
        let observatory = document.getElementById(
            "livingObservatory"
        );

        if (observatory) {
            return observatory;
        }

        const overview = document.getElementById("overviewView");

        if (!overview) {
            return null;
        }

        observatory = document.createElement("section");
        observatory.id = "livingObservatory";
        observatory.className = "living-observatory";
        observatory.setAttribute(
            "aria-label",
            "Savant living engine observatory"
        );

        const heading = overview.querySelector(".page-heading");

        if (heading && heading.nextSibling) {
            overview.insertBefore(
                observatory,
                heading.nextSibling
            );
        } else {
            overview.prepend(observatory);
        }

        return observatory;
    }

    function render() {
        const root = createObservatory();

        if (!root) {
            return;
        }

        if (!state.payload) {
            root.innerHTML = `
                <div class="living-heading">
                    <div>
                        <span class="living-kicker">
                            living constellation
                        </span>

                        <h2>Living Observatory</h2>

                        <p>
                            Read-only projection of Savant living state
                            and governance.
                        </p>
                    </div>

                    <div class="living-heading-actions">
                        <span class="living-connection degraded">
                            awaiting projection
                        </span>

                        <button
                            id="livingRefresh"
                            type="button">
                            Refresh
                        </button>
                    </div>
                </div>
            `;

            bindActions(root);
            return;
        }

        const payload = object(state.payload);
        const engines = object(payload.engines);

        const livingState = object(
            engines.living_state
        );

        const governanceEngine = object(
            engines.living_governance
        );

        const filesystem = normalizeFilesystem(livingState);
        const services = normalizeServices(livingState);
        const governance = normalizeGovernance(governanceEngine);
        const graph = normalizeGraph(governance);
        const delta = object(livingState.delta);
        const processes = object(livingState.processes);
        const tcp = object(livingState.listening_tcp);

        const processRecords = array(
            firstDefined(
                processes.records,
                livingState.process_records,
                []
            )
        );

        const processCount = Number(firstDefined(
            processes.count,
            livingState.process_count,
            processRecords.length
        )) || 0;

        const tcpRecords = array(
            firstDefined(
                tcp.records,
                livingState.listening_tcp_records,
                []
            )
        );

        const tcpCount = Number(firstDefined(
            tcp.count,
            livingState.listening_tcp_count,
            tcpRecords.length
        )) || 0;

        const sequence = firstDefined(
            livingState.sequence,
            0
        );

        const statePresent = livingState.present === true;
        const governancePresent =
            governanceEngine.present === true;

        const degraded = (
            !statePresent ||
            livingState.healthy === false ||
            !governancePresent ||
            governance.conflictCount > 0 ||
            state.failures > 0
        );

        const stateDot = engineDotClass(
            statePresent,
            livingState.healthy
        );

        const governanceDot = engineDotClass(
            governancePresent,
            governance.conflictCount === 0
                ? true
                : false
        );

        const selectedState =
            state.selectedEngine === "living_state";

        const selectedGovernance =
            state.selectedEngine === "living_governance";

        const sourceAge = ageFromUnixNs(
            livingState.generated_at_unix_ns
        );

        const capabilities = object(
            livingState.capabilities
        );

        const git = object(livingState.git);
        const latestSdump = object(livingState.latest_sdump);

        root.innerHTML = `
            <div class="living-heading">
                <div>
                    <span class="living-kicker">
                        living constellation
                    </span>

                    <h2>Living Observatory</h2>

                    <p>
                        Read-only live projection of Savant's living
                        state and living governance engines. This
                        surface does not establish or mutate authority.
                    </p>
                </div>

                <div class="living-heading-actions">
                    <span class="living-connection ${
                        degraded ? "degraded" : ""
                    }">
                        ${
                            degraded
                                ? "degraded"
                                : "live"
                        }
                    </span>

                    <button
                        id="livingRefresh"
                        type="button">
                        Refresh
                    </button>
                </div>
            </div>

            <div class="living-engine-rail">
                <button
                    type="button"
                    class="living-engine-card ${
                        selectedState ? "selected" : ""
                    }"
                    data-living-engine="living_state">

                    <span class="living-dot ${stateDot}"></span>

                    <span class="living-engine-copy">
                        <strong>living state</strong>
                        <small>
                            runtime observation + deterministic snapshot
                        </small>
                    </span>

                    <span class="living-engine-marker">
                        seq ${escapeHtml(sequence)}
                    </span>
                </button>

                <button
                    type="button"
                    class="living-engine-card ${
                        selectedGovernance ? "selected" : ""
                    }"
                    data-living-engine="living_governance">

                    <span class="living-dot ${governanceDot}"></span>

                    <span class="living-engine-copy">
                        <strong>living governance</strong>
                        <small>
                            authority ledger + deterministic projection
                        </small>
                    </span>

                    <span class="living-engine-marker">
                        ${escapeHtml(
                            shortHash(governanceEngine.digest)
                        )}
                    </span>
                </button>
            </div>

            <div class="living-metrics">
                ${metric(
                    "sequence",
                    number(sequence),
                    sourceAge
                )}

                ${metric(
                    "files",
                    number(filesystem.files),
                    bytes(filesystem.bytes)
                )}

                ${metric(
                    "source candidates",
                    number(filesystem.sourceCandidates),
                    `${number(filesystem.failures)} failures`
                )}

                ${metric(
                    "governance records",
                    number(governance.currentRecords),
                    `${number(governance.ledgerEvents)} ledger events`
                )}

                ${metric(
                    "streams",
                    number(governance.streamCount),
                    `${number(governance.conflictCount)} conflicts`
                )}

                ${metric(
                    "services",
                    `${number(services.active)}/${number(services.known)}`,
                    "active / known"
                )}

                ${metric(
                    "processes",
                    number(processCount),
                    "relevant runtime processes"
                )}

                ${metric(
                    "tcp",
                    number(tcpCount),
                    "listening endpoints"
                )}
            </div>

            <div class="living-grid">

                <section class="living-panel">
                    <header>
                        <div>
                            <span class="living-kicker">
                                continuity
                            </span>
                            <h3>Snapshot chain</h3>
                        </div>
                    </header>

                    <div class="living-stack">
                        ${codeLine(
                            "current",
                            shortHash(
                                livingState.snapshot_hash
                            )
                        )}

                        ${codeLine(
                            "previous",
                            shortHash(
                                livingState.previous_snapshot_hash
                            )
                        )}

                        ${line(
                            "projection age",
                            sourceAge,
                            sourceAge === "unknown"
                                ? "living-danger"
                                : ""
                        )}

                        ${line(
                            "cycle duration",
                            duration(
                                livingState.duration_seconds
                            )
                        )}

                        ${line(
                            "healthy",
                            booleanLabel(
                                livingState.healthy
                            ),
                            livingState.healthy === true
                                ? "living-good"
                                : "living-danger"
                        )}
                    </div>
                </section>

                <section class="living-panel">
                    <header>
                        <div>
                            <span class="living-kicker">
                                governance
                            </span>
                            <h3>Authority projection</h3>
                        </div>
                    </header>

                    <div class="living-stack">
                        ${line(
                            "ledger",
                            governance.ledgerPresent
                                ? "present"
                                : "absent",
                            governance.ledgerPresent
                                ? "living-good"
                                : "living-danger"
                        )}

                        ${line(
                            "events",
                            number(
                                governance.ledgerEvents
                            )
                        )}

                        ${line(
                            "records",
                            number(
                                governance.currentRecords
                            )
                        )}

                        ${line(
                            "conflicts",
                            number(
                                governance.conflictCount
                            ),
                            governance.conflictCount === 0
                                ? "living-good"
                                : "living-danger"
                        )}

                        ${line(
                            "graph",
                            `${number(graph.nodes)} nodes / ${number(graph.edges)} edges`
                        )}
                    </div>

                    ${streamsMarkup(
                        governance.streams
                    )}
                </section>

                <section class="living-panel">
                    <header>
                        <div>
                            <span class="living-kicker">
                                runtime
                            </span>
                            <h3>Host state</h3>
                        </div>
                    </header>

                    <div class="living-stack">
                        ${systemMarkup(
                            livingState.system
                        )}
                    </div>
                </section>

                <section class="living-panel">
                    <header>
                        <div>
                            <span class="living-kicker">
                                services
                            </span>
                            <h3>Engine neighborhood</h3>
                        </div>

                        <span class="living-engine-marker">
                            ${number(services.active)}
                            active
                        </span>
                    </header>

                    ${servicesMarkup(services)}
                </section>

                <section class="living-panel">
                    <header>
                        <div>
                            <span class="living-kicker">
                                acceleration
                            </span>
                            <h3>Capabilities</h3>
                        </div>
                    </header>

                    ${capabilitiesMarkup(
                        capabilities
                    )}
                </section>

                <section class="living-panel">
                    <header>
                        <div>
                            <span class="living-kicker">
                                provenance
                            </span>
                            <h3>Runtime context</h3>
                        </div>
                    </header>

                    <div class="living-stack">
                        ${line(
                            "git branch",
                            firstDefined(
                                git.branch,
                                "unknown"
                            )
                        )}

                        ${line(
                            "git dirty",
                            booleanLabel(
                                firstDefined(
                                    git.dirty,
                                    null
                                )
                            )
                        )}

                        ${line(
                            "sdump",
                            firstDefined(
                                latestSdump.path,
                                latestSdump.name,
                                "none"
                            )
                        )}

                        ${line(
                            "symlinks",
                            number(
                                filesystem.symlinks
                            )
                        )}

                        ${line(
                            "authority effect",
                            firstDefined(
                                payload.authority_effect,
                                "none"
                            ),
                            "living-good"
                        )}
                    </div>
                </section>

            </div>

            <section class="living-panel living-wide">
                <header>
                    <div>
                        <span class="living-kicker">
                            filesystem delta
                        </span>
                        <h3>Latest observed changes</h3>
                    </div>

                    <span class="living-engine-marker">
                        seq ${escapeHtml(sequence)}
                    </span>
                </header>

                <div class="living-delta">
                    ${deltaGroup(
                        "added",
                        delta.added
                    )}

                    ${deltaGroup(
                        "changed",
                        delta.changed
                    )}

                    ${deltaGroup(
                        "deleted",
                        delta.deleted
                    )}
                </div>
            </section>

            <section class="living-panel living-wide">
                <header>
                    <div>
                        <span class="living-kicker">
                            temporal signal
                        </span>
                        <h3>Sequence pulse</h3>
                    </div>

                    <span id="livingPulseLabel">
                        ${number(state.pulse.length)}
                        samples · polling every
                        ${pollIntervalMs / 1000}s
                    </span>
                </header>

                ${pulseMarkup()}
            </section>
        `;

        bindActions(root);
    }

    function bindActions(root) {
        const refresh = root.querySelector("#livingRefresh");

        if (refresh) {
            refresh.addEventListener(
                "click",
                () => refreshProjection(true)
            );
        }

        root.querySelectorAll(
            "[data-living-engine]"
        ).forEach((button) => {
            button.addEventListener("click", () => {
                state.selectedEngine =
                    button.dataset.livingEngine ||
                    "living_state";

                render();
            });
        });
    }

    async function refreshProjection(manual = false) {
        if (state.loading) {
            return;
        }

        if (
            document.visibilityState === "hidden" &&
            !manual
        ) {
            return;
        }

        state.loading = true;

        try {
            const response = await fetch(
                endpoint,
                {
                    method: "GET",
                    headers: {
                        Accept: "application/json"
                    },
                    cache: "no-store"
                }
            );

            if (!response.ok) {
                throw new Error(
                    `living projection returned ${response.status}`
                );
            }

            const payload = await response.json();
            const engines = object(payload.engines);
            const livingState = object(
                engines.living_state
            );

            updatePulse(
                livingState.sequence
            );

            state.payload = payload;
            state.updatedAt = Date.now();
            state.failures = 0;

            render();
        } catch (error) {
            state.failures += 1;

            console.warn(
                "niche living observatory refresh failed:",
                error
            );

            render();
        } finally {
            state.loading = false;
        }
    }

    function schedule() {
        if (state.timer !== null) {
            window.clearInterval(state.timer);
        }

        state.timer = window.setInterval(
            () => refreshProjection(false),
            pollIntervalMs
        );
    }

    function start() {
        createObservatory();
        render();

        refreshProjection(false);
        schedule();

        document.addEventListener(
            "visibilitychange",
            () => {
                if (
                    document.visibilityState === "visible"
                ) {
                    refreshProjection(false);
                }
            }
        );

        window.addEventListener(
            "focus",
            () => refreshProjection(false)
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            start,
            { once: true }
        );
    } else {
        start();
    }
})();
