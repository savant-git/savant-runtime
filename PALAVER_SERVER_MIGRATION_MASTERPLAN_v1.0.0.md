# PALAVER SERVER MIGRATION MASTERPLAN ## Permanent Savant-Inside-Savant Development Environment  **Version:** 1.0.0   **Created:** 2026-08-10   **Snapshot basis:** `sdump_savant-runtime_081026.txt`   **Snapshot SHA-256:** `b0040a3e649c4bae74b4cfad72c06b6e986799bd671d91e633286e8c8589d6c8`   **Reference masterplan:** `CHATGPT_MASTERPLAN_v2.0.0.md`   **Reference masterplan SHA-256:** `f2eb7fa88e0f6d61001c71ad854de3bb2eec4e7bb90fca9a7508c75707cc21ef`   **Document status:** strategic projection and implementation guide   **Task authority:** Niche remains authoritative task owner   **Primary runtime:** `/root/savant-runtime`   **Primary interface owner:** Palaver   **AI/API orchestration owner:** Opus   **Durable authorized mutation owner:** Coda   **Persona/voice identity owner:** Envoy   **Projection owner:** Filament   **Evidence/attestation owner:** Notary   **Task governance owner:** Niche    > This document is not a second task authority. > > It defines the migration program required to make Palaver the normal > human-facing Savant development interface running inside the Ubuntu > server. > > The accepted Niche task graph remains authoritative for task state, > ordering, priority, readiness, completion, and dependency governance. > > If this plan conflicts with accepted authority, accepted authority wins.  ---  # 1. Mission  Move the normal Savant-development workflow from an external ChatGPT interface into `/root/savant-runtime` itself.  The completed environment must allow the project owner to interact with Savant through Palaver while Palaver:  - reads the live filesystem directly; - retrieves current authority and canon; - inspects dependencies and dependents; - maintains persistent development sessions; - delegates model/API execution through Opus; - delegates durable mutations through Coda; - delegates persona and voice through Envoy; - uses Niche for task governance; - obtains verification/attestation through Notary where established; - uses Filament for projections where appropriate; - preserves lineage and provenance; - produces execution evidence; - continues work after browser, SSH, or server restarts; - performs bounded implementation work without requiring manual copying   between ChatGPT and Ubuntu.  The objective is not to reproduce ChatGPT on Ubuntu.  The objective is:  **Palaver as a native Savant development control plane whose intelligence is replaceable, whose tools operate locally, and whose rules are enforced by Savant itself.**  ---  # 2. Governing execution rules  Every migration task receives a finite stopping condition.  Default completion gate:  1. requested behavior works; 2. required existing behavior remains intact; 3. affected dependencies and dependents remain functional; 4. authority boundaries remain intact; 5. syntax or compilation passes; 6. one focused functional verification passes; 7. one relevant startup, compatibility, or integration check passes; 8. rollback exists only when materially warranted; 9. no known blocker prevents use; 10. exact implementation evidence exists.  Default validation budget:  - syntax or compilation; - one focused functional test; - one integration/startup/compatibility check.  Do not create broad testing, migration, reporting, or observability infrastructure for a localized task unless shared-interface risk requires it.  ---  # 3. Authority before convenience  The AI model is never itself the final enforcement boundary.  Prompts may instruct.  Local runtime policy must enforce.  The model may propose:  - file reads; - searches; - patches; - commands; - API calls; - tests; - projections.  The local Savant runtime determines whether those operations are permitted.  The execution boundary must enforce at least:  - allowed filesystem roots; - read/write distinction; - owner boundaries; - secret exclusion; - authority mutation restrictions; - destructive-operation restrictions; - execution timeouts; - output limits; - validation requirements; - receipt generation.  No model provider receives authority merely because it generated a tool call.  ---  # 4. Canonical responsibility map  The permanent implementation must preserve the following boundaries.  | Concern | Owner | |---|---| | Conversation and human interaction | Palaver | | AI/provider/API orchestration | Opus | | Durable authorized filesystem mutation | Coda | | Persona and voice identity | Envoy | | Task governance and roadmap | Niche | | Projection execution | Filament | | Evidence and attestation | Notary | | Canon/memory authority | existing owning canon/Lore architecture | | Shared interface substrate | Splyce where applicable | | Application composition | Coalesce when implemented |  Palaver coordinates these owners.  Palaver does not absorb them.  ---  # 5. Current implementation evidence  The current source contains meaningful Palaver implementation substance.  Observed Palaver capabilities include implementation for:  - safe relative path resolution; - file-tree construction; - directory listing; - file reading; - file saving; - diffs; - graph snapshots; - activity timelines; - workspace state loading; - workspace state saving; - direct commands; - AI chat; - runtime payloads; - repository payloads; - memory payloads; - agent-job payloads; - patch-review queues; - patch creation; - patch application; - patch rejection; - JSON/text reading; - matching-file lookup.  The existing `palaver_ultra` launcher already prefers:  `palaver/runtime/server.py`  and falls back to:  `palaver/apps/webui_ultra/server.py`  This is valuable compatibility behavior.  Do not discard it until the canonical replacement has proven equivalent or better behavior.  ---  # 6. Current interface evidence  The source includes:  `apps/webui_ultra`  and:  `apps/webui-nextgen`  The next-generation interface already contains architectural surfaces for concepts including:  - repository; - runtime; - memory; - ontology; - relationships; - timeline; - authority; - graph; - lineage; - observatories; - workspace state.  The migration should reuse these interface assets.  Do not start a third unrelated Palaver frontend.  ---  # 7. Current service evidence  Historical/current Palaver deployment work includes services for:  - Palaver backend; - Palaver frontend; - Cloudflare quick tunnel.  This topology demonstrates previous service persistence work.  It is not the intended final topology.  The final default topology should be simpler.  ---  # 8. Current architectural defects to correct  The migration must explicitly correct the following known classes of defect.  ## 8.1 Provider ownership leakage  Palaver code has historically called provider APIs directly.  That conflicts with the established responsibility:  **Opus owns API orchestration.**  Direct provider code in Palaver becomes compatibility lineage and is eventually retired.  ## 8.2 Mutation ownership leakage  Palaver currently contains direct file-saving behavior.  Durable authorized mutation belongs to Coda.  The final design separates:  `Palaver tool request`  from:  `Coda mutation execution`  Palaver may inspect and propose.  Coda performs the authorized durable write.  ## 8.3 Multiple Palaver backends  Historical implementations include:  - `palaver_voice_backend.py`; - `apps/webui_ultra/server.py`; - potential canonical `runtime/server.py`.  One canonical backend must emerge.  ## 8.4 Split frontend/backend origin  Historical development used Vite frontend plus backend proxying.  The production Palaver workstation should expose one same-origin application/API boundary.  ## 8.5 Implementation outrunning contracts  Palaver has more actual implementation than some formal capability and contract manifests describe.  Formal capability projections must eventually reflect verified implementation rather than remain generic stubs.  ## 8.6 Prompt-only rule enforcement  Rules currently represented only as AI instructions are insufficient.  Important rules must become executable local policy.  ---  # 9. Target runtime flow  Canonical text-development flow:  ```text USER   ↓ PALAVER   ↓ session resolver   ↓ context compiler   ↓ NICHE task state / relevant authority / relevant filesystem state   ↓ OPUS inference request   ↓ provider/model selection   ↓ MODEL   ↓ structured response or requested tool operation   ↓ PALAVER TOOL BROKER   ↓ policy resolution   ↓ read operation or CODA mutation transaction or authorized Exile capability   ↓ execution receipt   ↓ context update   ↓ MODEL continuation when necessary   ↓ PALAVER   ↓ USER ` 
No step gives the model direct unrestricted root-shell authority.
  
