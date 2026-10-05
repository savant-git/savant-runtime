# COALESCE — SLIVER MIGRATION PLAN

Status: ACCEPTED IMPLEMENTATION PLAN
System: Savant Runtime
Component: `prodigal:modus:coalesce`
Authority source: `/root/savant-runtime/COALESCE_COMPOSITION_CONTRACT.md`
Historical target reference: `/root/savant-runtime/COALESCE_27_PRIMITIVE_TARGET.md`
Directive date: 2026-08-11

# 1. OUTCOME

Migrate the verified historical Coalesce implementation into the canonical:

`Coalesce -> Sliver Pool -> 1–9 Slivers -> Alloy`

architecture without destroying working behavior, historical evidence, lineage, provenance, Filament compatibility, lower-order reuse, or existing application capability.

This is a migration plan.

It does not authorize an immediate rewrite.

The current verified implementation remains the baseline until each replacement path proves compatibility.

---

# 2. CANONICAL DEFINITIONS

Coalesce:
the application-composition system.

Sliver:
a reusable primary application capability.

Sliver Pool:
the canonical reusable capability registry.

Alloy:
an application composed from one through nine Sliver instances.

Alloy Recipe:
the authoritative declarative composition of an Alloy.

The maximum primary Sliver count per Alloy is:

`9`

---

# 3. MIGRATION PRINCIPLE

Migration MUST be:

- capability-preserving;
- instance-first;
- lineage-preserving;
- reversible where materially warranted;
- compatibility-aware;
- dependency-aware;
- deterministic;
- incremental.

Migration MUST NOT be:

- a mass rename;
- a filesystem-wide rewrite;
- a destructive cleanup;
- a recreation from memory;
- a forced conversion of every historical piece into a Sliver.

---

# 4. CURRENT BASELINE

The newest source-dump evidence shows Savant already requires:

- current verified implementation as baseline;
- extension rather than replacement;
- authority before inference;
- composition over duplication;
- immutable history;
- explicit dependencies;
- deterministic projection;
- migration safety.

These requirements govern Coalesce migration. 0

Historical source also establishes Modus as an accepted Exile concerned with modularity, composition modes, and module boundaries, preserving Coalesce's placement beneath Modus rather than promoting Coalesce into a new ontology level. 1

---

# 5. MIGRATION STOP CONDITION

The migration is complete when:

1. every required historical Coalesce capability has an explicit disposition;
2. the canonical Sliver Pool exists;
3. Alloy Recipes select no more than nine Slivers;
4. one representative complex historical application is reproduced as an Alloy;
5. its required behavior remains functional;
6. Filament projection remains functional where required;
7. Prodigal and Quirk reuse remains intact;
8. Exiles remain external;
9. composition lineage is preserved;
10. historical implementations remain recoverable;
11. no known active dependent requires the obsolete composition path.

When these conditions pass, STOP.

---

# 6. PHASE 0 — FREEZE THE BASELINE

Before mutation, establish the live Coalesce implementation currently in use.

Record:

- canonical Coalesce path;
- active launcher;
- recipes;
- piece registry;
- Filament integration;
- composition digest behavior;
- known applications;
- direct dependents;
- lower-order dependencies.

Do not duplicate the entire source tree merely to create a backup unless rollback risk warrants it.

Use existing source-dump and version/history evidence where sufficient.

Completion:

the active implementation and its known dependents are identifiable.

---

# 7. PHASE 1 — HISTORICAL PIECE INVENTORY

Enumerate historical Coalesce pieces from the verified implementation.

For each piece record:

- historical ID;
- path;
- purpose;
- inputs;
- outputs;
- dependencies;
- dependents;
- configuration;
- source application origin where applicable;
- whether currently referenced;
- whether behavior is generic or domain-specific.

Do not classify by filename alone.

---

# 8. PHASE 2 — SEMANTIC DISPOSITION

Every historical piece receives one disposition:

- `sliver`
- `merge_into_sliver`
- `parameter`
- `mode`
- `prodigal_instance`
- `quirk_instance`
- `adapter`
- `provider`
- `segue`
- `projection`
- `engine`
- `compatibility`
- `superseded`
- `historical_only`

No active behavior may disappear without disposition.

---

# 9. PHASE 3 — CAPABILITY NORMALIZATION

Convert historical implementation descriptions into stable semantic capabilities.

Examples:

