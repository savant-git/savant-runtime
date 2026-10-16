# COALESCE — ARCHITECTURE CANON AND IMPLEMENTATION RETURN POINT

Status: ACCEPTED DESIGN AUTHORITY
System: Savant Runtime
Component: Coalesce
Identity: `prodigal:modus:coalesce`
Owner: `exile:modus`
Directive date: 2026-08-11

Canonical runtime root:

`/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/segue/prodigals/coalesce`

Primary authority:

`/root/savant-runtime/COALESCE_COMPOSITION_CONTRACT.md`

Migration plan:

`/root/savant-runtime/COALESCE_SLIVER_MIGRATION_PLAN.md`

Historical target compatibility record:

`/root/savant-runtime/COALESCE_27_PRIMITIVE_TARGET.md`

---

# 1. PURPOSE

This document is the canonical architectural return point for Coalesce.

It preserves:

- identity;
- ownership;
- composition boundaries;
- historical implementation evidence;
- migration lineage;
- current terminology;
- implementation direction;
- completion criteria.

It supersedes conflicting portions of earlier Coalesce architecture documents.

Historical implementation facts remain historical evidence.

They are not rewritten to imply that Slivers and Alloys existed before their acceptance.

---

# 2. IDENTITY

Coalesce is:

`prodigal:modus:coalesce`

Owner:

`exile:modus`

Coalesce is a Prodigal.

Coalesce is not an Exile.

Coalesce is not a new ontology tier.

Coalesce is not an independent authority domain.

Coalesce is Savant's reusable application-composition system beneath Modus.

---

# 3. CANONICAL VOCABULARY

## Coalesce

The application-composition system.

## Sliver

A reusable primary application capability.

## Sliver Pool

The extensible canonical pool of reusable Slivers.

## Alloy

An application assembled by Coalesce.

## Alloy Recipe

The declarative composition specification from which an Alloy is materialized.

---

# 4. CANONICAL SHAPE

The canonical architecture is:

`Sliver Pool`

→ capability requirements

→ compatible Sliver selection

→ `1–9 Sliver instances`

→ configuration

→ typed segues

→ adapters/providers where required

→ Alloy Recipe

→ Alloy

→ projection.

---

# 5. HARD ALLOY LIMIT

An Alloy contains:

`1–9 Slivers`

Nine is the maximum number of primary Slivers in one Alloy.

This supersedes the historical fixed native-piece targets.

The limit applies to primary application composition.

It does not count legitimate lower-order reusable elements referenced beneath a Sliver.

The limit MUST NOT be bypassed by:

- wrapper Slivers hiding additional primary Slivers;
- recursive Sliver bundles;
- treating another Alloy as a Sliver;
- embedding complete Exiles;
- anonymous component collections.

If a product cannot remain coherent within nine Slivers, it should normally become multiple federated Alloys.

---

# 6. SLIVER POOL CARDINALITY

The Sliver Pool has no fixed canonical size.

It may contain:

- fewer than 27 Slivers;
- exactly 27 Slivers;
- more than 27 Slivers.

Pool cardinality is not the design objective.

The objective is:

**maximum useful application coverage with minimum semantic redundancy while requiring no more than nine Slivers per Alloy.**

---

# 7. SUPERSESSION OF THE 27-PRIMITIVE TARGET

The previous target:

`27 canonical Coalesce-native primitives`

is superseded.

The historical three-family × nine-piece design remains implementation history and architectural provenance.

It is no longer the final target.

The accepted future model is:

`extensible Sliver Pool + <=9 Slivers per Alloy`.

No source history should be rewritten to hide the previous 27-piece decision.

---

# 8. HISTORICAL 81-PIECE IMPLEMENTATION

Verified historical Coalesce development included an 81-piece model.

Historical implementation evidence included:

- nine service families;
- nine pieces per service;
- recipes;
- composition execution;
- Filament projection;
- composition digests;
- reusable application behavior.

That implementation remains migration evidence.

It must not be deleted merely because the canonical grammar has changed.

Every useful historical capability requires explicit migration disposition.

---

# 9. HISTORICAL SERVICE FAMILIES

Historical families included:

- temporal;
- record;
- discovery;
- lens;
- gridd;
- workspace;
- narrative;
- shell;
- substrate.