# 10. Target voice flow
 
Canonical voice flow:
 `USER AUDIO   ↓ PALAVER conversation/session   ↓ speech transcription capability   ↓ normal Palaver turn   ↓ OPUS inference   ↓ response text   ↓ ENVOY persona/voice resolution   ↓ OPUS provider execution   ↓ audio   ↓ PALAVER   ↓ USER ` 
Conversation identity remains Palaver-owned.
 
Voice identity remains Envoy-owned.
 
Provider execution remains Opus-owned.
  
# 11. Permanent operating model
 
After cutover, the normal development entry point is Palaver.
 
Typical commands should become possible:
 `Continue. ` `What is the highest-priority ready Savant task? ` `Read the newest source dump and continue Coalesce. ` `Inspect the live implementation before changing it. ` `Fix this failure and validate only what is necessary. ` `Show me the proposed patch before applying it. ` `Implement it. ` `Resume the session from yesterday. ` 
Palaver should recover the task and filesystem context locally rather than requiring the user to repaste terminal output.
  
# 12. Dependency strategy
 
Do not introduce an external orchestration framework that competes with Savant ownership.
 
Dependencies are admitted only where they materially improve several of:
 
 
- correctness;
 
- schema safety;
 
- streaming;
 
- concurrency;
 
- interoperability;
 
- maintainability;
 
- security;
 
- observability;
 
- recoverability.
 

 
All Python dependencies belong in an isolated Palaver runtime environment.
 
Do not modify Ubuntu's system Python package set unnecessarily.
  
# 13. Required dependency candidates
 
The migration should evaluate and, if compatibility is confirmed, admit the following.
 
## 13.1 FastAPI
 
Purpose:
 
 
- canonical asynchronous HTTP interface;
 
- typed API routes;
 
- request/response validation;
 
- WebSockets;
 
- streaming;
 
- static application integration;
 
- lifecycle hooks.
 

 
It replaces Flask only after feature parity is demonstrated.
 
## 13.2 Uvicorn
 
Purpose:
 
 
- ASGI server;
 
- local production service process;
 
- WebSocket transport;
 
- clean systemd execution.
 

 
Default bind remains loopback.
 
## 13.3 Pydantic
 
Purpose:
 
 
- typed tool contracts;
 
- typed inference contracts;
 
- request/response validation;
 
- generated JSON Schema projections;
 
- strict settings models.
 

 
Pydantic models are validation projections.
 
They are not Savant authority.
 
## 13.4 Official OpenAI Python SDK
 
Owner:
 
Opus.
 
Purpose:
 
 
- OpenAI Responses/API access;
 
- streaming;
 
- tool-call normalization;
 
- provider-native error handling.
 

 
Palaver does not import provider SDKs directly.
 
## 13.5 Official Anthropic Python SDK
 
Owner:
 
Opus.
 
Purpose:
 
 
- Claude provider access;
 
- streaming;
 
- provider-native request/response handling.
 

 
Palaver does not import it directly.
 
## 13.6 Google Gen AI Python SDK
 
Owner:
 
Opus.
 
Purpose:
 
 
- Gemini provider access;
 
- asynchronous provider calls;
 
- streaming;
 
- provider-native content handling.
 

 
Palaver does not import it directly.
  
# 14. Optional dependency candidates
 
These are not automatically admitted.
 
## 14.1 `watchfiles`
 
Potential purpose:
 
 
- incremental repository-change notifications;
 
- live interface refresh;
 
- efficient development-time filesystem observation.
 

 
Do not use filesystem watching as authority.
 
## 14.2 `orjson`
 
Potential purpose:
 
 
- faster serialization for large graph/repository projections.
 

 
Admit only if profiling proves a material benefit.
 
## 14.3 JSON Schema implementation
 
Potential purpose:
 
 
- portable validation of tool and protocol projections.
 

 
Use only as validation.
 
## 14.4 OpenAI Agents SDK
 
Status:
 
optional Opus adapter only.
 
Potential capabilities include:
 
 
- OpenAI-specific agent loops;
 
- sessions;
 
- tool helpers;
 
- tracing;
 
- guardrails;
 
- resumable/sandbox-oriented patterns.
 

 
It must not become Savant's canonical agent architecture.
 
Opus retains orchestration ownership.
 
## 14.5 Model Context Protocol
 
Status:
 
interoperability boundary only.
 
Potential purpose:
 
 
- expose selected Palaver/Savant resources and tools to compatible external clients;
 
- consume explicitly approved external MCP tools.
 

 
MCP must not replace Savant authority, graph, owner, or tool contracts.
  
# 15. Dependency rejection rules
 
Reject a dependency when it:
 
 
- duplicates an existing Savant primitive;
 
- creates a second task engine;
 
- creates a second authority system;
 
- creates a second memory authority;
 
- requires provider-specific logic inside Palaver;
 
- forces cloud-hosted runtime state;
 
- prevents deterministic local operation;
 
- makes rollback materially harder without proportional benefit;
 
- hides filesystem mutation from Savant;
 
- introduces broad unrestricted tool execution.
 

  
# 16. Nine-phase migration
 
The migration has exactly nine program phases.
 `P0 — freeze and baseline P1 — authority and contracts P2 — canonical Palaver runtime P3 — local tool and mutation plane P4 — Opus intelligence plane P5 — context, session, and replay P6 — interface, streaming, and voice P7 — assurance, security, and operations P8 — shadow migration and permanent cutover ` 
Each phase is independently bounded.
 
Do not begin the next phase when the current exit gate is not satisfied.
  