- collection browsing;
- record detail;
- search;
- filtering;
- relationship navigation;
- chronology projection;
- graph exploration;
- comparison;
- command interaction;
- editing;
- workspace state;
- import/export;
- visualization.

Capabilities MUST describe behavior rather than source filenames.

---

# 10. PHASE 4 — DUPLICATION COLLAPSE

Identify historical pieces that provide substantially the same capability.

Prefer:

`multiple historical pieces`

→ `one canonical Sliver + parameters`

rather than:

`multiple source-derived Slivers`.

Preserve source lineage for all merged pieces.

---

# 11. PHASE 5 — LOWER-ORDER EXTRACTION

Before promoting behavior to a Sliver, determine whether it belongs to an existing lower-order Savant element.

Prefer:

- Prodigal instance;
- Quirk instance;
- adapter;
- provider;
- typed segue;
- projection;

when those primitives already express the behavior.

A Sliver should not duplicate lower-order substance.

---

# 12. PHASE 6 — ENGINE EXTRACTION

Universal Coalesce behavior must remain Coalesce engine behavior rather than consuming Sliver slots.

Engine responsibilities SHOULD include:

- Recipe parsing;
- Sliver resolution;
- capability matching;
- count enforcement;
- contract validation;
- binding;
- lifecycle coordination;
- composition digest generation;
- receipt generation;
- deterministic materialization.

These are not application Slivers.

---

# 13. PHASE 7 — CANDIDATE SLIVER POOL

Create candidate Slivers only after normalization.

Each candidate MUST have:

- stable ID;
- capability manifest;
- public contract;
- configuration schema;
- ports;
- effects;
- dependencies;
- compatibility;
- provenance;
- lineage.

Do not establish a fixed total count.

---

# 14. PHASE 8 — CAPABILITY COVERAGE MAP

Project:

`required capability -> candidate Slivers`

from candidate manifests.

The coverage map is derived.

It MUST NOT become independently maintained authority.

Use it to identify:

- gaps;
- overlaps;
- unnecessary fragmentation;
- missing adapters.

---

# 15. PHASE 9 — NINE-SLIVER FEASIBILITY

Test representative application requirements against the candidate pool.

For each application:

1. identify required capabilities;
2. select compatible Slivers;
3. minimize selected count;
4. verify count <= 9;
5. identify uncovered capability.

If a representative application requires more than nine Slivers, investigate:

- over-fragmentation;
- duplicate capability;
- behavior that belongs in configuration;
- lower-order reuse;
- adapter need;
- multi-Alloy federation.

Do not simply raise the cap.

---

# 16. PHASE 10 — ALLOY RECIPE CONTRACT

Every migrated application receives an Alloy Recipe containing:

- Alloy ID;
- Recipe version;
- Sliver IDs;
- Sliver instance IDs;
- parameters;
- ports;
- typed segues;
- adapters;
- providers;
- authorized Exile calls;
- projection targets;
- policy.

Recipe data references canonical Slivers.

It MUST NOT copy Sliver implementation.

---

# 17. PHASE 11 — DETERMINISTIC PLANNER

Implement the smallest sufficient deterministic planner first.

Baseline algorithm:

1. normalize requested capability IDs;
2. identify eligible Slivers;
3. reject incompatible candidates;
4. calculate uncovered capability gain;
5. select greatest gain;
6. repeat until requirements are covered;
7. reject if more than nine Slivers are required;
8. resolve ties using stable Sliver identity.

Do not introduce SAT/SMT or integer-programming dependencies until evidence demonstrates the simpler planner is insufficient.

---

# 18. PHASE 12 — CONTRACT VALIDATION

Before materialization validate:

- 1–9 Slivers;
- IDs resolve;
- versions resolve;
- required capabilities resolve;
- ports match;
- segues match;
- dependencies resolve;
- conflicts are absent;
- Exile embedding is absent;
- effects are declared;
- configuration validates;
- required projection exists.

---

# 19. PHASE 13 — COMPOSITION DIGEST

Generate a deterministic digest from semantic composition inputs.

Include:

- Recipe version;
- Sliver IDs;
- Sliver versions;
- relevant parameters;
- typed segues;
- adapters;
- provider identities;
- projection identity.

Exclude irrelevant volatile runtime values.

---

# 20. PHASE 14 — COMPOSITION RECEIPT

Materialization should emit a receipt containing:

- Alloy ID;
- Recipe ID;
- composition digest;
- Sliver IDs;
- Sliver versions;
- instance IDs;
- configuration digests;
- dependencies;
- external calls;
- projection;
- degraded capabilities;
- warnings.