These names describe historical implementation organization.

They are not required future Sliver families.

Their functionality must be classified semantically.

---

# 10. HISTORICAL CAPABILITY DISPOSITION

Every historical Coalesce piece must eventually receive one explicit disposition:

- `sliver`;
- `merge_into_sliver`;
- `parameter`;
- `mode`;
- `prodigal_instance`;
- `quirk_instance`;
- `adapter`;
- `provider`;
- `segue`;
- `projection`;
- `engine`;
- `compatibility`;
- `superseded`;
- `historical_only`.

No useful behavior disappears silently.

---

# 11. SLIVER DEFINITION

A Sliver is a coherent reusable application-scale capability.

A Sliver is not:

- a button;
- a single field;
- one CSS component;
- one endpoint;
- one source-specific record type;
- an entire application;
- an Exile.

A Sliver SHOULD provide one broad but cohesive application capability.

---

# 12. SLIVER REQUIREMENTS

Every canonical Sliver should expose:

- stable identity;
- version;
- status;
- semantic capability identifiers;
- public contract;
- inputs;
- outputs;
- ports;
- configuration;
- required dependencies;
- optional dependencies;
- declared effects;
- compatibility;
- conflicts;
- supported typed segues;
- provenance;
- lineage.

---

# 13. ORTHOGONALITY

Slivers should maximize:

- reuse;
- semantic distinction;
- configurability;
- interoperability;
- compositional leverage.

Slivers should minimize:

- duplicated capability;
- source-specific behavior;
- hidden state;
- framework coupling;
- redundant implementations.

Before creating a new Sliver, determine whether the behavior can be represented by:

- configuration;
- parameterization;
- Prodigal instance;
- Quirk instance;
- adapter;
- provider;
- typed segue;
- projection.

---

# 14. MINIMAL SUFFICIENT ALLOY

Coalesce should construct the smallest sufficient valid Alloy.

Given equivalent capability coverage, prefer:

1. fewer Slivers;
2. less overlap;
3. fewer required external dependencies;
4. clearer ownership;
5. stronger deterministic behavior;
6. lower hidden coupling.

---

# 15. CAPABILITY-DRIVEN COMPOSITION

Coalesce should compose from semantic capability requirements rather than source filenames.

Conceptually:

`requested capabilities`

→ `Sliver capability index`

→ `candidate Slivers`

→ `compatibility constraints`

→ `minimal sufficient selection`

→ `Alloy Recipe`.

---

# 16. SELECTION AS A BOUNDED COVERAGE PROBLEM

Automatic Sliver selection may be treated as constrained set cover.

Required conditions:

- all mandatory capabilities covered;
- selected Slivers compatible;
- dependencies satisfied;
- authority boundaries valid;
- projection requirements satisfied;
- selected count <= 9.

The first implementation should use the simplest deterministic algorithm sufficient for the actual pool.

Advanced solvers are optional.

---

# 17. ENGINE VERSUS SLIVER

Universal Coalesce functionality belongs to Coalesce itself.

Engine responsibilities include:

- Recipe parsing;
- Sliver registry resolution;
- capability matching;
- count enforcement;
- contract validation;
- binding;
- lifecycle coordination;
- deterministic planning;
- composition digest generation;
- composition receipt generation.

These functions do not consume Sliver slots.

---

# 18. PRODIGALS

Prodigals are valid lower-order reusable composition substance where their contracts permit reuse.

Preferred model:

`canonical Prodigal`

→ `instance`

→ `Sliver`

→ `Alloy`.

Do not copy Prodigal source into Alloy-specific implementations.

Prodigal instances retain:

- identity;
- owner;
- parameters;
- lineage;
- provenance;
- dependencies;
- dependents.

---

# 19. QUIRKS

Quirks are valid lower-order reusable behavior.

They may support Sliver capabilities through instances.

Typical uses include:

- filtering;
- normalization;
- transformation;
- ranking;
- formatting;
- localized interaction behavior.

Do not duplicate Quirk substance inside Slivers when a reusable instance is available.

---

# 20. LOWER-ORDER INSTANCE COUNTING

Prodigal and Quirk instances do not count as primary Sliver slots.

They remain graph-visible dependencies.

This rule must never be used to hide additional primary Slivers.

The nine-Sliver limit governs primary Alloy application capability composition.