# 17. PHASE P0 — Freeze and baseline
 
## Objective
 
Create a stable comparison point before changing Palaver architecture.
 
## Tasks
 
### PAL-M0-001 — Capture current Palaver implementation inventory
 
Inspect and record:
 
 
- canonical Palaver root;
 
- `runtime`;
 
- `apps/webui_ultra`;
 
- `apps/webui-nextgen`;
 
- commands;
 
- API routes;
 
- contracts;
 
- capabilities;
 
- registry;
 
- services;
 
- symlinks;
 
- runtime state;
 
- current provider integrations.
 

 
### PAL-M0-002 — Capture related owner interfaces
 
Inspect current:
 
 
- Opus;
 
- Coda;
 
- Envoy;
 
- Niche;
 
- Filament;
 
- Notary;
 
- Splyce integration surfaces.
 

 
### PAL-M0-003 — Capture three baseline workflows
 
Baseline:
 
 
1. text chat;
 
2. repository read/search;
 
3. patch-review/write workflow.
 

 
### PAL-M0-004 — Preserve active return points
 
Record unfinished work including:
 
 
- Coalesce rename/migration;
 
- Coalesce architecture documents;
 
- source-application integration;
 
- ownership/authority reconciliation blockers;
 
- current Masterplan state.
 

 
### PAL-M0-005 — Record current services
 
Capture:
 
 
- systemd unit definitions;
 
- listening ports;
 
- environment files;
 
- startup commands;
 
- current health endpoints.
 

 
## Exit gate
 
The existing Palaver environment can be reconstructed or compared after migration.
 
No code replacement occurs before this gate.
  
# 18. PHASE P1 — Authority and contracts
 
## Objective
 
Make the future Palaver behavior enforce current Savant jurisdiction.
 
## Tasks
 
### PAL-M1-001 — Define canonical Palaver responsibility
 
Palaver owns:
 
 
- human interaction;
 
- session management;
 
- conversation state;
 
- request admission;
 
- context requests;
 
- tool request coordination;
 
- response presentation.
 

 
Palaver does not own:
 
 
- AI provider execution;
 
- durable mutation authority;
 
- task authority;
 
- persona ownership;
 
- evidence authority.
 

 
### PAL-M1-002 — Define canonical inference contract
 
Create provider-neutral structures for:
 
 
- request identity;
 
- session identity;
 
- task identity;
 
- messages;
 
- context packet;
 
- requested capabilities;
 
- model preference constraints;
 
- tool declarations;
 
- streaming policy;
 
- budget;
 
- response;
 
- usage;
 
- lineage.
 

 
### PAL-M1-003 — Define canonical tool contract
 
Every tool exposes:
 
 
- stable identity;
 
- owner;
 
- schema;
 
- read/write classification;
 
- allowed roots;
 
- timeout;
 
- output limit;
 
- approval class;
 
- authority effect;
 
- mutation effect;
 
- validation requirements.
 

 
### PAL-M1-004 — Define execution policy
 
At minimum distinguish:
 `inspect propose implement authority-sensitive destructive external ` 
### PAL-M1-005 — Bind mutation ownership to Coda
 
All durable mutation requests transition through Coda.
 
Existing direct-save functions remain compatibility paths until migrated.
 
### PAL-M1-006 — Bind AI/API ownership to Opus
 
Palaver emits provider-neutral inference requests.
 
### PAL-M1-007 — Bind task governance to Niche
 
Requests such as:
 
`what should I do next?`
 
must resolve through Niche task state rather than Palaver inventing priority.
 
### PAL-M1-008 — Bind voice/persona to Envoy
 
Palaver never stores independent canonical persona definitions.
 
### PAL-M1-009 — Formalize Palaver capabilities
 
Update formal capability/contracts projections only from verified implementation.
 
## Exit gate
 
A local validator can classify representative Palaver operations and reject at least:
 
 
- unauthorized write;
 
- direct provider bypass;
 
- authority-changing operation without owner;
 
- secret read into model context.
 

  
# 19. PHASE P2 — Canonical Palaver runtime
 
## Objective
 
Replace multiple backend paths with one canonical runtime while preserving compatibility.
 
## Canonical target
 `.../exiles/palaver/runtime/server.py ` 
## Tasks
 
### PAL-M2-001 — Read current backends completely
 
Read:
 
 
- `palaver_voice_backend.py`;
 
- `apps/webui_ultra/server.py`;
 
- any existing `runtime/server.py`.
 

 
Map every active route and caller.
 
### PAL-M2-002 — Establish ASGI runtime
 
Implement a canonical FastAPI/ASGI application after compatibility review.
 
### PAL-M2-003 — Preserve compatibility entry points
 
`palaver_ultra` remains valid.
 
Legacy callers route to the canonical server.
 
### PAL-M2-004 — Same-origin UI/API serving
 
Production Palaver serves:
 
 
- built interface;
 
- `/api/...`;
 
- WebSocket/stream endpoint;
 

 
from one origin.
 
### PAL-M2-005 — Lifecycle initialization
 
Startup initializes:
 
 
- policy;
 
- session store;
 
- Opus adapter registry;
 
- workspace registry;
 
- health registry.
 

 
Shutdown closes:
 
 
- provider clients;
 
- streams;
 
- pending background work cleanly.
 

 
### PAL-M2-006 — Structured error contract
 
Errors identify:
 
 
- operation;
 
- owner;
 
- class;
 
- recoverability;
 
- retryability;
 
- receipt ID where applicable.
 

 
### PAL-M2-007 — Versioned API
 
Introduce an explicit protocol version.
 
Do not silently break current UI consumers.
 
### PAL-M2-008 — Health decomposition
 
Expose separate health for:
 
 
- Palaver;
 
- Opus;
 
- Coda;
 
- Envoy;
 
- task context;
 
- filesystem tool plane;
 
- session store;
 
- projection plane.
 

 
### PAL-M2-009 — Retire Flask only after parity
 
Flask remains compatibility evidence until all required routes have equivalent canonical behavior.
 
## Exit gate
 
One canonical server can:
 
 
- start from systemd;
 
- serve the interface;
 
- answer health;
 
- open a streaming connection;
 
- preserve one legacy API path.
 

  
# 20. PHASE P3 — Local tool and mutation plane
 
## Objective
 
Give the AI useful filesystem/runtime capability without granting it unrestricted root control.
 
## Tasks
 
### PAL-M3-001 — Typed filesystem-read tools
 
Implement typed operations for:
 
 
- stat;
 
- list;
 
- read text;
 
- read structured data;
 
- search;
 
- inspect directory;
 