The receipt is evidence.

It is not separate architecture authority.

---

# 21. PHASE 15 — FILAMENT COMPATIBILITY

Where the current verified implementation projects applications through Filament, preserve that relationship.

Required boundary:

`Coalesce -> Alloy -> projection request -> Filament`

Coalesce owns application composition.

Filament owns its legitimate presentation capability.

Do not duplicate Filament behavior inside Slivers merely to simplify migration.

---

# 22. PHASE 16 — EXILE COMPATIBILITY

Exiles remain external capability owners.

Migration MUST reject:

- Exile-as-Sliver;
- embedded Exile implementation;
- copied Exile source;
- Alloy-owned Exile state.

Allowed:

`Sliver -> authorized interface -> Exile`

The external relationship remains visible in the graph.

---

# 23. PHASE 17 — PRODIGAL AND QUIRK REUSE

Existing compatible Prodigal and Quirk implementations should be instantiated rather than copied.

Each instance preserves:

- canonical source;
- instance ID;
- configuration;
- ownership;
- lineage;
- provenance;
- dependents.

This reuse does not consume additional primary Sliver slots.

---

# 24. PHASE 18 — ADAPTER COMPATIBILITY

Historical interfaces that cannot immediately consume Sliver contracts may use compatibility adapters.

Adapters MUST:

- preserve old external behavior where required;
- translate explicitly;
- expose lineage;
- remain removable;
- avoid becoming duplicate architecture authority.

---

# 25. PHASE 19 — REPRESENTATIVE ALLOY

Migrate exactly one representative complex application first.

Choose an application exercising several distinct capability classes.

The representative Alloy should demonstrate:

- multiple Slivers;
- lower-order reuse;
- typed segues;
- provider/external boundaries;
- projection;
- deterministic Recipe;
- composition digest.

Do not migrate every application before this path passes.

---

# 26. PHASE 20 — DIFFERENTIAL COMPARISON

Compare the representative Alloy against the verified historical application.

Compare:

- required functionality;
- data neutrality;
- external calls;
- projection;
- interaction behavior;
- dependency visibility;
- composition reproducibility.

Do not require identical implementation internals.

Require preserved required semantics.

---

# 27. PHASE 21 — HISTORICAL RECIPE TRANSLATION

Translate additional required historical Recipes only after the representative Alloy passes.

Historical Recipes remain immutable.

Translation produces:

`historical recipe`

→ migration lineage

→ `Alloy Recipe`.

---

# 28. PHASE 22 — LEGACY ALIASES

Where active dependents still refer to historical piece IDs, maintain explicit compatibility aliases.

Aliases MUST resolve:

`historical ID -> canonical Sliver / adapter / disposition`

They MUST NOT create cloned implementations.

---

# 29. PHASE 23 — OBSOLETE PATH RETIREMENT

Only retire obsolete runtime paths after:

- active dependents have migrated;
- compatibility references resolve;
- representative integration passes;
- historical source remains recoverable.

Retirement means no longer active.

It does not mean historical deletion.

---

# 30. PHASE 24 — SLIVER REGISTRY

The canonical registry stores only authoritative Sliver primitives.

Derived views include:

- capability index;
- dependency graph;
- compatibility matrix;
- search index;
- usage projection.

Do not maintain these manually when deterministic projection is possible.

---

# 31. PHASE 25 — ALLOY REGISTRY

Accepted Alloy Recipes should remain independently addressable.

An Alloy registry should identify:

- Alloy ID;
- active Recipe version;
- Recipe lineage;
- projection targets;
- lifecycle state.

It should not duplicate Recipe contents unnecessarily.

---

# 32. PHASE 26 — STATIC COMPOSITION LINT

Implement bounded lint rules for:

- >9 Slivers;
- duplicate capability;
- unresolved requirement;
- undeclared dependency;
- cycle;
- conflict;
- embedded Exile;
- undeclared effect;
- domain contamination;
- unknown Sliver;
- unsupported projection.

Avoid building an unrelated general-purpose lint platform.

---

# 33. PHASE 27 — HOT RECOMPOSITION

Only after static Alloy composition works, support safe runtime membership changes where useful.

Required process:

1. construct candidate;
2. validate candidate;
3. initialize candidate;
4. atomically activate candidate;
5. retire old composition.

Failure preserves the prior valid composition.

---

