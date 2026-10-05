# niche taskboard

## identity

`niche taskboard` is the local human control surface for Niche task
governance.

owner: `exile:niche`

authority effect: `none` for projections.

User-authorized task mutations are delegated to Niche's existing
authoritative task store.

## purpose

The taskboard turns Niche's existing persistent living-task
implementation into a practical day-to-day task engine without creating
a second roadmap, task database, or planning authority.

It continuously answers:

1.  what work exists;
2.  what can be executed now;
3.  what is blocking progress;
4.  what deserves attention next.

## authority boundary

The authoritative task store remains the existing Niche SQLite task
store managed by:

`runtime/living_task.py`

The taskboard does not create task authority by rendering:

-   cards;
-   queues;
-   graphs;
-   scores;
-   deadlines;
-   critical paths;
-   search results;
-   progress values;
-   dashboard metrics.

Those are deterministic or operational projections.

Task mutations performed through the UI update the same Niche task rows
and append an immutable hash-chained task event.

Completion remains evidence-gated.

Terminal task history remains immutable.

## composition

``` text
niche
└── runtime/living_task.py
    authoritative task primitives
    direct dependencies
    immutable hash-chained history
    readiness
    masterplan projection
        ↓
   runtime/task_engine.py
    operational task facade
    amendments
    scheduling metadata
    leases
    search
    critical path
    focus ranking
    workload/deadline projections
        ↓
   apps/taskboard/server.py
    local HTTP API
        ↓
   apps/taskboard/
    overview
    board
    focus queue
    dependency graph
    history
    task editor
```

## extension metadata

Taskboard metadata is stored in the existing task `extension_slots`
under:

``` text
niche.taskboard
```

Supported fields:

-   `title`;
-   `labels`;
-   `notes`;
-   `assignee`;
-   `due_at`;
-   `start_at`;
-   `lease_until`;
-   `estimate_minutes`;
-   `checklist`.

No secondary metadata database is created.

## implemented capabilities

1.  authoritative task creation through Niche;
2.  evidence-gated completion;
3.  immutable hash-chained task history;
4.  direct dependency storage;
5.  dependency-cycle prevention;
6.  reverse-dependency projection;
7.  transitive-dependency projection;
8.  executable ready queue;
9.  newly-unblocked projection;
10. bottleneck/fan-out projection;
11. deterministic critical-path projection;
12. priority/impact/deadline focus ranking;
13. deadline tracking;
14. overdue detection;
15. task estimates;
16. assignee metadata;
17. bounded leases;
18. explicit lease release;
19. labels;
20. notes;
21. checklist metadata;
22. SQLite FTS5 search when available;
23. deterministic substring search fallback;
24. status filtering;
25. priority filtering;
26. label filtering;
27. owner filtering;
28. assignee filtering;
29. workload projection;
30. progress projection;
31. health projection;
32. Kanban interface;
33. drag-to-transition workflow;
34. focus interface;
35. dependency graph interface;
36. immutable-history interface;
37. task detail/editor interface;
38. keyboard shortcuts;
39. responsive UI;
40. automatic local refresh;
41. localhost-first binding;
42. restrictive browser security headers;
43. bounded JSON request bodies;
44. framework-free browser runtime;
45. no CDN dependency;
46. rebuildable search index;
47. source-task authority preserved;
48. no second Masterplan authority.

## focus score

Focus score is a scheduling projection.

It does not outrank authority.

Inputs currently include:

-   task priority;
-   downstream fan-out;
-   overdue state;
-   near-term deadline pressure.

The score may change without changing canonical task meaning.

## critical path

Critical-path calculation uses:

-   direct dependency edges;
-   task estimates;
-   current completion state.

Completed tasks contribute zero remaining duration.

When the task graph contains a cycle, critical-path calculation reports
itself unavailable rather than inventing an ordering.

## search

When SQLite FTS5 is available, Niche builds a disposable search index
from current tasks.

Indexed fields:

-   task id;
-   purpose;
-   owner;
-   jurisdiction;
-   labels;
-   notes.

If FTS5 is unavailable or rejects a query, Niche falls back to
deterministic case-insensitive substring search.

The search index is rebuildable and non-authoritative.

## interface views

### overview

Shows:

-   global progress;
-   ready work;
-   active work;
-   blockers;
-   overdue tasks;
-   critical path;
-   bottlenecks.

### board

Shows task state as draggable work columns.

Moving a card requests a Niche task transition.

### focus

Shows executable work ordered by derived attention score.

### graph

Shows direct task dependency topology.

The graph is never written back as task authority.

### history

Shows Niche's immutable hash-chained event history.

## generic amendments

The taskboard may amend:

-   purpose;
-   priority;
-   completion condition;
-   affected instances;
-   compatibility obligations;
-   validation budget;
-   blockers;
-   implementation references;
-   decomposition children;
-   direct dependencies;
-   taskboard extension metadata.

Generic amendment does not rewrite:

-   task identity;
-   task owner;
-   task jurisdiction;
-   authority basis.

## dependency rules

Dependencies remain direct primitives.

Reverse and transitive relationships are derived.

Dependency amendments:

1.  resolve referenced tasks;
2.  reject unknown task references;
3.  reject self-dependency;
4.  calculate the prospective graph;
5.  reject cycles before persistence;
6.  append an immutable amendment event after successful mutation.

## lease semantics

A task may be leased only when:

-   no explicit blocker exists;
-   no direct dependency remains unsatisfied.

Lease state records:

-   assignee;
-   expiration timestamp;
-   task state `leased`.

Lease release returns the task to `ready`.

Lease state does not change authority or priority.

## completion

Completion continues to use the existing Niche rule:

``` text
completed requires evidence or receipt
```

The taskboard does not bypass it.

## security

Default bind:

``` text
127.0.0.1
```

The browser surface uses:

-   no remote JavaScript;
-   no remote CSS;
-   no CDN;
-   no tracking;
-   no third-party browser runtime.

HTTP responses apply:

-   content security policy;
-   frame denial;
-   MIME sniff prevention;
-   no-referrer policy;
-   no-store caching.

Mutation payloads:

-   require JSON;
-   are size bounded.

## dependencies

Mandatory:

-   Python standard library;
-   existing Niche `living_task.py`;
-   SQLite.

Optional:

-   SQLite FTS5.

No new mandatory package is introduced.

## failure behavior

Missing task:

``` text
reject explicitly
```

Invalid state:

``` text
reject explicitly
```

Unknown dependency:

``` text
reject explicitly
```

Dependency cycle:

``` text
reject before persistence
```

Blocked lease:

``` text
reject explicitly
```

Completion without receipt:

``` text
reject through Niche's existing completion gate
```

FTS5 unavailable:

``` text
fall back to substring search
```

Existing task-graph cycle:

``` text
suppress critical path and expose cycle
```

UI/API error:

``` text
return structured error without changing task authority
```

## extension apertures

Future compatible extensions include:

-   calendar projection;
-   recurring-task proposals;
-   notification projection;
-   saved views;
-   release dashboards;
-   milestone dashboards;
-   Palaver embedding;
-   Splyce presentation specialization;
-   Opus execution dispatch;
-   Coda implementation-receipt linking;
-   Scrybe task-context hydration;
-   Notary completion-evidence inspection;
-   architecture-to-task delta proposals;
-   event streaming;
-   multi-user lease policy.

Every extension must continue to use Niche as the single task-governance
owner.