- inspect current implementation.
 

 
### PAL-M3-002 — Repository tools
 
Expose:
 
 
- git status;
 
- diff;
 
- tracked-file inspection;
 
- history lookup where available;
 
- dependency/dependent inspection.
 

 
Git does not become authority.
 
### PAL-M3-003 — Structured command runner
 
Commands require:
 
 
- explicit executable;
 
- explicit arguments;
 
- absolute working directory;
 
- timeout;
 
- environment allowlist;
 
- maximum captured output.
 

 
Do not execute arbitrary shell strings by default.
 
### PAL-M3-004 — Coda patch transaction
 
Mutation flow:
 `proposal → policy → current-file digest check → Coda transaction → atomic write → receipt → validation ` 
### PAL-M3-005 — Optimistic concurrency
 
Reject mutation if the target changed after the AI inspected it unless the operation explicitly re-reads and replans.
 
### PAL-M3-006 — Atomic file replacement
 
Never leave half-written source files.
 
### PAL-M3-007 — Patch review compatibility
 
Reuse current patch review concepts.
 
Do not build a second unrelated review queue.
 
### PAL-M3-008 — Mutation receipts
 
A write receipt contains:
 
 
- target;
 
- prior digest;
 
- new digest;
 
- requesting session;
 
- task ID;
 
- operation;
 
- owner;
 
- timestamp;
 
- validation result.
 

 
### PAL-M3-009 — Tool result normalization
 
Tool outputs are structured and bounded before returning to a model.
 
## Exit gate
 
A model can autonomously:
 
 
1. inspect a file;
 
2. propose a change;
 
3. request a Coda mutation;
 
4. run syntax validation;
 
5. receive evidence;
 

 
without direct unrestricted shell or raw file-write authority.
  
# 21. PHASE P4 — Opus intelligence plane
 
## Objective
 
Move provider intelligence completely behind Opus.
 
## Tasks
 
### PAL-M4-001 — Inventory `/root/.env` variable names safely
 
Determine available provider capability without exposing values.
 
Never print secrets.
 
### PAL-M4-002 — Official provider adapters
 
Implement/adapt verified Opus providers for available credentials.
 
Candidate official SDKs:
 
 
- OpenAI;
 
- Anthropic;
 
- Google Gen AI.
 

 
Only providers for which valid configured credentials exist become available.
 
### PAL-M4-003 — Provider-neutral response schema
 
Normalize:
 
 
- text;
 
- structured output;
 
- tool calls;
 
- usage;
 
- finish reason;
 
- errors;
 
- provider;
 
- model;
 
- latency;
 
- lineage.
 

 
### PAL-M4-004 — Capability registry
 
Providers advertise capabilities such as:
 
 
- text;
 
- structured output;
 
- tools;
 
- vision;
 
- large context;
 
- streaming;
 
- realtime;
 
- embeddings;
 
- audio.
 

 
Do not hardcode assumptions from provider names.
 
### PAL-M4-005 — Adaptive routing
 
Opus chooses models according to:
 
 
- task kind;
 
- capability requirement;
 
- cost policy;
 
- latency policy;
 
- context size;
 
- availability;
 
- reliability;
 
- user preference.
 

 
### PAL-M4-006 — Fallback chain
 
Provider failure may trigger deterministic fallback when the task permits it.
 
Fallback must be visible in lineage.
 
### PAL-M4-007 — Circuit breaking
 
Repeated provider failure temporarily removes that route from normal selection rather than repeatedly stalling Palaver.
 
### PAL-M4-008 — Usage accounting
 
Record:
 
 
- requests;
 
- tokens where reported;
 
- estimated/actual cost where supported;
 
- latency;
 
- provider/model.
 

 
Usage is telemetry, not task authority.
 
### PAL-M4-009 — Optional advanced adapter boundary
 
OpenAI Agents SDK, MCP, provider-native agent features, or later provider frameworks may be exposed through Opus adapters.
 
They never become Palaver's canonical orchestration engine.
 
## Exit gate
 
Palaver contains no required provider-specific inference logic.
 
A Palaver turn can route through at least two configured Opus providers when available.
  
# 22. PHASE P5 — Context, session, and replay
 
## Objective
 
Make Palaver capable of sustained Savant development without conversation copy/paste.
 
## Tasks
 
### PAL-M5-001 — Persistent session identity
 
Each session receives a stable identifier.
 
### PAL-M5-002 — Active task binding
 
A session may bind to a Niche task or explicit bounded project task.
 
### PAL-M5-003 — Authority-aware context compiler
 
Context assembly considers:
 
 
1. current user directive;
 
2. accepted authority;
 
3. accepted decisions;
 
4. constitutional canon;
 
5. verified implementation;
 
6. admitted evidence;
 
7. deterministic projections;
 
8. relevant recent session history.
 

 
### PAL-M5-004 — Bounded repository retrieval
 
Do not send the repository wholesale.
 
Retrieve only relevant files and records.
 
### PAL-M5-005 — Return-point ingestion
 
Detailed Markdown return points become resumable context sources while retaining their stated authority class.
 
### PAL-M5-006 — Session compaction
 
Long sessions receive deterministic summaries/checkpoints.
 
Raw history remains separately recoverable.
 
### PAL-M5-007 — Context provenance
 
Every model context packet can identify where significant context came from.
 
### PAL-M5-008 — Deterministic replay record
 
Store enough information to reconstruct:
 
 
- session;
 
- task;
 
- context sources;
 
- provider request identity;
 
- tool calls;
 
- mutation receipts;
 
- final result.
 

 
### PAL-M5-009 — Resume after restart
 
A server restart must not erase the active development session.
 
## Exit gate
 
The user can close Palaver, restart it, say:
 `Continue. ` 
and Palaver can recover the active bounded task without requiring terminal history to be repasted.
  
# 23. PHASE P6 — Interface, streaming, and voice
 
## Objective
 
Turn existing Palaver frontend work into the permanent Savant workstation.
 
## Tasks
 
### PAL-M6-001 — Select one frontend lineage
 
Use `webui-nextgen` as the target presentation lineage unless live inspection establishes a stronger current implementation.
 
Reuse proven `webui_ultra` behavior.
 
Do not maintain two complete frontend products.
 
### PAL-M6-002 — Align with Splyce
 
Shared interface primitives should reuse Splyce where current authority and implementation permit it.
 
Palaver-specific controls remain Palaver specialization.
 
### PAL-M6-003 — Streaming text responses
 
Show model output progressively.
 
### PAL-M6-004 — Live tool activity
 
The UI should visibly distinguish:
 
 
- reasoning request;
 
- read;
 