# 34. PHASE 28 — MULTI-ALLOY FEDERATION

When a product genuinely exceeds the coherent nine-Sliver scope, support cooperating Alloys.

Federation uses explicit:

- events;
- commands;
- queries;
- typed segues;
- providers.

An Alloy must not masquerade as another Alloy's Sliver.

---

# 35. PHASE 29 — PROJECTION INDEPENDENCE

Prove that Alloy semantics can be inspected independently from one browser implementation.

The same Alloy should be capable of at least a headless semantic projection where feasible.

This prevents UI source from becoming Alloy authority.

---

# 36. PHASE 30 — SEMANTIC RECIPE DIFF

Support comparison of Alloy Recipes by semantic change:

- Sliver added;
- Sliver removed;
- version changed;
- parameter changed;
- segue changed;
- provider changed;
- projection changed.

Do not rely solely on line diffs.

---

# 37. PHASE 31 — INCREMENTAL RECOMPUTATION

Use the dependency graph to recompute only affected Sliver branches where semantics permit.

Do not introduce a new Sliver for caching or scheduling.

These remain engine concerns.

---

# 38. PHASE 32 — LAZY ACTIVATION

Support dormant/lazy Sliver activation where material startup cost justifies it.

A dormant selected Sliver still counts toward the Alloy's nine-Sliver cap.

---

# 39. PHASE 33 — FAILURE DEGRADATION

Optional capability failure should produce explicit degraded state.

Required capability failure invalidates the relevant composition.

Never fabricate successful capability.

---

# 40. PHASE 34 — RESOURCE POLICY

Allow Alloy policy to express:

- latency;
- memory;
- CPU;
- network;
- storage;
- external-call budgets.

Budgets remain policy/configuration.

They do not become Slivers.

---

# 41. PHASE 35 — EFFECT GATING

Sliver effect manifests should distinguish:

- filesystem read;
- filesystem write;
- network;
- process execution;
- database read;
- database write;
- credential access;
- external mutation.

Composition alone does not grant these effects.

---

# 42. PHASE 36 — TRUST STATE

Slivers may have lifecycle/trust state:

- candidate;
- evaluated;
- accepted;
- active;
- deprecated;
- superseded;
- quarantined;
- external.

Historical state remains recoverable.

---

# 43. PHASE 37 — CHAMPION / CHALLENGER

Where multiple implementations legitimately provide equivalent capability:

- maintain one active champion;
- evaluate challengers separately;
- preserve evidence;
- supersede explicitly.

Avoid permanent duplicate Slivers for nearly identical capability.

---

# 44. PHASE 38 — COVERAGE BENCHMARK

Use representative application capability requirements to measure the Sliver Pool.

Primary measure:

`applications expressible with <=9 Slivers`

Secondary measures:

- mean Sliver count;
- unresolved gaps;
- duplicate capability;
- adapter burden;
- external dependency burden.

Do not optimize for pool size alone.

---

# 45. PHASE 39 — GAP-DRIVEN EVOLUTION

Repeated unsatisfied capability should generate a candidate architectural finding.

The remedy may be:

- new Sliver;
- broader existing Sliver;
- adapter;
- parameter;
- Prodigal;
- Quirk;
- provider;
- federation.

Do not automatically create a Sliver.

---

# 46. PHASE 40 — OPTIONAL LIBRARY ADMISSION

Potential future implementation aids:

- Pydantic;
- JSON Schema tooling;
- NetworkX;
- Z3;
- OR-Tools.

Default:

use no new dependency unless the current bounded implementation materially benefits.

Likely order of consideration:

1. existing Savant primitive;
2. Python standard library;
3. existing installed dependency;
4. small dedicated dependency;
5. heavier solver/library only with demonstrated need.

---

# 47. PHASE 41 — Pydantic

If Python contract validation becomes sufficiently complex, Pydantic may validate:

- Sliver manifests;
- Alloy Recipes;
- receipts;
- port contracts.

Pydantic does not own canonical semantics.

---

# 48. PHASE 42 — JSON SCHEMA

JSON Schema may provide portable schema validation for non-Python projections.

Prefer deterministic schema projection from authoritative definitions rather than manually maintaining duplicate contract authority.

---

# 49. PHASE 43 — GRAPH ANALYSIS

Use existing Savant graph functionality first.

NetworkX may be admitted only if it materially improves bounded:

- cycle analysis;
- reachability;
- dependency scheduling;
- compatibility analysis.