---

# 21. EXILE BOUNDARY

Exiles cannot be constituents of an Alloy.

An Exile must not be:

- embedded;
- instantiated as Alloy-owned substance;
- copied into a Sliver;
- converted into a Sliver;
- treated as an internal Alloy module.

If an Alloy requires an Exile-owned capability, it must call that capability through an authorized external boundary.

Canonical shape:

`Alloy`

→ `Sliver`

→ `authorized interface`

→ `Exile`.

Calling an Exile does not make the Exile part of the Alloy.

---

# 22. ADAPTERS

Adapters translate between otherwise incompatible representations or contracts.

Prefer:

`Sliver A -> adapter -> Sliver B`

over application-specific modification of either Sliver.

Adapters:

- remain reusable;
- remain graph-addressable;
- preserve provenance;
- do not become new authority.

---

# 23. PROVIDERS

Providers expose external capability or data without transferring ownership.

A provider should declare:

- identity;
- capability;
- contract;
- availability;
- provenance where relevant;
- failure state.

External services do not automatically become Slivers.

---

# 24. TYPED SEGUES

Sliver relationships must be explicit.

Typed relationships may include:

- feeds;
- transforms;
- queries;
- observes;
- controls;
- projects;
- validates;
- selects;
- decorates;
- adapts.

Hidden coupling is prohibited.

---

# 25. PORTS

A Sliver should expose semantic ports such as:

- input;
- output;
- state;
- events;
- commands;
- queries;
- selection;
- provider;
- projection.

Ports define attachment boundaries.

Implementation internals remain private.

---

# 26. ALLOY RECIPE

An Alloy Recipe defines Alloy structure.

A Recipe should contain:

- Alloy ID;
- Recipe version;
- selected Sliver IDs;
- Sliver instance IDs;
- parameters;
- bindings;
- typed segues;
- adapters;
- providers;
- authorized external calls;
- projection targets;
- policy.

A Recipe references canonical Slivers.

It does not copy implementation.

---

# 27. ALLOY IDENTITY

An Alloy has identity distinct from the identity of its Slivers.

The same Sliver may participate in multiple Alloys.

The same Sliver may appear with different legitimate configuration.

An Alloy's identity should be recoverable from its Recipe and referenced canonical composition state.

---

# 28. COMPOSITION DIGEST

Coalesce retains the historical composition-digest principle.

A deterministic semantic digest should derive from:

- Recipe version;
- Sliver identities;
- Sliver versions;
- significant parameters;
- typed segues;
- adapters;
- provider/interface identities;
- projection identity.

Volatile telemetry should not alter semantic identity.

---

# 29. COMPOSITION RECEIPT

Materialization should be capable of producing a receipt containing:

- Alloy ID;
- Recipe ID;
- composition digest;
- Sliver IDs;
- versions;
- instance IDs;
- configuration digests;
- dependency summary;
- external calls;
- projection;
- degraded capabilities;
- warnings.

Receipts are evidence.

They are not separate architecture authority.

---

# 30. DETERMINISM

Given identical semantic inputs and policy, Coalesce should derive the same composition.

Relevant inputs include:

- requested capabilities;
- Sliver Pool version;
- compatibility graph;
- Recipe;
- configuration;
- availability state.

Filesystem enumeration order must not alter composition semantics.

---

# 31. REPLAY

A historical Alloy execution should retain enough metadata to reconstruct semantic composition.

Replay identity should include:

- Recipe;
- Recipe version;
- Sliver identities;
- Sliver versions;
- configuration;
- relevant provider/interface versions;
- relevant input digest where required.

Replay does not require duplication of canonical substance.

---

# 32. APPLICATION PROJECTION

An Alloy is not its UI.

Projection targets may include:

- Filament;
- browser;
- API;
- terminal;
- mobile;
- desktop;
- report;
- embedded surface.

Canonical application semantics should not depend exclusively on one presentation framework.

---

# 33. FILAMENT RELATIONSHIP

Filament remains the verified historical Coalesce presentation/projection integration path unless stronger authority supersedes it.

Historical integration paths include:

`/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/filament/runtime/filament_projection.py`

and:

`/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/filament/interface/api/coalesce_server.py`

Canonical ownership:

Coalesce owns composition.