- search;
 
- proposed mutation;
 
- applied mutation;
 
- validation;
 
- failure.
 

 
Do not expose hidden chain-of-thought.
 
Expose operation state and evidence.
 
### PAL-M6-005 — Monaco/editor integration
 
Reuse the existing editor lineage for:
 
 
- current file;
 
- proposed file;
 
- diff;
 
- applied state.
 

 
### PAL-M6-006 — Command palette
 
Expose user-controlled commands including:
 
 
- continue;
 
- inspect;
 
- propose;
 
- implement;
 
- validate;
 
- open file;
 
- show task;
 
- show authority;
 
- show diff;
 
- rollback where authorized.
 

 
### PAL-M6-007 — Observatory consolidation
 
Use existing observatory surfaces for:
 
 
- authority;
 
- repository;
 
- runtime;
 
- graph;
 
- lineage;
 
- memory/context;
 
- relationships;
 
- task state;
 
- activity.
 

 
### PAL-M6-008 — Unified voice/text session
 
Voice and text operate on the same Palaver session rather than creating parallel conversation histories.
 
### PAL-M6-009 — Interruptible voice
 
User interruption cancels pending speech cleanly.
 
Tool chatter is not synthesized.
 
Only appropriate user-facing output is sent through Envoy.
 
## Exit gate
 
One mobile browser session can:
 
 
- chat;
 
- stream a response;
 
- inspect files;
 
- view a diff;
 
- approve or request implementation;
 
- see validation;
 
- use voice without losing text session continuity.
 

  
# 24. PHASE P7 — Assurance, security, and operations
 
## Objective
 
Make Palaver safe enough to become the normal Savant development interface.
 
## Tasks
 
### PAL-M7-001 — Secret isolation
 
`/root/.env` values must never enter:
 
 
- browser payloads;
 
- model context;
 
- transcripts;
 
- tool output;
 
- source dumps;
 
- ordinary logs.
 

 
### PAL-M7-002 — Prompt-injection boundary
 
Repository text is data.
 
A file cannot grant itself tool permission or authority merely by containing instructions.
 
### PAL-M7-003 — Autonomy profiles
 
Support at least:
 `inspect propose implement ` 
Authority-sensitive and destructive operations remain separately gated.
 
### PAL-M7-004 — Resource budgets
 
Per-run controls include:
 
 
- model-request budget;
 
- token budget where measurable;
 
- command timeout;
 
- maximum command output;
 
- maximum context size;
 
- tool-call limit.
 

 
### PAL-M7-005 — Structured cancellation
 
The user can cancel:
 
 
- model generation;
 
- long read/search;
 
- process execution;
 
- queued mutation before commit.
 

 
### PAL-M7-006 — Trace redaction
 
Observability records useful metadata without storing secrets or unnecessarily copying sensitive file contents.
 
### PAL-M7-007 — Startup recovery
 
systemd restart restores Palaver service and persisted session state.
 
### PAL-M7-008 — Dependency health
 
Health identifies availability of:
 
 
- provider adapters;
 
- Coda;
 
- Niche;
 
- Envoy;
 
- Filament;
 
- session storage;
 
- repository access.
 

 
### PAL-M7-009 — Minimal attack surface
 
Default production bind:
 
`127.0.0.1`
 
Primary remote-development baseline:
 
SSH local forwarding.
 
Quick public tunnels are development convenience, not default trust boundaries.
 
## Exit gate
 
Palaver survives restart, keeps secrets isolated, rejects unauthorized mutations, enforces bounded execution, and remains usable through a private local-forwarded connection.
  
# 25. PHASE P8 — Shadow migration and permanent cutover
 
## Objective
 
Prove that Palaver can replace the external ChatGPT development workflow.
 
## Shadow test one — localized repair
 
Palaver must:
 
 
1. discover the live implementation;
 
2. identify the failure;
 
3. inspect dependencies;
 
4. perform the bounded correction;
 
5. validate syntax;
 
6. run one focused test;
 
7. report evidence.
 

 
## Shadow test two — cross-module integration
 
Palaver must:
 
 
1. retrieve authority;
 
2. inspect both modules;
 
3. preserve ownership;
 
4. implement integration;
 
5. validate one representative workflow;
 
6. preserve lineage.
 

 
## Shadow test three — source-dump-driven work
 
Palaver must:
 
 
1. locate the newest source dump;
 
2. retrieve relevant implementation;
 
3. distinguish historical evidence from current authority;
 
4. identify the next bounded task;
 
5. implement;
 
6. verify.
 

 
## Final cutover test
 
Resume the paused Coalesce work from its return-point documents.
 
This demonstrates that development continuity no longer depends on the external ChatGPT transcript.
 
## Exit gate
 
All three shadow workflows and the Coalesce-resumption test pass.
 
At that point Palaver becomes the default Savant development interface.
 
External ChatGPT use becomes optional consultation rather than the primary execution environment.
  
# 26. Twenty-seven required advanced enhancements
 
The permanent Palaver migration includes **27 substantive enhancements**.
 
They are divided into three groups of nine.
 
No enhancement exists merely to satisfy a count.
  
## 26.1 Intelligence and execution enhancements
 
### Enhancement 01 — Authority-aware context compiler
 
Context is assembled according to authority and task relevance rather than simple recency.
 
### Enhancement 02 — Typed local tool broker
 
Every tool is schema-defined, owner-aware, capability-classified, and policy-checked.
 
### Enhancement 03 — Persistent resumable sessions
 
Development state survives browser and server restarts.
 
### Enhancement 04 — Autonomy profiles
 
Inspect, proposal, and implementation modes change tool permissions without changing canonical authority.
 
### Enhancement 05 — Coda-backed atomic mutation transactions
 
Model-generated writes cannot bypass durable mutation ownership.
 
### Enhancement 06 — Optimistic concurrency protection
 
A proposed mutation is rejected when its inspected target changed before commit.
 
### Enhancement 07 — Immutable execution receipts
 
Important operations produce durable evidence containing identities and digests.
 
### Enhancement 08 — Deterministic execution replay
 
A development run can be reconstructed from task, context, tool, and mutation records.
 
### Enhancement 09 — Adaptive Opus model routing
 
The model is selected by capability and policy rather than hardcoded in Palaver.
  
## 26.2 Interaction and workstation enhancements
 
### Enhancement 10 — Streaming model responses
 
Users see useful output immediately rather than waiting for whole-response completion.
 
### Enhancement 11 — WebSocket live execution channel
 
Tool states, model states, cancellation, and interface events use a persistent bidirectional transport.
 
### Enhancement 12 — Unified command palette
 
