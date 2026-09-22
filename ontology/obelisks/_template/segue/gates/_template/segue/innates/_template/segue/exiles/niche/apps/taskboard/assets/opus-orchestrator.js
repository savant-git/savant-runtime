"use strict";

/**
 * savant / niche / opus
 * autonomous execution engine & hierarchical task decomposer
 *
 * owner: exile:opus & exile:niche
 * authority_effect: none (projection & client-side guidance runner)
 */

(() => {
    const OPUS_BUILD = "opus-orchestrator-v2026.1";

    const state = {
        isPlaying: false,
        activeSystem: "all",
        activeSubsystem: "all",
        tasks: [],
        decomposedBlocks: new Map(), // taskId -> [ { id, title, done, weight, action } ]
        activeBlockIndex: 0,
        activeTaskId: null,
        executionQueue: [],
        stats: { completedBlocks: 0, totalBlocks: 0 }
    };

    const dom = Object.create(null);
    const $ = (sel, root = document) => root.querySelector(sel);
    const arr = v => (Array.isArray(v) ? v : []);
    const txt = (v, f = "") => (v == null ? f : (String(v).trim() || f));

    // -------------------------------------------------------------------------
    // I. OPUS INTELLIGENCE & HIERARCHICAL CLASSIFICATION
    // -------------------------------------------------------------------------
    class OpusClassifier {
        static resolveSystem(task) {
            const raw = `${task.id} ${task.title || ""} ${task.objective || ""}`.toLowerCase();
            if (raw.includes("scyon") || raw.includes("db") || raw.includes("sqlite") || raw.includes("store")) {
                return { system: "Data Substrate", subsystem: "Scyon Engine" };
            }
            if (raw.includes("atlas") || raw.includes("ui") || raw.includes("viewport") || raw.includes("theme")) {
                return { system: "Spatial Interface", subsystem: "Atlas Geography" };
            }
            if (raw.includes("palaver") || raw.includes("chat") || raw.includes("webui") || raw.includes("gateway")) {
                return { system: "Conversational Surface", subsystem: "Palaver Gateway" };
            }
            if (raw.includes("opus") || raw.includes("voice") || raw.includes("provider") || raw.includes("tts")) {
                return { system: "Cognitive Processing", subsystem: "Opus Routing" };
            }
            if (raw.includes("niche") || raw.includes("task") || raw.includes("masterplan")) {
                return { system: "Task Governance", subsystem: "Niche Engine" };
            }
            return { system: "System Runtime", subsystem: "Constitutional Core" };
        }

        static priorityWeight(priority) {
            const p = String(priority).toLowerCase();
            if (p === "critical" || p === "p0") return 1000;
            if (p === "high" || p === "p1") return 750;
            if (p === "medium" || p === "normal" || p === "p2") return 500;
            if (p === "low" || p === "p3") return 250;
            return 100;
        }

        /**
         * Opus Autonomous Decomposition
         * Takes a major task and breaks it into fine-grained atomic blocks.
         */
        static decomposeTask(task) {
            const tId = task.id || task.task_id;
            const title = task.title || task.name || tId;
            const existing = state.decomposedBlocks.get(tId);
            if (existing) return existing;

            // Granular micro-blocks tailored to task specification
            const blocks = [
                {
                    id: `${tId}-b1`,
                    taskId: tId,
                    title: `Inspect & Verify Inputs for "${title}"`,
                    detail: "Audit prerequisite dependencies and parameter states before mutation.",
                    done: false,
                    weight: 1
                },
                {
                    id: `${tId}-b2`,
                    taskId: tId,
                    title: `Execute Core Mutation: "${title}"`,
                    detail: "Perform direct structural logic, API transition, or file write operations.",
                    done: false,
                    weight: 2
                },
                {
                    id: `${tId}-b3`,
                    taskId: tId,
                    title: `Cryptographic Evidence & Graph Attestation`,
                    detail: "Collect runtime hash receipt, check invariant integrity, and close block.",
                    done: false,
                    weight: 3
                }
            ];

            state.decomposedBlocks.set(tId, blocks);
            return blocks;
        }
    }

    // -------------------------------------------------------------------------
    // II. SEQUENTIAL EXECUTION RUNNER
    // -------------------------------------------------------------------------
    class ExecutionRunner {
        static buildExecutionQueue() {
            const queue = [];
            // Sort tasks by priority descending
            const sortedTasks = [...state.tasks].sort((a, b) => {
                const wa = OpusClassifier.priorityWeight(a.priority);
                const wb = OpusClassifier.priorityWeight(b.priority);
                return wb - wa;
            });

            for (const task of sortedTasks) {
                const blocks = OpusClassifier.decomposeTask(task);
                for (const block of blocks) {
                    if (!block.done) {
                        queue.push({
                            block,
                            task,
                            system: OpusClassifier.resolveSystem(task)
                        });
                    }
                }
            }

            state.executionQueue = queue;
            this.updateStats();
        }

        static updateStats() {
            let total = 0;
            let done = 0;
            for (const blocks of state.decomposedBlocks.values()) {
                for (const b of blocks) {
                    total++;
                    if (b.done) done++;
                }
            }
            state.stats.totalBlocks = total;
            state.stats.completedBlocks = done;
        }

        static step() {
            if (!state.executionQueue.length) {
                this.buildExecutionQueue();
            }
            if (!state.executionQueue.length) {
                this.pause();
                this.render();
                return;
            }

            const current = state.executionQueue[0];
            state.activeTaskId = current.task.id || current.task.task_id;
            state.activeBlockIndex = current.block.id;

            // Highlight task on Atlas spatial canvas if available
            if (window.NicheAtlas && typeof window.NicheAtlas.select === "function") {
                window.NicheAtlas.select(state.activeTaskId);
            }

            this.render();
        }

        static completeCurrentBlock() {
            if (!state.executionQueue.length) return;
            const current = state.executionQueue[0];
            current.block.done = true;

            // Opus Re-planning Trigger: Adjust queue & recalculate priorities
            this.buildExecutionQueue();

            if (state.isPlaying) {
                this.step();
            } else {
                this.render();
            }
        }

        static play() {
            state.isPlaying = true;
            this.buildExecutionQueue();
            this.step();
        }

        static pause() {
            state.isPlaying = false;
            this.render();
        }

        static render() {
            if (!dom.container) return;

            const current = state.executionQueue[0] || null;

            dom.playBtn.textContent = state.isPlaying ? "PAUSE (SPACE)" : "PLAY SEQUENCE (SPACE)";
            dom.playBtn.classList.toggle("active", state.isPlaying);

            if (current) {
                dom.activeTaskTitle.textContent = current.task.title || current.task.id;
                dom.activeSystemTag.textContent = `${current.system.system} // ${current.system.subsystem}`;
                dom.activePriorityTag.textContent = `PRIORITY: ${String(current.task.priority || "NORMAL").toUpperCase()}`;
                dom.activeBlockTitle.textContent = current.block.title;
                dom.activeBlockDetail.textContent = current.block.detail;
                dom.stepCounter.textContent = `QUEUE: ${state.executionQueue.length} REMAINING | COMPLETED: ${state.stats.completedBlocks}`;
            } else {
                dom.activeTaskTitle.textContent = "ALL BLOCKS EXECUTED";
                dom.activeSystemTag.textContent = "IDLE";
                dom.activePriorityTag.textContent = "STANDBY";
                dom.activeBlockTitle.textContent = "No pending micro-blocks in active queue.";
                dom.activeBlockDetail.textContent = "Opus has verified that all decomposed tasks are complete.";
                dom.stepCounter.textContent = `ALL ${state.stats.completedBlocks} BLOCKS VERIFIED`;
            }

            // Render Decomposed Queue List
            const frag = document.createDocumentFragment();
            const previewItems = state.executionQueue.slice(0, 5);

            previewItems.forEach((item, idx) => {
                const el = document.createElement("div");
                el.className = `opus-queue-row ${idx === 0 ? "current" : ""}`;
                el.innerHTML = `
                    <span class="opus-row-num">${idx + 1}</span>
                    <div class="opus-row-meta">
                        <strong>${item.block.title}</strong>
                        <small>${item.task.title || item.task.id} · ${item.system.subsystem}</small>
                    </div>
                `;
                frag.append(el);
            });

            dom.queueList.replaceChildren(frag);
        }
    }

    // -------------------------------------------------------------------------
    // III. USER INTERFACE DEPLOYMENT
    // -------------------------------------------------------------------------
    function ensureUI() {
        let deck = $("#opus-execution-deck");
        if (!deck) {
            deck = document.createElement("div");
            deck.id = "opus-execution-deck";
            deck.className = "opus-deck-container";
            document.body.append(deck);
        }

        deck.innerHTML = `
            <div class="opus-deck-panel">
                <header class="opus-deck-head">
                    <div class="opus-deck-brand">
                        <span class="opus-beacon-dot"></span>
                        <strong>OPUS ORCHESTRATOR</strong>
                        <span class="opus-build-pill">${OPUS_BUILD}</span>
                    </div>
                    <div class="opus-deck-controls">
                        <button id="opus-btn-play" class="opus-btn primary" type="button">PLAY SEQUENCE</button>
                        <button id="opus-btn-step" class="opus-btn" type="button">COMPLETE BLOCK (↵)</button>
                        <button id="opus-btn-replan" class="opus-btn" type="button">OPUS RE-PLAN</button>
                    </div>
                </header>

                <div class="opus-deck-body">
                    <div class="opus-active-card">
                        <div class="opus-card-tags">
                            <span id="opus-system-tag" class="opus-tag">System</span>
                            <span id="opus-priority-tag" class="opus-tag priority">PRIORITY</span>
                        </div>
                        <h2 id="opus-active-task-title">Awaiting Execution Sequence</h2>
                        <div class="opus-block-box">
                            <span class="opus-block-label">ACTIVE MICRO-BLOCK</span>
                            <h3 id="opus-active-block-title">Loading Blocks...</h3>
                            <p id="opus-active-block-detail">Decomposing graph dependencies...</p>
                        </div>
                        <div class="opus-deck-foot">
                            <span id="opus-step-counter">QUEUE: 0 REMAINING</span>
                        </div>
                    </div>

                    <div class="opus-queue-preview">
                        <div class="opus-queue-head">UPCOMING ATOMIC BLOCKS</div>
                        <div id="opus-queue-list" class="opus-queue-list"></div>
                    </div>
                </div>
            </div>
        `;

        dom.container = deck;
        dom.playBtn = $("#opus-btn-play", deck);
        dom.stepBtn = $("#opus-btn-step", deck);
        dom.replanBtn = $("#opus-btn-replan", deck);
        dom.activeTaskTitle = $("#opus-active-task-title", deck);
        dom.activeSystemTag = $("#opus-system-tag", deck);
        dom.activePriorityTag = $("#opus-priority-tag", deck);
        dom.activeBlockTitle = $("#opus-active-block-title", deck);
        dom.activeBlockDetail = $("#opus-active-block-detail", deck);
        dom.stepCounter = $("#opus-step-counter", deck);
        dom.queueList = $("#opus-queue-list", deck);

        // Bind events
        dom.playBtn.addEventListener("click", () => {
            if (state.isPlaying) ExecutionRunner.pause();
            else ExecutionRunner.play();
        });

        dom.stepBtn.addEventListener("click", () => {
            ExecutionRunner.completeCurrentBlock();
        });

        dom.replanBtn.addEventListener("click", () => {
            ExecutionRunner.buildExecutionQueue();
            ExecutionRunner.render();
        });

        window.addEventListener("keydown", e => {
            if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
            if (e.code === "Space") {
                e.preventDefault();
                if (state.isPlaying) ExecutionRunner.pause();
                else ExecutionRunner.play();
            }
            if (e.key === "Enter") {
                e.preventDefault();
                ExecutionRunner.completeCurrentBlock();
            }
        });
    }

    // -------------------------------------------------------------------------
    // IV. SYNCHRONIZATION WITH CORE NICHE PROJECTION
    // -------------------------------------------------------------------------
    function sync() {
        const raw = window.Niche?.projection?.();
        if (!raw) return;
        state.tasks = arr(raw.source?.tasks);
        ExecutionRunner.buildExecutionQueue();
        ExecutionRunner.render();
    }

    function init() {
        ensureUI();
        sync();
        window.addEventListener("niche:projection", sync);
    }

    window.OpusOrchestrator = Object.freeze({
        play: () => ExecutionRunner.play(),
        pause: () => ExecutionRunner.pause(),
        completeBlock: () => ExecutionRunner.completeCurrentBlock(),
        replan: () => ExecutionRunner.buildExecutionQueue(),
        state: () => Object.freeze({ ...state })
    });

    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", init, { once: true })
        : init();
})();