Filament owns its legitimate projection behavior.

Neither subsumes the other.

---

# 34. HISTORICAL COALESCE UI

Historical Coalesce interface code has existed beneath:

`/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/segue/prodigals/coalesce/static/public/`

Historical UI functionality is implementation evidence.

It must not become the semantic definition of future Slivers.

---

# 35. DATA NEUTRALITY

Generic Slivers must remain domain-neutral by default.

Do not embed application-specific source substance such as:

- Mayorgate data;
- Viscera data;
- Palaver conversation data;
- fixed source schemas;
- application-specific sample records.

Correct flow:

`source`

→ authorized adapter/provider

→ neutral representation

→ Sliver composition.

---

# 36. STATE

Runtime application state does not automatically become Savant authority.

Examples:

- current selection;
- active query;
- bookmarks;
- notes;
- sort order;
- viewport;
- open panel;
- active lens;
- comparison tray;
- temporary editor state.

Every persistent state channel should preserve ownership and authority distinction.

---

# 37. EVENTS

Slivers may communicate through typed events where direct calls are unnecessary.

Events should expose:

- event identity;
- source;
- event type;
- payload;
- correlation identity where required.

Event transport is implementation detail.

Event meaning belongs to the contract.

---

# 38. COMMANDS

State-changing application operations should use explicit commands where practical.

A command may expose:

- command ID;
- source;
- target;
- intent;
- parameters;
- required authority;
- result.

Composition does not itself authorize mutation.

---

# 39. QUERIES

Read-only requests should remain distinguishable from commands.

Queries should remain side-effect free where their contract declares them read-only.

This supports:

- caching;
- replay;
- concurrency;
- projection.

---

# 40. EFFECT DECLARATION

A Sliver should declare material side effects.

Effect classes may include:

- `filesystem.read`;
- `filesystem.write`;
- `network`;
- `process.execute`;
- `database.read`;
- `database.write`;
- `credential.access`;
- `external.mutation`.

Selecting a Sliver does not automatically grant those effects.

---

# 41. SECURITY

Coalesce composition must preserve least-capability behavior.

Authority does not propagate merely because Slivers are connected.

A Sliver must not gain another Sliver's permissions implicitly.

---

# 42. MUTATION AUTHORITY

Coalesce is not the general mutation owner for Savant.

An Alloy exposing editing behavior must still respect the legitimate mutation authority.

Application composition is not authorization to bypass Coda or any other accepted mutation boundary.

---

# 43. REQUIRED AND OPTIONAL DEPENDENCIES

Every dependency should be classified:

- required;
- optional;
- conditional.

Required dependency failure:

`composition failure or explicit invalid state`.

Optional dependency failure:

`explicit degraded capability`.

Never fabricate unavailable behavior.

---

# 44. FAILURE CONTAINMENT

Failure of one optional Sliver capability must not corrupt unrelated Alloy state.

Where possible, failures should remain isolated and attributable.

Material degradation must be visible.

---

# 45. FALLBACK

Fallback is permitted only when semantic compatibility is explicit.

Fallback must preserve:

- capability meaning;
- contract;
- authority ownership.

Availability alone is insufficient to establish equivalence.

---

# 46. COMPATIBILITY GRAPH

Coalesce should maintain explicit typed relationships between Slivers.

Possible relationships:

- `requires`;
- `compatible_with`;
- `conflicts_with`;
- `substitutes_for`;
- `adapts`;
- `decorates`;
- `supersedes`;
- `derived_from`.

The graph should be projected from authoritative Sliver definitions where possible.

---

# 47. DEPENDENCY GRAPH

Every materialized Alloy should expose its material dependency graph.

The graph should include:

- Alloy;
- Recipe;
- Slivers;
- lower-order instances;
- adapters;
- providers;
- authorized Exile calls;
- projection.

Hidden dependencies are defects.

---

# 48. VERSIONING

Sliver evolution must distinguish:

- implementation-only change;
- backward-compatible contract extension;
- semantic contract change.

Historical Recipe interpretation must remain stable.

Accepted Recipe versions should be immutable.

---

# 49. MIGRATION

The historical migration target is no longer:

`81 -> 27`.

The canonical migration is:

`historical capability inventory`

→ semantic dispositions

→ lower-order reuse

→ capability normalization