Frequent developer operations are addressable without memorizing shell commands.
 
### Enhancement 13 — Integrated editor and diff projection
 
Current, proposed, and applied states are visible from the same Palaver workspace.
 
### Enhancement 14 — Observatory unification
 
Existing Palaver observatories become a coherent workstation rather than independent demo surfaces.
 
### Enhancement 15 — Live Niche task projection
 
Current task, blockers, readiness, dependencies, and completion evidence remain visible during development.
 
### Enhancement 16 — Incremental repository change stream
 
Palaver can update relevant file projections without rescanning the whole repository after every change.
 
### Enhancement 17 — Unified voice/text continuity
 
Voice is another modality of the same persistent Palaver session.
 
### Enhancement 18 — Mobile-first private workstation access
 
The development environment remains fully usable from Termux/browser over private forwarding.
  
## 26.3 Assurance and operations enhancements
 
### Enhancement 19 — Secret-isolation firewall
 
Secrets cannot be retrieved into ordinary model context.
 
### Enhancement 20 — Prompt-injection-resistant tool policy
 
Instructions contained in repository files cannot grant themselves execution authority.
 
### Enhancement 21 — Per-session cost and token budgets
 
Provider consumption becomes visible and bounded.
 
### Enhancement 22 — Provider circuit breakers
 
Repeated provider failures cause graceful route degradation rather than repeated stalls.
 
### Enhancement 23 — Capability health matrix
 
Palaver exposes live health for its required owner integrations.
 
### Enhancement 24 — Versioned protocol contracts
 
Frontend, Palaver, Opus, Coda, and other integration contracts evolve without silent semantic breakage.
 
### Enhancement 25 — Redacted structured tracing
 
Operational evidence remains useful without leaking sensitive contents.
 
### Enhancement 26 — Automatic startup/session recovery
 
systemd and persisted workspace state return Palaver to useful operation after a restart.
 
### Enhancement 27 — Shadow-mode cutover benchmarking
 
Palaver proves equivalence or superiority against representative ChatGPT-era workflows before permanent migration.
  
# 27. Provider-routing policy
 
Opus should normally use one model per ordinary step.
 
Multi-model work is reserved for cases that materially benefit from it, such as:
 
 
- difficult architecture adjudication;
 
- conflicting evidence;
 
- independent verification;
 
- uncertain technical diagnosis;
 
- explicit project-owner request.
 

 
Do not multiply API calls merely because multiple keys exist.
 
Provider diversity exists for capability, resilience, and informed selection.
  
# 28. Context policy
 
Do not send the entire repository on every turn.
 
The context compiler should retrieve a bounded packet containing only what is needed.
 
Candidate packet:
 `session identity task identity current user directive relevant accepted authority relevant decisions relevant canon relevant implementation direct dependencies direct dependents relevant return point recent tool receipts bounded recent conversation ` 
Every substantial context item should retain source identity.
  
# 29. Filesystem policy
 
Default root:
 
`/root/savant-runtime`
 
All paths used by tools must resolve absolutely.
 
Reads outside the runtime require explicit policy.
 
Writes outside the runtime require explicit authorization and appropriate owner.
 
Symlink traversal must not silently escape permitted roots.
  
# 30. Shell policy
 
Do not expose:
 
`bash -c <arbitrary-model-string>`
 
as the default model tool.
 
Use typed subprocess execution:
 `executable arguments[] working_directory timeout environment_allowlist ` 
Shell wrappers may remain for existing Savant commands when they are known, inspected, and intentionally invoked.
  
# 31. Mutation policy
 
For source replacement:
 
 
1. read current target;
 
2. verify authority;
 
3. inspect dependencies/dependents proportionately;
 
4. create complete replacement or deterministic patch;
 
5. re-check current digest;
 
6. invoke Coda;
 
7. write atomically;
 
8. emit receipt;
 
9. syntax/compile;
 
10. focused test;
 
11. integration/startup check where applicable.
 

 
Do not claim success before steps required by the specific task have evidence.
  
# 32. Niche integration
 
Palaver must not invent task priority.
 
Niche owns:
 
 
- task discovery;
 
- priority;
 
- blockers;
 
- readiness;
 
- task transitions;
 
- leases;
 
- completion state;
 
- Masterplan projection.
 

 
When the user says:
 
`Continue.`
 
Palaver should first determine whether a bound active task exists.
 
If not, Palaver asks Niche for the highest-priority ready work permitted by current authority.
  
# 33. Coda integration
 
Coda remains the operational owner of authorized durable mutation.
 
The ideal tool relationship is:
 `Palaver   → mutation proposal   → Coda   → transaction   → receipt   → Palaver ` 
Palaver may expose the resulting diff and receipt.
 
It does not independently become the durable mutation owner.
  
# 34. Opus integration
 
Opus becomes Palaver's exclusive normal AI/provider execution plane.
 
Opus handles:
 
 
- provider discovery;
 
- credential availability;
 
- model selection;
 
- provider request formatting;
 
- provider response normalization;
 
- retries;
 
- fallback;
 
- latency policy;
 
- usage;
 
- provider lineage.
 

 
Direct provider calls in Palaver become deprecated compatibility paths.
  
# 35. Envoy integration
 
Envoy owns:
 
 
- persona;
 
- voice identity;
 
- pronunciation;
 
- speaking style;
 
- accent;
 
- presentation intent.
 

 
Palaver owns the dialogue.
 
Opus executes external provider requests.
 
No future voice implementation should collapse these responsibilities.
  
# 36. Filament integration
 
Filament should remain responsible for projection execution where the current architecture assigns that role.
 
Palaver's interface consumes projections.
 
Palaver should not duplicate every repository/graph visualization algorithm merely because it displays the result.
  
# 37. Notary integration
 
Do not make an incomplete Notary implementation a cutover blocker.
 
Initial Palaver assurance may rely on existing deterministic validators and receipts.
 
As Notary's verified contract becomes available, route suitable:
 
 
- evidence;
 
- verification;
 
- attestation;
 

 
through Notary rather than duplicating that authority inside Palaver.
  
# 38. Splyce integration
 
The permanent Palaver interface should progressively reuse the accepted shared UI substrate.
 
Do not rewrite the working next-generation UI merely for architectural symmetry.
 
Use compatibility-first adoption.
  
# 39. Coalesce relationship
 
Coalesce remains paused during Palaver migration.
 
Its architecture and return-point records remain preserved.
 
After successful Palaver cutover, Coalesce is the first major resumed development program.
 
That provides a real proof that Palaver can resume complex Savant work from server-resident authority and documentation without relying on an external chat transcript.
  
# 40. MCP interoperability policy
 