It must not become a second canonical graph.

---

# 50. PHASE 44 — ADVANCED CONSTRAINT SOLVING

Only if the deterministic baseline planner proves insufficient may advanced solving be introduced.

Potential techniques:

- branch-and-bound;
- SAT;
- SMT;
- integer programming.

Potential libraries:

- Z3;
- OR-Tools.

The solver produces a composition proposal.

It does not own composition authority.

---

# 51. PHASE 45 — CONTENT ADDRESSING

Immutable Sliver/Recipe artifacts may receive content digests.

Semantic IDs remain primary identities.

Content hashes improve:

- integrity;
- caching;
- replay;
- provenance.

---

# 52. PHASE 46 — STRUCTURAL SHARING

Multiple Alloys should reuse the same canonical Sliver definitions and immutable artifacts.

Do not generate independent copies of canonical Slivers inside every Alloy.

---

# 53. PHASE 47 — NATURAL-LANGUAGE PLANNING

Later, Coalesce may accept a natural-language application request.

Flow:

`request`

→ capability requirements

→ candidate Recipe

→ deterministic validation

→ user/runtime acceptance

→ Alloy.

AI-generated Recipes remain proposals.

---

# 54. PHASE 48 — VISUAL COMPOSER

A future Coalesce projection may expose:

- Sliver Pool;
- nine available composition positions;
- capability search;
- compatibility indicators;
- dependency view;
- Recipe preview;
- projection preview.

The visual editor manipulates the Recipe.

It does not become separate composition authority.

---

# 55. PHASE 49 — FEDERATED PRODUCT COMPOSITION

Large products may expose multiple cooperating Alloy identities.

Example conceptual topology:

`Alloy A <-> typed segue <-> Alloy B`

Each retains:

- Recipe;
- digest;
- Slivers;
- lifecycle;
- lineage.

---

# 56. PHASE 50 — FINAL CUTOVER

Only after all active required dependents have a compatible Sliver/Alloy path:

1. mark old runtime route deprecated;
2. activate canonical Sliver route;
3. keep explicit compatibility where still consumed;
4. preserve historical implementation;
5. update active projections;
6. record supersession.

Do not delete history.

---

# 57. REQUIRED ADVANCED ENHANCEMENTS

The migration should preserve the following accepted targets from the composition contract:

1. capability manifests;
2. formal Sliver contracts;
3. typed ports;
4. typed segues;
5. deterministic composition digests;
6. minimal-set planning;
7. compatibility graph;
8. composition linting;
9. static validation;
10. composition receipts;
11. deterministic replay;
12. semantic Recipe diff;
13. lazy activation;
14. incremental recomputation;
15. structural sharing;
16. atomic recomposition;
17. transaction-safe recomposition;
18. sandbox composition;
19. shadow Recipes;
20. champion/challenger Slivers;
21. capability gap detection;
22. redundancy detection;
23. adapter recommendation;
24. dependency-health projection;
25. explicit degraded states;
26. late provider binding;
27. capability security grants;
28. effect declarations;
29. resource budgets;
30. dependency-aware scheduling.

These do not all need to be implemented simultaneously.

They are bounded architecture targets.

---

# 58. FIRST IMPLEMENTATION MILESTONE

The first implementation milestone contains only:

1. canonical Sliver manifest schema;
2. canonical Alloy Recipe schema;
3. Sliver Pool registry;
4. deterministic <=9 validator;
5. simple minimal-set planner;
6. composition digest;
7. one representative Alloy Recipe;
8. compatibility bridge to current projection.

Nothing else is required for milestone one.

---

# 59. FIRST MILESTONE COMPLETION

Milestone one is complete when:

- schemas validate;
- registry resolves Slivers;
- planner can select a compatible set;
- selected set contains <=9 Slivers;
- Recipe materializes;
- digest is stable;
- representative Alloy projection works;
- current required behavior remains available.

At that point STOP and evaluate before proceeding.

---

# 60. FINAL MIGRATION INVARIANT

The target is not:

`rewrite Coalesce`.

The target is:

`preserve proven Coalesce behavior while changing its canonical composition grammar from historical pieces into Slivers and Alloys`.

Canonical future:

`Coalesce`

→ `Sliver Pool`

→ `smallest sufficient compatible selection`

→ `1–9 Sliver instances`

→ `Alloy Recipe`

→ `Alloy`

→ `projection`.

Migration stops when that path is proven and required historical dependents are safely accounted for.