→ Sliver Pool

→ Alloy Recipes

→ compatibility projection

→ verified cutover.

---

# 50. NO BIG-BANG REWRITE

Do not rewrite the historical Coalesce implementation all at once.

The current verified implementation remains baseline until a Sliver-based path proves required behavior.

Migration should be incremental and reversible where materially warranted.

---

# 51. REPRESENTATIVE MIGRATION

The first implementation proof should migrate exactly one representative complex application.

The application should exercise several capability categories.

It should prove:

- source adaptation;
- capability selection;
- multiple Slivers;
- typed bindings;
- lower-order reuse;
- projection;
- deterministic digest;
- compatibility.

Do not migrate all applications before this proof passes.

---

# 52. SLIVER SELECTION PLANNER

The first planner should remain simple and deterministic.

Recommended baseline:

1. normalize required capabilities;
2. enumerate eligible Slivers;
3. reject conflicts;
4. score uncovered capability gain;
5. select greatest gain;
6. repeat;
7. reject if more than nine Slivers are required;
8. use stable identity for deterministic tie-breaking.

Only adopt heavier solver infrastructure when evidence demonstrates need.

---

# 53. OPTIONAL SOLVERS

Potential future implementation primitives include:

- branch-and-bound;
- SAT;
- SMT;
- integer programming.

Potential libraries include:

- Z3;
- OR-Tools.

They are optional.

They do not become Coalesce authority.

---

# 54. CONTRACT VALIDATION

Suitable implementation tools may include:

- Python standard library;
- Pydantic;
- JSON Schema.

Pydantic may validate Python contracts.

JSON Schema may support portable validation.

Authoritative semantics remain Savant-owned.

---

# 55. GRAPH TOOLING

Existing Savant graph capabilities should be used first.

NetworkX may be introduced only where it materially improves bounded:

- cycle detection;
- reachability;
- dependency scheduling;
- compatibility analysis.

NetworkX must not become a second canonical graph.

---

# 56. EXTERNAL DEPENDENCY POLICY

Do not install every potentially useful library.

Dependency admission requires material benefit in the current bounded implementation.

Preference order:

1. existing Savant primitive;
2. standard library;
3. existing installed dependency;
4. small dedicated dependency;
5. heavy solver/framework only when justified.

---

# 57. STATIC VALIDATION

Before execution, Coalesce should validate:

1. Sliver count is between 1 and 9;
2. every Sliver resolves;
3. required capabilities are covered;
4. contracts are compatible;
5. required dependencies resolve;
6. conflicts are absent;
7. Exiles are not embedded;
8. typed segues resolve;
9. configuration validates;
10. projection is supported.

---

# 58. COMPOSITION LINTING

Coalesce should eventually detect:

- more than nine Slivers;
- duplicate capability;
- unresolved capability;
- undeclared dependency;
- incompatible Slivers;
- cycles;
- hidden Exile embedding;
- undeclared effects;
- source-domain contamination;
- unsupported projection.

This should remain bounded Coalesce functionality.

---

# 59. LAZY ACTIVATION

A selected Sliver may activate lazily when useful.

A dormant selected Sliver still counts toward the nine-Sliver limit.

Lazy activation does not alter Alloy identity.

---

# 60. INCREMENTAL RECOMPUTATION

When dependencies permit it, Coalesce should recompute only affected Sliver branches.

Unrelated results should remain reusable.

Scheduling and caching are engine concerns, not new Slivers.

---

# 61. PARALLELISM

Independent Sliver operations may execute concurrently where ordering is not semantically required.

Concurrency must preserve deterministic result semantics and explicit dependencies.

---

# 62. ATOMIC RECOMPOSITION

Runtime Sliver membership changes should be atomic.

Process:

1. build candidate;
2. validate;
3. initialize;
4. activate;
5. retire old composition.

Failure preserves the last valid Alloy.

---

# 63. COMPOSITION TRANSACTIONS

Where recomposition failure could corrupt persistent state, transaction semantics should preserve the prior valid composition.

Failed attempts remain historical evidence where appropriate.

---

# 64. FEDERATION

Large products may consist of multiple cooperating Alloys.

Alloy-to-Alloy relationships must preserve independent identity.

Federation may use:

- events;
- commands;
- queries;
- typed segues;
- providers.