MCP may be implemented later as a boundary adapter.
 
Permitted uses:
 
 
- expose selected read-only Savant resources;
 
- expose explicitly approved Palaver tools;
 
- consume narrowly approved external tools;
 
- connect compatible IDE or AI clients.
 

 
MCP does not become:
 
 
- task authority;
 
- ontology;
 
- canon;
 
- ownership graph;
 
- mutation authority;
 
- Savant internal orchestration.
 

  
# 41. OpenAI Agents SDK policy
 
Do not make the OpenAI Agents SDK the canonical Palaver/Opus runtime.
 
It may be evaluated as an optional Opus-specific adapter when a workflow benefits from provider-native:
 
 
- tool loops;
 
- sessions;
 
- guardrails;
 
- tracing;
 
- sandbox/workspace features.
 

 
The canonical Savant tool and owner contracts remain provider-neutral.
  
# 42. Data persistence strategy
 
Persist only what is required for continuity and evidence.
 
Recommended persistent classes:
 
 
- session metadata;
 
- conversation records;
 
- task binding;
 
- context-source references;
 
- tool receipts;
 
- Coda mutation receipts;
 
- user workspace state;
 
- model usage summaries;
 
- replay metadata.
 

 
Do not duplicate canonical repository contents into a second Palaver database.
 
File content should normally remain source-addressed.
  
# 43. Session-store strategy
 
Use the smallest durable mechanism that satisfies current needs.
 
A local SQLite-backed session projection is acceptable when:
 
 
- it stores Palaver runtime/session state;
 
- it does not become canon;
 
- it does not duplicate authoritative Savant primitives;
 
- schema/version is explicit;
 
- transactions are enabled;
 
- recovery is deterministic.
 

 
Do not introduce a network database merely for Palaver chat persistence.
  
# 44. Same-origin production topology
 
Target:
 `127.0.0.1:8787         │         └── PALAVER              ├── built frontend              ├── /api/*              ├── /ws/*              └── local owner integrations ` 
Default production remote use:
 `Android / workstation       │       └── SSH local forward               │               └── 127.0.0.1:8787 on Ubuntu ` 
This removes the requirement for a permanent Vite development server and public quick tunnel.
  
# 45. systemd target
 
Long-term default:
 
`palaver.service`
 
It should:
 
 
- use an isolated Python environment;
 
- load secrets from `/root/.env` through process environment;
 
- bind loopback;
 
- restart on failure;
 
- use a fixed working directory;
 
- write structured operational logs;
 
- avoid printing secrets.
 

 
Separate services remain only when a genuine owner/runtime boundary requires them.
  
# 46. Development versus production
 
Development mode may support:
 
 
- Vite dev server;
 
- hot reload;
 
- verbose diagnostics;
 
- live filesystem watching.
 

 
Production/default mode should use:
 
 
- built static frontend;
 
- one Palaver ASGI server;
 
- stable systemd process;
 
- no automatic source reload;
 
- bounded logs;
 
- private access.
 

 
Do not conflate development hot reload with reliable runtime operation.
  
# 47. Security boundary
 
The completed system must deny by default:
 
 
1. arbitrary filesystem mutation;
 
2. arbitrary shell evaluation;
 
3. secret export;
 
4. task transition outside Niche;
 
5. AI-provider bypass outside Opus;
 
6. durable mutation bypass outside Coda;
 
7. authority mutation without owner;
 
8. evidence promotion without proper authority;
 
9. unrestricted remote network exposure.
 

  
# 48. Secret handling
 
Secrets may be used internally by provider adapters.
 
Secret values must not appear in:
 
 
- model messages;
 
- browser state;
 
- session transcript;
 
- execution receipts;
 
- normal debug logs;
 
- source dumps;
 
- error payloads.
 

 
Provider availability should expose:
 `configured: true ` 
not the credential.
  
# 49. Observability
 
Palaver should expose enough evidence to answer:
 
 
- what task is active?
 
- what model/provider was selected?
 
- what tool executed?
 
- what files were read?
 
- what mutation occurred?
 
- what validator ran?
 
- what failed?
 
- what remains blocked?
 
- what did the operation cost?
 
- can the task be replayed?
 

 
Observability does not define truth.
 
It records execution.
  
# 50. Completion evidence
 
A coding task completed through Palaver should be able to produce a compact receipt such as:
 `task files inspected authority consulted files changed before/after digests syntax result focused test result integration result remaining blockers provider/model lineage ` 
No hidden claim of success is sufficient.
  
# 51. Performance strategy
 
Optimize after correctness.
 
Primary performance targets:
 
 
- streaming first token quickly;
 
- avoid rescanning entire repository;
 
- reuse bounded indexes/projections;
 
- keep provider clients warm;
 
- perform independent reads concurrently when safe;
 
- limit tool-output size;
 
- cache disposable projections only where invalidation is known;
 
- cancel obsolete work when the user changes direction.
 

 
Do not trade authority correctness for latency.
  
# 52. Failure model
 
Palaver must distinguish at least:
 
 
- provider unavailable;
 
- provider timeout;
 
- context compilation failure;
 
- tool validation failure;
 
- policy rejection;
 
- filesystem read failure;
 
- mutation conflict;
 
- mutation failure;
 
- syntax failure;
 
- focused test failure;
 
- integration failure;
 
- external owner unavailable;
 
- session recovery failure.
 

 
Each failure should name the next actionable blocker.
  
# 53. Cancellation and interruption
 
The user must be able to cancel active work.
 
Cancellation should propagate to:
 
 
- model streaming;
 
- pending tool operations;
 
- subprocesses;
 
- voice output.
 

 
An atomic Coda transaction already committed is not silently reversed by cancellation.
 
Rollback remains an explicit operation.
  
# 54. Compatibility strategy
 
Compatibility is temporary.
 
Allowed compatibility mechanisms:
 
 
- API aliases;
 
- adapters;
 
- launchers;
 
- symlinks;
 
- protocol translations;
 
- legacy route wrappers;
 
- UI proxy paths.
 

 
Every compatibility path should have known consumers.
 
Retire only after reverse-dependency evidence.
  
# 55. Migration non-goals
 
Do not:
 
 
- rebuild Savant while building Palaver migration infrastructure;
 
- migrate Coalesce simultaneously;
 
- rewrite every Exile;
 
- replace Niche;
 
- replace Coda;
 
- replace Opus;
 
- replace Envoy;
 
- create a new authority database;
 
- create another task graph;
 
- create another memory authority;
 
- expose unrestricted root shell;
 
- make a public unauthenticated AI development endpoint;
 
- add a large orchestration platform merely because it is fashionable.
 

  
# 56. First post-cutover development sequence
 
After Palaver becomes the default interface:
 
 
1. resume Coalesce identity migration;
 
2. verify its architecture return points;
 
3. complete current application extraction;
 
4. perform the future 81-to-27 Coalesce migration as a separate bounded task if still authoritative;
 
5. return to the accepted Niche Masterplan priority queue.
 

 
Palaver itself does not redefine this order when Niche authority differs.
  
# 57. Migration artifacts
 
The program should eventually produce at minimum:
 `Palaver canonical contracts Palaver tool schemas Palaver execution policy Palaver canonical runtime server Opus inference bridge Coda mutation bridge persistent session store context compiler replay/receipt model same-origin frontend build systemd service compatibility adapters cutover evidence ` 
Exact paths must be derived from the live implementation before each change.
 
Do not reconstruct files from this plan.
  
# 58. Dependency admission record
 
Every admitted external dependency must record:
 `name owner purpose source version constraint license security review state fallback failure mode removal strategy consumers ` 
Do not make `requirements.txt` or a lockfile the only record of why a dependency exists.
  
# 59. Quality gate for provider adapters
 
Every provider adapter must demonstrate:
 
 
- credentials remain private;
 
- one normal request;
 
- one streaming request where supported/required;
 
- normalized error handling;
 
- timeout;
 
- usage extraction where available;
 
- provider/model lineage;
 
- no Palaver-owned provider semantics.
 

  
# 60. Quality gate for tool broker
 
The broker passes when:
 
 
- valid read succeeds;
 
- escaping filesystem root is rejected;
 
- secret-target read into AI context is rejected;
 
- raw unbounded shell request is rejected;
 
- allowed subprocess invocation succeeds;
 
- mutation requires Coda;
 
- stale mutation is rejected;
 
- receipt is emitted.
 

 
Use focused tests only.
  
# 61. Quality gate for sessions
 
Session implementation passes when:
 
 
- turn one persists;
 
- server restarts;
 
- turn two resumes;
 
- active task survives;
 
- recent tool receipt survives;
 
- context remains bounded;
 
- a new independent session does not inherit unrelated state.
 

  
# 62. Quality gate for interface
 
The production Palaver UI passes when the same mobile browser can:
 
 
- connect privately;
 
- open/resume a session;
 
- stream text;
 
- inspect repository files;
 
- view a diff;
 
- see active task;
 
- trigger an allowed implementation;
 
- observe validation;
 
- interrupt generation;
 
- switch between text and voice without changing session identity.
 

  
# 63. Shadow-mode acceptance benchmark
 
Before permanent cutover, compare Palaver against the external-chat workflow on representative tasks.
 
Measure:
 
 
- manual copy/paste required;
 
- number of unnecessary user interventions;
 
- incorrect path assumptions;
 
- authority violations;
 
- failed file edits;
 
- redundant validation;
 
- time to useful completion;
 
- recovery after interruption;
 
- ability to prove success.
 

 
Permanent cutover requires Palaver to remove the dependency on manual filesystem transcription.
  
# 64. Enterprise completion definition
 
The migration is complete when:
 
 
- Palaver is the normal human-facing development interface;
 
- Palaver runs persistently on Ubuntu;
 
- one canonical Palaver server exists;
 
- the production interface and API share an origin;
 
- persistent sessions survive restarts;
 
- context is compiled from live Savant state;
 
- Niche supplies task governance;
 
- Opus supplies AI/provider execution;
 
- Coda supplies durable authorized mutation;
 
- Envoy supplies persona/voice;
 
- external capabilities preserve their owners;
 
- secrets remain server-side;
 
- model tool calls are locally policy-enforced;
 
- filesystem operations use absolute bounded paths;
 
- mutations are atomic and receipted;
 
- provider failures degrade gracefully;
 
- voice and text share conversation state;
 
- at least three shadow workflows pass;
 
- Coalesce can be resumed from server-resident return points;
 
- no external ChatGPT transcript is required for ordinary continuation.
 

 
At this milestone, Savant is being built from inside Savant.
  
# 65. Immediate implementation sequence
 
When this migration begins, perform only:
 `1. PAL-M0 baseline 2. PAL-M1 contracts 3. PAL-M2 canonical runtime 4. PAL-M3 tool/Coda plane 5. PAL-M4 Opus provider plane 6. PAL-M5 sessions/context 7. PAL-M6 workstation/voice 8. PAL-M7 assurance/operations 9. PAL-M8 shadow/cutover ` 
Do not start by rebuilding the frontend.
 
Do not start by installing every candidate dependency.
 
Do not start by giving a model unrestricted shell access.
 
The first engineering act is to preserve and classify the existing working Palaver implementation.
  
# 66. Current known uncertainty
 
The source dump is a source/canon projection, not proof of every live runtime artifact.
 
Generated files, caches, large graph outputs, environments, and other excluded material may exist on the Ubuntu filesystem without appearing in the dump.
 
Therefore every implementation task begins by reading the current live implementation.
 
Historical Palaver material also exists alongside newer architecture.
 
Historical implementation is evidence.
 
It is not automatically current authority.
 
Formal Palaver/related Exile capability manifests may lag actual code.
 
Do not upgrade those manifests from inference alone.
  
# 67. Research basis
 
Contemporary dependency research for this plan considered official documentation or official repositories for:
 
 
- FastAPI;
 
- Uvicorn;
 
- Pydantic-based API validation;
 
- OpenAI Python/API tooling;
 
- OpenAI Agents SDK;
 
- Anthropic Python SDK;
 
- Google Gen AI Python SDK;
 
- Model Context Protocol.
 

 
The architectural decision is intentionally conservative:
 
 
- use mature typed ASGI infrastructure for Palaver;
 
- use official provider SDKs behind Opus;
 
- keep Savant's own owner/tool/task architecture authoritative;
 
- treat provider-agent frameworks and MCP as optional adapters;
 
- do not vendor public repository snippets when a maintained official package provides the capability;
 
- verify licenses and version compatibility at admission time.
 

  
# 68. Final architectural rule
 
The permanent system is not:
 `Palaver = giant AI that owns Savant ` 
It is:
 `Palaver = conversation and development control plane  Niche = task governance Opus = intelligence/API orchestration Coda = durable mutation Envoy = persona/voice Filament = projection Notary = evidence/attestation other owners = their established jurisdictions ` 
The model proposes.
 
Savant decides what is permitted.
 
Owners perform their operations.
 
Receipts prove what happened.
 
The filesystem is live.
 
Sessions persist.
 
The user can continue from inside the server.
 
That is the cutover target.