An Alloy cannot be used as an ordinary Sliver merely to bypass the nine-Sliver cap.

---

# 65. HEADLESS SEMANTICS

Where practical, an Alloy should expose a headless semantic representation.

Browser UI is a projection.

React, HTML, native UI, terminal, or another presentation technology should not define Alloy identity.

---

# 66. ACCESSIBILITY

Projection contracts should carry enough semantics to support accessible renderers.

Accessibility should not be relegated to one application-specific visual patch.

---

# 67. RESOURCE POLICY

An Alloy may declare budgets for:

- latency;
- memory;
- CPU;
- network;
- external calls;
- rendering complexity.

Budgets belong to policy/configuration.

They do not become Slivers.

---

# 68. CONTENT ADDRESSING

Immutable Recipe snapshots, receipts, and related artifacts may use content-addressed digests.

Content hashes complement semantic identity.

They do not replace semantic IDs.

---

# 69. STRUCTURAL SHARING

Different Alloys should share canonical Sliver definitions and lower-order reusable substance.

Do not generate independent copies of canonical Slivers for each application.

---

# 70. SEMANTIC RECIPE DIFF

Coalesce should eventually support semantic Recipe comparison.

A diff should identify:

- Sliver added;
- Sliver removed;
- Sliver version changed;
- parameter changed;
- binding changed;
- segue changed;
- provider changed;
- projection changed.

Source-code line diff is not sufficient as the only composition comparison.

---

# 71. SLIVER LIFECYCLE

A Sliver may have lifecycle/trust states such as:

- candidate;
- evaluated;
- accepted;
- active;
- deprecated;
- superseded;
- quarantined;
- external.

History is preserved.

---

# 72. CHAMPION / CHALLENGER

Where multiple Slivers provide substantially equivalent capability, Coalesce may maintain:

- one accepted champion;
- one or more challengers.

Replacement requires evidence.

Historical champions remain recoverable.

---

# 73. CAPABILITY GAP DETECTION

When an Alloy cannot be built within nine Slivers, classify the cause.

Possible classes:

- missing capability;
- excessive fragmentation;
- incompatibility;
- missing adapter;
- unavailable provider;
- authority conflict;
- projection gap;
- multi-Alloy requirement.

Do not immediately raise the Sliver cap.

---

# 74. COVERAGE BENCHMARK

The Sliver Pool should eventually be evaluated against representative application requirements.

Primary metric:

`percentage of representative applications expressible with <=9 Slivers`.

Secondary metrics may include:

- average Sliver count;
- unresolved capability gaps;
- duplicate capability count;
- adapter burden;
- external dependency burden.

Raw pool size is not a quality metric.

---

# 75. SOURCE APPLICATION DECOMPOSITION

When converting an existing application into Coalesce:

1. identify useful generic functionality;
2. separate source-domain data;
3. identify existing Slivers;
4. identify lower-order reusable elements;
5. identify adapters/providers;
6. identify missing capabilities;
7. add a Sliver only when required;
8. create the Alloy Recipe;
9. validate <=9 Slivers;
10. project the Alloy.

Do not mechanically reproduce source application architecture.

---

# 76. NATURAL-LANGUAGE COMPOSITION

Future Coalesce may support:

`application description`

→ capability requirements

→ candidate Alloy Recipe

→ validation

→ accepted composition.

AI-generated Recipes remain proposals until accepted by applicable policy.

---

# 77. VISUAL COMPOSER

A future Coalesce projection may expose:

- Sliver Pool;
- nine composition positions;
- capability search;
- compatibility state;
- dependency view;
- Recipe editor;
- projection preview.

The visual composer edits the Recipe.

It is not separate composition authority.

---

# 78. ADVANCED ACCEPTED TARGETS

The following enhancements are accepted implementation targets where useful:

1. capability manifests;
2. formal Sliver contracts;
3. typed ports;
4. typed segues;
5. deterministic composition digests;
6. minimal-set planning;
7. compatibility graphs;
8. composition linting;
9. static validation;
10. composition receipts;
11. deterministic replay;
12. semantic Recipe diffs;
13. lazy activation;
14. incremental recomputation;
15. structural sharing;
16. atomic recomposition;
17. transaction-safe recomposition;
18. sandbox materialization;
19. shadow Recipes;
20. champion/challenger Slivers;
21. capability gap detection;
22. redundancy detection;
23. adapter recommendation;
24. dependency-health projection;
25. degraded capability states;
26. late provider binding;
27. explicit effect manifests;
28. capability-based security gates;
29. resource budgets;
30. dependency-aware scheduling;
31. safe parallel execution;
32. semantic caching;
33. content-addressed immutable artifacts;
34. Sliver lifecycle states;
35. quarantine;
36. trust classes;
37. supply-chain validation;
38. schema-driven configuration;
39. headless Alloy execution;
40. multi-projection output;
41. accessibility-aware projection;
42. visual Recipe composition;
43. natural-language Recipe proposals;
44. Alloy federation;
45. runtime observability;
46. provenance exploration;
47. coverage benchmarking;
48. gap-driven evolution;
49. semantic compatibility aliases;
50. deterministic migration receipts.

These targets do not authorize implementing all fifty at once.

---

# 79. FIRST IMPLEMENTATION MILESTONE

The first bounded Sliver implementation milestone contains only:

1. Sliver manifest contract;
2. Alloy Recipe contract;
3. Sliver Pool registry;
4. deterministic nine-Sliver validator;
5. simple minimal-set planner;
6. composition digest;
7. one representative Alloy Recipe;
8. compatibility path to the current projection.

Nothing else is required for milestone one.

---

# 80. FIRST MILESTONE VALIDATION

Minimum validation:

1. syntax/schema validation;
2. one focused composition test;
3. one relevant Filament/UI/API integration check.

Do not create unrelated test infrastructure.

---

# 81. FIRST MILESTONE COMPLETION

Milestone one is complete when:

- Sliver manifests resolve;
- Alloy Recipe resolves;
- selected Sliver count <=9;
- required capabilities are covered;
- selected Slivers are compatible;
- deterministic digest is stable;
- representative Alloy materializes;
- current projection path remains functional.

Then stop and evaluate before expanding.

---

# 82. FINAL COALESCE MIGRATION COMPLETION

The Coalesce migration is complete when:

1. historical capabilities have explicit disposition;
2. canonical Sliver Pool exists;
3. Alloy Recipes use no more than nine Slivers;
4. lower-order reuse works;
5. Exile embedding is rejected;
6. external Exile calls preserve ownership;
7. composition remains deterministic;
8. lineage and provenance remain inspectable;
9. historical implementation remains recoverable;
10. representative complex Alloy works;
11. Filament integration remains functional where still required;
12. source-domain data remains outside generic Sliver substance;
13. active dependents no longer require obsolete native-piece composition;
14. new materially different Alloys can reuse the same Sliver Pool.

When these conditions pass, stop.

---

# 83. CANONICAL INVARIANTS

1. Coalesce is the system.
2. Alloy is the assembled application.
3. Sliver is the reusable primary application capability.
4. An Alloy contains 1–9 Slivers.
5. Nine is the hard maximum primary Sliver count.
6. The Sliver Pool has no fixed canonical size.
7. Coalesce remains owned by Modus.
8. Coalesce remains a Prodigal.
9. Slivers reuse lower-order Savant substance.
10. Prodigals may be instanced.
11. Quirks may be instanced.
12. Exiles cannot be embedded.
13. Exiles may be called through authorized interfaces.
14. Recipes define Alloy composition.
15. UI is projection rather than Alloy identity.
16. Typed segues expose relationships.
17. Hidden dependencies are defects.
18. Composition does not grant mutation authority.
19. Runtime state is not automatically authority.
20. Historical 81-piece implementation remains provenance.
21. Historical 27-piece target remains provenance.
22. Neither 81 nor 27 is the current canonical pool cardinality.
23. The smallest sufficient valid Alloy is preferred.
24. No useful historical capability is silently discarded.

---

# 84. FINAL RULE

Coalesce's power comes from composition.

The Sliver Pool supplies reusable capability.

Prodigals and Quirks supply reusable lower-order substance.

Adapters normalize.

Providers connect.

Typed segues relate.

Recipes compose.

Alloys emerge.

Projections present.

Exiles remain external.

A coherent Alloy contains no more than nine Slivers.

The pool evolves only when real capability requires it.

Do not grow architecture merely because more abstractions are possible.
