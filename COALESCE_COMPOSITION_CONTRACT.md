# COALESCE — COMPOSITION CONTRACT

Status: ACCEPTED DESIGN AUTHORITY  
System: Savant Runtime  
Component: `prodigal:modus:coalesce`  
Owner: `exile:modus`  
Supersedes: prior Coalesce composition contract where conflicting  
Directive date: 2026-08-11

This document defines the canonical architecture of Coalesce, Alloy, and Sliver composition.

The current user directive supersedes the prior 27-native-primitive target.

Historical Coalesce implementations, including the 81-piece and 27-piece architectural stages, remain historical implementation evidence and migration input. They are not the future composition target.

---

# 1. CANONICAL VOCABULARY

## Coalesce

**Coalesce** is the Savant application-composition system.

Coalesce does not itself mean an application.

It is the composition capability that discovers, selects, configures, connects, validates, materializes, and projects reusable functionality into applications.

## Alloy

An **Alloy** is an application assembled by Coalesce.

An Alloy is an emergent composition rather than a monolithic implementation.

An Alloy contains:

`1–9 Sliver instances`

plus configuration, typed segues, bindings, data projections, and authorized external capability calls.

Nine is a hard maximum for internal Sliver membership unless explicitly superseded by stronger authority.

## Sliver

A **Sliver** is a reusable, bounded, independently addressable unit of application functionality available to Coalesce.

A Sliver is not merely a UI component.

A Sliver represents a coherent application capability that can be parameterized, attached, composed, projected, and reused across materially different Alloys.

The available canonical set is the:

**Sliver Pool**

An Alloy selects only the Slivers it needs from that pool.

---

# 2. PRIMARY ARCHITECTURE

The canonical model is:

`Sliver Pool`

→ selection

→ `1–9 configured Sliver instances`

→ typed composition

→ **Alloy**

Coalesce therefore optimizes for:

**small application compositions over a sufficiently expressive reusable capability pool.**

The purpose of the Sliver Pool is not to contain every possible application as predefined pieces.

Its purpose is to contain enough orthogonal functional capability that composition, parameterization, lower-order Savant instances, adapters, providers, and projections can produce nearly any required Alloy.

---

# 3. HARD ALLOY CAP

An Alloy MUST contain no more than:

`9 Slivers`

This cap is architectural, not aesthetic.

The cap exists to force:

- meaningful Sliver granularity;
- low composition complexity;
- inspectable dependency graphs;
- predictable runtime behavior;
- comprehensible recipes;
- reusable capabilities;
- controlled coupling;
- easier replay;
- easier testing;
- easier migration;
- easier optimization.

A proposed Alloy requiring more than nine Slivers is evidence that one or more of the following should occur:

1. overlapping Slivers should be composed into a more coherent Sliver;
2. behavior belongs in configuration rather than another Sliver;
3. behavior belongs in a Prodigal or Quirk instance;
4. behavior belongs behind an adapter;
5. behavior belongs behind a provider;
6. behavior belongs in a projection;
7. a higher-order external capability should be called;
8. the requested product is actually multiple cooperating Alloys rather than one Alloy.

The nine-Sliver maximum MUST NOT be bypassed by hiding additional Slivers inside an ordinary Sliver.

---

# 4. SLIVER GRANULARITY

A Sliver is the smallest **coherent application-scale capability**, not the smallest possible behavior.

A Sliver should be broad enough to remain useful across many applications while narrow enough to preserve one understandable responsibility.

Do not create:

- one Sliver per button;
- one Sliver per field;
- one Sliver per endpoint;
- one Sliver per source application;
- one Sliver per visual widget;
- one Sliver per data schema.

Do not create giant universal Slivers containing unrelated capabilities merely to satisfy the nine-Sliver cap.

Correct granularity is defined by:

- semantic cohesion;
- independent reuse;
- clean contract boundaries;
- parameterizability;
- low hidden coupling;
- composability.

---

# 5. SLIVER POOL

The Sliver Pool is an extensible registry of canonical Sliver definitions.

The pool MAY contain more than nine Slivers.

The nine-count invariant applies to one Alloy's active internal composition, not to the total pool.

Every canonical Sliver MUST expose:

- stable Sliver identity;
- semantic capability;
- version;
- contract;
- inputs;
- outputs;
- configuration schema;
- supported attachments;
- required dependencies;
- optional dependencies;
- incompatible Slivers where applicable;
- compatible typed segues;
- projection capabilities;
- provenance;
- lineage;
- lifecycle state;
- deterministic digest where feasible.

Sliver definitions are authoritative primitives.

Alloy-specific configuration is not.

---

# 6. ORTHOGONALITY

The Sliver Pool should maximize functional coverage while minimizing semantic overlap.

Two Slivers SHOULD NOT exist when they represent the same capability with different names or minor application-specific behavior.

Overlap should resolve through:

- parameterization;
- modes;
- adapters;
- reusable lower-order instances;
- projections;
- typed attachments.

A new Sliver is justified only when it provides a distinct reusable capability that cannot be cleanly represented through existing composition primitives.

---

# 7. DIFFERENTIAL CAPABILITY

The Sliver Pool should be designed around **differential capability**.

Each Sliver contributes a materially distinct capability vector.

Conceptually:

`Alloy capability = composition of distinct Sliver capability vectors`

The objective is to maximize the functional space reachable from combinations of at most nine Slivers.

Therefore Sliver design SHOULD favor capabilities with high:

- reuse;
- orthogonality;
- compositional leverage;
- configurability;
- interoperability.

And minimize:

- redundancy;
- domain specificity;
- hidden state;
- source coupling;
- duplicate authority.

---

# 8. FUNCTIONAL COMPLETENESS

Coalesce does not require one Sliver for every possible application behavior.

Functional completeness emerges from:

`Sliver`

+ parameters

+ typed segues

+ Prodigal instances

+ Quirk instances

+ adapters

+ providers

+ external calls

+ projections

+ runtime configuration

+ data.

The target is therefore:

**bounded composition with unbounded practical expressiveness through reusable primitives.**

---

# 9. INTERNAL COMPOSITION BOUNDARY

An Alloy may internally contain:

1. Sliver instances;
2. permitted Prodigal instances referenced by Slivers;
3. permitted Quirk instances referenced by Slivers;
4. configuration;
5. typed segues;
6. adapters;
7. providers;
8. projections;
9. transient application state.

Only Slivers count toward the maximum nine primary application pieces.

Lower-order instances do not become hidden additional primary pieces merely because they support a Sliver.

Their identity and dependency relationships must remain visible.

---

# 10. EXILE BOUNDARY

Exiles MUST NOT be embedded in an Alloy.

Exiles MUST NOT become Slivers.

Exiles MUST NOT be copied into Coalesce.

Exiles MUST NOT be instantiated as application-owned internal substance.

An Alloy MAY call an Exile through an authorized contract when it legitimately requires an Exile-owned capability.

Canonical relationship:

`Alloy`

→ `Sliver`

→ `authorized interface`

→ `Exile`

The Exile remains external, independently owned, independently versioned, and independently graph-addressable.

---

# 11. PRODIGALS

Prodigals may supply reusable lower-order substance to Slivers.

Prefer:

`canonical Prodigal -> instance -> Sliver`

not:

`canonical Prodigal -> copied implementation -> Alloy-specific fork`

A Prodigal instance MUST retain:

- canonical identity;
- instance identity;
- owner;
- parameters;
- lineage;
- provenance;
- dependencies;
- dependents.

---

# 12. QUIRKS

Quirks may provide localized, narrow, optional, or transforming behavior within a Sliver.

Typical uses include:

- normalization;
- filtering;
- ranking;
- formatting;
- adaptation;
- interaction modifiers;
- presentation modifiers;
- specialized transformations.

Prefer parameterized Quirk instances over duplicate Quirks.

---

# 13. INSTANCE-FIRST COMPOSITION

The preferred realization path is:

`canonical Sliver`

→ `Sliver instance`

→ `configuration`

→ `Alloy`

not:

`canonical Sliver`

→ `copied source`

→ `modified fork`

→ `Alloy`

Every Sliver instance MUST permit recovery of:

- canonical Sliver;
- instance ID;
- Alloy ID;
- configuration;
- lineage;
- provenance;
- relationships;
- dependencies;
- attachments.

---

# 14. ALLOY RECIPE

Every Alloy is defined primarily by an **Alloy Recipe**.

The recipe MUST specify:

- Alloy identity;
- recipe version;
- selected Sliver identities;
- Sliver instance IDs;
- parameters;
- typed segues;
- bindings;
- required providers;
- authorized external capability calls;
- projection targets;
- initialization policy;
- deterministic ordering only where ordering is semantically required.

The recipe MUST NOT duplicate Sliver implementation.

---

# 15. ALLOY IDENTITY

An Alloy has identity independent of its component Slivers.

Canonical reconstruction should be possible from:

`Alloy Recipe`

+ `canonical Sliver versions`

+ `instance configuration`

+ `referenced lower-order elements`

+ `relevant input identity`

An Alloy should not require a monolithic source implementation to establish its identity.

---

# 16. COMPOSITION DIGEST

Every materialized Alloy SHOULD receive a deterministic composition digest derived from the semantic composition inputs.

The digest SHOULD include:

- recipe version;
- ordered canonical Sliver identities where order matters;
- configuration digests;
- typed segue identities;
- provider/interface identities;
- projection identity.

The digest MUST NOT include volatile values that do not affect semantic composition.

This enables:

- replay;
- caching;
- comparison;
- drift detection;
- provenance;
- reproducibility.

---

# 17. COMPOSITION PLANNER

Coalesce SHOULD expose a deterministic composition planner.

Input:

- requested application capabilities;
- constraints;
- available Sliver Pool;
- permitted external capabilities;
- runtime target.

Output:

- candidate Alloy Recipe;
- selected Slivers;
- unsatisfied requirements;
- composition score;
- incompatibilities;
- dependencies;
- projection plan.

The planner MUST prefer the smallest sufficient Sliver set.

---

# 18. MINIMAL SUFFICIENT ALLOY

Given two valid compositions providing equivalent required behavior, Coalesce SHOULD prefer the composition with:

1. fewer Slivers;
2. fewer required external dependencies;
3. lower semantic overlap;
4. clearer ownership;
5. stronger deterministic behavior;
6. lower coupling.

This is the:

**Minimal Sufficient Alloy Principle.**

---

# 19. SLIVER SELECTION

Sliver selection SHOULD be treated as a constrained set-cover problem rather than arbitrary assembly.

Conceptually:

find the smallest compatible Sliver set that covers all required capabilities subject to:

`|selected Slivers| <= 9`

plus:

- compatibility;
- authority;
- dependency;
- runtime;
- security;
- performance;
- accessibility constraints.

The exact algorithm is implementation policy.

It must not become architectural authority.

---

# 20. CAPABILITY MANIFEST

Every Sliver SHOULD publish a machine-readable capability manifest.

Capabilities should use stable semantic identifiers rather than prose-only descriptions.

Example conceptual identifiers:

`data.collection`

`data.query`

`data.filter`

`data.transform`

`relationship.graph`

`state.workspace`

`interaction.command`

`presentation.detail`

`projection.timeline`

This allows deterministic composition without binding Coalesce to implementation filenames.

---

# 21. CAPABILITY NEGOTIATION

Slivers MAY negotiate compatible capabilities through declared contracts.

Negotiation must be deterministic from:

- declared requirements;
- provided capabilities;
- versions;
- policy;
- configuration.

Runtime duck-typing of unknown Slivers SHOULD NOT be the primary composition mechanism.

---

# 22. TYPED SEGUES

Slivers connect through typed segues.

Typed segues declare relationship semantics explicitly.

Examples:

- feeds;
- transforms;
- observes;
- controls;
- projects;
- indexes;
- queries;
- navigates;
- decorates;
- validates.

Do not replace typed relationships with invisible application-local coupling.

---

# 23. PORTS

A Sliver SHOULD expose explicit logical ports.

A port represents an attachable semantic boundary.

Examples:

- input;
- output;
- events;
- commands;
- state;
- selection;
- projection;
- provider;
- query.

Ports make composition inspectable without requiring Slivers to know each other's internal implementation.

---

# 24. CONTRACT-FIRST CONNECTION

Two Slivers compose only when their declared contracts are compatible or an explicit adapter exists.

Do not couple Slivers through undocumented assumptions about:

- object shape;
- DOM structure;
- filenames;
- global variables;
- private methods;
- source application internals.

---

# 25. ADAPTERS

Adapters normalize incompatible representations without altering either canonical Sliver.

Prefer:

`Sliver A -> adapter -> Sliver B`

over:

`modify Sliver A specifically for Sliver B`

Adapters are reusable and graph-addressable.

Adapters do not become new authority.

---

# 26. PROVIDERS

Providers expose external data or capability.

Providers MUST preserve ownership boundaries.

A provider record should expose:

- provider identity;
- capability;
- contract;
- availability;
- provenance where applicable;
- error state.

Provider implementations do not count as Slivers unless their behavior independently satisfies the canonical definition of a Sliver.

---

# 27. PROJECTIONS

An Alloy may have multiple projections without becoming multiple Alloys.

Possible projections include:

- browser;
- terminal;
- API;
- mobile;
- desktop;
- report;
- embedded panel.

Application semantics remain separate from projection technology.

Therefore:

**UI is a projection of an Alloy, not the Alloy itself.**

---

# 28. HEADLESS ALLOY

Every Alloy SHOULD be capable of a headless semantic representation when feasible.

This prevents Coalesce from becoming fundamentally bound to:

- React;
- browser DOM;
- HTML;
- JavaScript;
- one rendering framework.

A browser implementation is a projection.

---

# 29. DATA NEUTRALITY

Slivers MUST be domain-neutral unless a stronger authority explicitly establishes a domain-specific Sliver.

A generic Sliver must not contain:

- Mayorgate records;
- Viscera records;
- Palaver conversations;
- application-specific sample data;
- hardcoded source schemas.

Source-specific data enters through adapters/providers/input projections.

---

# 30. STATE SEPARATION

Alloy runtime state is not automatically authority.

Examples:

- selected entity;
- query;
- viewport;
- open drawer;
- sort order;
- active lens;
- local bookmarks;
- pending comparison;
- temporary form state.

Runtime state must remain distinguishable from:

- canon;
- accepted decisions;
- evidence;
- authoritative graph state.

---

# 31. STATE OWNERSHIP

Every state channel SHOULD declare:

- owner;
- lifetime;
- persistence;
- authority level;
- serialization policy;
- replay significance.

This prevents application convenience state from becoming accidental system authority.

---

# 32. EVENT MODEL

Slivers SHOULD communicate state changes through typed events when direct synchronous coupling is unnecessary.

Events SHOULD contain:

- event ID;
- source Sliver;
- event type;
- payload;
- timestamp where semantically relevant;
- correlation ID where applicable.

Event transport is implementation detail.

Event meaning is contract.

---

# 33. COMMAND MODEL

State-changing operations SHOULD use explicit commands where practical.

A command SHOULD expose:

- command identity;
- source;
- target;
- intent;
- parameters;
- authority requirement;
- result status.

This improves:

- auditability;
- replay;
- mutation control;
- compatibility.

---

# 34. QUERY MODEL

Read-only semantic requests SHOULD be distinguishable from commands.

Query behavior SHOULD remain side-effect free unless explicitly documented.

This enables safe:

- caching;
- replay;
- parallel execution;
- projection.

---

# 35. REQUIRED / OPTIONAL DEPENDENCIES

Every dependency MUST be declared as:

- required;
- optional;
- conditional.

Required dependency failure:

`explicit Alloy degradation or failure`

Optional dependency failure:

`explicit reduced capability`

Never:

`silent fabrication`

---

# 36. FAILURE CONTAINMENT

One failed optional Sliver capability MUST NOT corrupt unrelated Alloy state.

Sliver failure boundaries SHOULD isolate:

- errors;
- retries;
- fallback;
- degraded state.

An Alloy must surface its degraded capability state when material.

---

# 37. FALLBACK

Fallback is valid only when the fallback is semantically compatible.

Do not substitute merely because another implementation exists.

Fallback decisions should preserve:

- capability meaning;
- authority;
- expected output contract.

---

# 38. LAZY ACTIVATION

A Sliver MAY be lazily activated when:

- its capability is not initially required;
- activation cost is meaningful;
- deterministic semantics remain intact.

Lazy activation MUST NOT permit more than nine active primary Slivers in one Alloy.

---

# 39. CAPABILITY DORMANCY

A selected Sliver MAY remain dormant until triggered.

Dormancy is not absence.

A dormant selected Sliver still counts toward the nine-Sliver Alloy cap because it remains part of the composition.

---

# 40. HOT RECONFIGURATION

An Alloy MAY support runtime reconfiguration of Sliver parameters and optional bindings.

Replacing the selected Sliver set constitutes a new composition state.

Material composition changes SHOULD produce a new composition digest.

---

# 41. ATOMIC RECOMPOSITION

Where Sliver membership changes at runtime, recomposition SHOULD be atomic:

1. resolve candidate;
2. validate candidate;
3. prepare candidate;
4. activate candidate;
5. retire previous composition.

Do not expose half-composed application state.

---

# 42. COMPOSITION TRANSACTIONS

Material Alloy recomposition SHOULD support transaction semantics where failure could otherwise leave invalid state.

A failed recomposition should preserve the last valid composition.

---

# 43. COMPATIBILITY

Sliver compatibility SHOULD be explicit and machine-checkable.

Compatibility may include:

- contract version ranges;
- required capabilities;
- forbidden pairings;
- projection requirements;
- runtime requirements;
- provider requirements.

Do not infer compatibility solely from successful imports.

---

# 44. VERSIONING

Sliver version changes MUST distinguish:

- behavior-preserving implementation change;
- backward-compatible contract extension;
- semantic contract change.

Semantic changes require supersession or explicit version compatibility handling.

Old Alloy Recipes must not be silently reinterpreted.

---

# 45. IMMUTABLE HISTORICAL RECIPES

Historical Alloy Recipes are historical evidence.

Do not mutate a historical recipe to match a newer Sliver.

Instead:

`old recipe`

→ explicit migration

→ `new recipe`

The lineage between them remains inspectable.

---

# 46. MIGRATION

Historical Coalesce pieces MUST receive an explicit disposition before retirement.

Possible dispositions include:

- Sliver;
- merged into Sliver;
- parameter;
- configuration;
- Prodigal instance;
- Quirk instance;
- adapter;
- provider;
- projection;
- compatibility layer;
- superseded;
- historical only.

No capability disappears without disposition.

---

# 47. HISTORICAL 81-PIECE ARCHITECTURE

The historical 81-piece implementation remains provenance.

It is not the future structural target.

Its useful behavior must be mapped into the Sliver architecture before obsolete representations are retired.

---

# 48. SUPERSEDED 27-PIECE TARGET

The previously accepted future target of:

`27 native Coalesce primitives`

is superseded by this contract.

The new target is:

`extensible Sliver Pool`

with:

`1–9 Slivers per Alloy`.

Any migration plan, registry, validation, or canon that treats 27 native pieces as the final target must eventually be superseded or projected through compatibility.

Historical references must not be rewritten to pretend this decision existed earlier.

---

# 49. SLIVER POOL EVOLUTION

The Sliver Pool may grow or shrink as capabilities are:

- discovered;
- generalized;
- merged;
- superseded;
- decomposed;
- retired.

Pool size has no canonical fixed number.

Quality is determined by coverage and orthogonality, not quantity.

---

# 50. POOL MINIMIZATION

Coalesce SHOULD periodically identify:

- duplicate capabilities;
- near-duplicate Slivers;
- unreachable Slivers;
- obsolete Slivers;
- over-specialized Slivers;
- capabilities better represented as configuration.

This analysis may propose consolidation.

It may not mutate authority automatically.

---

# 51. CAPABILITY COVERAGE MAP

Coalesce SHOULD maintain a projection of:

`application capability -> Slivers capable of providing it`

This enables:

- gap detection;
- redundancy analysis;
- composition planning;
- migration;
- substitution.

The coverage map is derived projection, not separate authority.

---

# 52. CAPABILITY GAP DETECTION

If a requested Alloy cannot be formed from nine or fewer Slivers, Coalesce SHOULD identify exactly why.

Possible gap classes:

- missing capability;
- incompatible capabilities;
- excessive fragmentation;
- missing adapter;
- unavailable provider;
- forbidden authority crossing;
- projection limitation.

The planner SHOULD propose the smallest architectural remedy.

---

# 53. NOVEL SLIVER ADMISSION

A proposed new Sliver must demonstrate:

1. distinct semantic capability;
2. reuse beyond one narrow application where practical;
3. no existing equivalent;
4. clean contract;
5. parameterization potential;
6. graph addressability;
7. compatibility with the nine-Sliver model.

Application convenience alone is insufficient.

---

# 54. SLIVER PROMOTION

Experimental implementation SHOULD NOT immediately become canonical Sliver authority.

Preferred lifecycle:

`candidate`

→ `evaluated`

→ `accepted`

→ `active`

→ optionally `superseded`

Historical stages remain attributable.

---

# 55. SLIVER QUALITY SCORE

Coalesce MAY project a quality score for composition planning.

Potential factors:

- reuse count;
- test status;
- deterministic behavior;
- contract stability;
- dependency burden;
- performance;
- accessibility;
- error rate;
- compatibility breadth.

A projected score does not become semantic authority.

---

# 56. CONFLICT GRAPH

Coalesce SHOULD represent incompatible Sliver combinations explicitly.

Typed relations may include:

- conflicts-with;
- requires;
- prefers;
- substitutes-for;
- supersedes;
- decorates;
- adapts.

This makes Alloy feasibility deterministic and inspectable.

---

# 57. DEPENDENCY GRAPH

Every materialized Alloy SHOULD expose a dependency graph containing:

- Alloy;
- selected Slivers;
- lower-order instances;
- adapters;
- providers;
- external calls;
- projections;
- significant data inputs.

Hidden dependencies are defects.

---

# 58. PROVENANCE

Every Sliver derived from an earlier application should preserve its extraction provenance.

Example:

`source application behavior`

→ `generic capability extraction`

→ `canonical Sliver`

The Sliver is not permanently semantically owned by the source application.

---

# 59. LINEAGE

Alloy lineage SHOULD identify:

- parent recipe where applicable;
- composition digest;
- constituent Sliver identities;
- Sliver versions;
- significant configuration;
- migration source;
- projection lineage.

---

# 60. REPLAY

A historical Alloy execution SHOULD preserve enough metadata to recover its semantic composition.

Minimum replay identity:

- Alloy Recipe;
- recipe version;
- Sliver identities;
- Sliver versions;
- configuration;
- relevant provider/interface versions;
- input digest where appropriate.

---

# 61. DETERMINISM

Equivalent semantic inputs SHOULD resolve to equivalent semantic composition.

Equivalent inputs include:

- capability request;
- Sliver Pool version;
- policy;
- configuration;
- availability state.

Presentation animation, timing, and explicitly nondeterministic visual effects are not semantic composition.

---

# 62. CACHING

Derived composition plans MAY be cached by semantic digest.

Cache entries MUST be invalidated when relevant:

- Sliver contract;
- configuration;
- policy;
- capability availability;
- compatibility graph

changes.

Caches never become authority.

---

# 63. PARALLELISM

Independent Sliver operations MAY execute concurrently when:

- ordering is not semantically required;
- shared mutation is controlled;
- deterministic result semantics are preserved.

Concurrency is implementation optimization.

It must not create hidden ordering dependencies.

---

# 64. SCHEDULING

Coalesce MAY maintain a dependency-aware execution schedule derived from the Alloy graph.

Scheduling SHOULD favor:

- independent parallel work;
- explicit barriers;
- deterministic dependency resolution;
- bounded resource use.

---

# 65. RESOURCE BUDGETS

An Alloy MAY define budgets for:

- memory;
- CPU;
- network;
- latency;
- external calls;
- storage;
- rendering complexity.

Budgets are configuration and policy, not new Slivers.

---

# 66. OBSERVABILITY

Coalesce SHOULD expose non-authoritative runtime observations including:

- active Alloy;
- selected Slivers;
- composition digest;
- degraded capabilities;
- dependency health;
- execution timings;
- provider status.

Observability does not modify composition authority.

---

# 67. COMPOSITION RECEIPT

Every successful materialization SHOULD be capable of producing a composition receipt containing:

- Alloy ID;
- recipe ID;
- composition digest;
- Sliver IDs;
- versions;
- configuration digests;
- dependency summary;
- projection ID;
- timestamp;
- warnings/degraded state.

This supports audit and replay.

---

# 68. VALIDATION

Before activation, an Alloy SHOULD validate:

1. Sliver count <= 9;
2. every Sliver resolves;
3. contracts are compatible;
4. required dependencies resolve;
5. forbidden Exile embedding is absent;
6. typed segues resolve;
7. configuration validates;
8. provider boundaries remain visible;
9. projection is supported;
10. authority boundaries remain intact.

---

# 69. SCHEMA VALIDATION

Machine-readable Coalesce contracts SHOULD use formal schemas where useful.

JSON Schema is appropriate for portable data-contract validation.

Typed implementation environments MAY additionally use native type systems.

Schema tooling is support infrastructure, not architectural authority.

---

# 70. RECOMMENDED IMPLEMENTATION TECHNIQUES

The following techniques are compatible with this architecture when materially useful:

- JSON Schema for portable manifest validation;
- Pydantic for typed Python contracts where Python owns the implementation;
- dataclasses for lightweight internal immutable structures;
- semantic content hashing;
- topological sorting for dependency execution;
- constraint solving / set-cover heuristics for Sliver selection;
- event-driven boundaries for loosely coupled runtime operations;
- structured concurrency for independent execution;
- capability negotiation;
- dependency injection at declared ports;
- content-addressable composition receipts.

External libraries MUST remain subordinate to Savant authority.

---

# 71. OPTIONAL LIBRARY POLICY

Dependencies are admitted only if they materially improve:

- correctness;
- deterministic validation;
- interoperability;
- accessibility;
- significant performance;
- maintainability;
- security;
- composition planning.

Core composition semantics MUST NOT require a dependency merely because it is fashionable or convenient.

Optional tooling SHOULD degrade cleanly.

---

# 72. Pydantic

Pydantic is a suitable optional implementation primitive for:

- Sliver manifests;
- Alloy Recipes;
- configuration contracts;
- composition receipts;
- typed validation.

It MUST NOT own canonical definitions.

Canonical semantics remain Savant authority.

---

# 73. JSON SCHEMA

JSON Schema is suitable for interoperable validation of:

- Sliver manifests;
- Alloy Recipes;
- port contracts;
- adapters;
- providers;
- receipts.

Schemas SHOULD be generated or projected from authoritative primitives where practical rather than independently maintained duplicate authority.

---

# 74. GRAPH TOOLING

Graph libraries such as NetworkX MAY assist:

- cycle detection;
- topological ordering;
- reachability;
- dependency analysis;
- compatibility analysis.

Graph libraries do not become the canonical graph.

The Savant graph remains authoritative.

---

# 75. CONSTRAINT SOLVING

Constraint-solving techniques MAY materially improve automatic Alloy planning.

Potential uses:

- <=9 Sliver enforcement;
- capability coverage;
- incompatibility avoidance;
- dependency satisfaction;
- cost minimization.

An implementation MAY use:

- deterministic set-cover heuristics;
- SAT/SMT;
- integer programming;
- specialized constraint libraries.

The solver is an implementation primitive.

Its output is a proposal until accepted by applicable runtime policy.

---

# 76. SECURITY

A Sliver MUST NOT gain undeclared access merely because another Sliver has that access.

Capability boundaries SHOULD make security-relevant access explicit.

Examples:

- filesystem;
- network;
- process execution;
- credentials;
- mutation;
- external API use.

Alloy composition does not expand authority automatically.

---

# 77. LEAST CAPABILITY

Each Sliver SHOULD receive only the capabilities required for its declared behavior.

Prefer:

`explicit capability grant`

over:

`shared global runtime access`.

This reduces hidden coupling and accidental authority propagation.

---

# 78. MUTATION

Durable Savant mutation remains governed by the legitimate mutation owner.

A Coalesce Alloy MUST NOT silently bypass mutation authority merely because it presents an editor or command surface.

Composition permission is not mutation authority.

---

# 79. EXTERNAL SERVICES

External services remain behind providers or authorized Exile calls.

No external service becomes a Sliver solely because an Alloy uses it.

A Sliver may wrap provider-neutral application semantics around an external capability while preserving external ownership.

---

# 80. MULTI-ALLOY COMPOSITION

If a product exceeds the coherent nine-Sliver boundary, it may consist of multiple cooperating Alloys.

Each Alloy remains independently addressable.

Relationships between Alloys SHOULD use explicit typed interfaces.

Do not create one giant Alloy merely to avoid acknowledging multiple application domains.

---

# 81. ALLOY OF ALLOYS

An Alloy MUST NOT bypass the Sliver cap by treating another complete Alloy as an ordinary Sliver.

Alloy-to-Alloy composition is federation, not internal Sliver composition.

Federation must preserve independent Alloy identity.

---

# 82. FEDERATION

Multiple Alloys MAY cooperate through:

- events;
- commands;
- queries;
- typed segues;
- shared providers;
- shared projections;
- authorized external interfaces.

Federation is appropriate for large systems that would otherwise violate single-Alloy cohesion.

---

# 83. NESTING

Arbitrary recursive Sliver nesting is prohibited when used to obscure actual composition complexity.

Internal implementation decomposition is permitted.

Canonical primary composition remains visible as no more than nine Slivers.

---

# 84. PRESENTATION SYSTEMS

A Sliver may expose presentation semantics without binding them to one framework.

Examples:

- collection view;
- detail surface;
- graph surface;
- command surface;
- editor surface.

React, DOM, terminal, native, or other implementations are projections.

---

# 85. RESPONSIVE PROJECTION

Responsive behavior belongs to presentation projection unless it materially changes application semantics.

Do not create desktop and mobile Sliver duplicates solely for layout differences.

---

# 86. ACCESSIBILITY

Projection contracts SHOULD expose enough semantic structure for accessible renderers.

Accessibility concerns SHOULD be treated as first-class projection requirements rather than optional visual patches.

---

# 87. OFFLINE DEGRADATION

Where feasible, an Alloy SHOULD remain partially functional when optional network providers are unavailable.

Offline behavior must be explicit.

Do not fabricate remote data.

---

# 88. SERIALIZATION

Canonical Alloy Recipes and Sliver manifests SHOULD use deterministic serialization where digests or replay depend on them.

Equivalent semantic objects should serialize equivalently under the canonical serializer.

---

# 89. CONTENT ADDRESSING

Immutable composition artifacts MAY use content-addressed identity.

Useful targets include:

- recipe snapshots;
- composition receipts;
- schema projections;
- Sliver package artifacts.

Content hashes complement semantic IDs.

They do not replace semantic identity.

---

# 90. PACKAGE BOUNDARIES

A Sliver's implementation package SHOULD contain only what belongs to that Sliver.

Shared reusable lower-order substance should remain shared.

Do not vendor duplicated Prodigal/Quirk substance into every Sliver.

---

# 91. SLIVER INTERFACE STABILITY

A Sliver SHOULD expose a small stable public contract.

Implementation internals may evolve without forcing Alloy Recipe changes when semantics remain compatible.

---

# 92. TESTABILITY

A Sliver SHOULD be independently testable against its contract.

An Alloy SHOULD be testable from its Recipe without manually reconstructing hidden dependencies.

Do not create large dedicated testing infrastructure for one localized Sliver.

---

# 93. GENERATED CODE

Generated projection code MAY be derived from an Alloy Recipe.

Generated code is a projection artifact.

The Recipe and canonical Slivers remain the semantic source.

Do not treat generated UI code as duplicate application authority.

---

# 94. ROUND-TRIP SAFETY

Where Coalesce supports editing through generated projections, edits must not silently mutate canonical Sliver definitions.

Changes should resolve to:

- configuration;
- new recipe;
- authorized Sliver evolution;
- external mutation proposal.

---

# 95. COMPOSITION DIFF

Coalesce SHOULD support semantic comparison between two Alloy Recipes.

A composition diff SHOULD identify:

- added Slivers;
- removed Slivers;
- version changes;
- parameter changes;
- segue changes;
- provider changes;
- projection changes.

Avoid line-oriented source diff as the only semantic comparison.

---

# 96. EXPLAINABILITY

Coalesce SHOULD be able to explain a composition decision without exposing irrelevant implementation internals.

An explanation may state:

- required capabilities;
- selected Slivers;
- why each was selected;
- alternatives rejected;
- unsatisfied constraints.

---

# 97. SLIVER RECOMMENDATION

Coalesce MAY recommend an existing Sliver when a developer proposes duplicate functionality.

Recommendation does not automatically alter files or authority.

---

# 98. COMPOSITION LINTING

Coalesce SHOULD identify architectural defects such as:

- >9 Slivers;
- duplicate capabilities;
- undeclared dependencies;
- unused Slivers;
- incompatible contracts;
- hidden provider coupling;
- source-domain contamination;
- embedded Exiles;
- circular required dependencies;
- non-replayable configuration.

---

# 99. CYCLE POLICY

Required dependency cycles between Slivers are invalid unless explicitly modeled as a safe mutually coordinated runtime protocol.

Default policy is acyclic dependency composition.

Event feedback loops may exist where their semantics are explicit and bounded.

---

# 100. CONFIGURATION OVER CREATION

Before creating a new Sliver, check whether the required variation can be expressed through:

- parameter;
- mode;
- attachment;
- Quirk instance;
- Prodigal instance;
- adapter;
- provider;
- typed segue;
- projection.

New Sliver creation is the final option.

---

# 101. ADAPTATION OVER FORKING

When a Sliver nearly satisfies a use case, prefer a reusable adapter or optional attachment rather than an Alloy-specific fork.

---

# 102. COMPOSITION OVER INHERITANCE

Prefer capability composition over deep inheritance edifices.

Slivers should be independently reusable.

Shared behavior belongs in reusable primitives rather than fragile class ancestry.

---

# 103. IMMUTABILITY BY DEFAULT

Canonical Sliver definitions and accepted Alloy Recipe versions SHOULD be immutable records.

Evolution occurs through new versions or supersession.

Runtime instance state remains mutable where required.

---

# 104. IDEMPOTENT MATERIALIZATION

Given the same accepted Recipe and semantic environment, repeated materialization SHOULD avoid duplicate persistent artifacts.

Materialization SHOULD be idempotent where practical.

---

# 105. ROLLBACK

Material composition changes SHOULD permit recovery to the previous accepted Recipe where rollback is materially warranted.

Rollback does not erase failed composition history.

---

# 106. COMPOSITION SANDBOX

Candidate Alloy Recipes MAY be materialized in an isolated preview context before activation.

Preview state does not become canonical simply because it executed successfully.

---

# 107. SHADOW COMPOSITION

A candidate Sliver or Recipe MAY run in shadow mode beside the active composition for comparison without receiving active authority.

Useful for:

- migrations;
- performance comparison;
- compatibility validation.

---

# 108. SLIVER CHAMPION / CHALLENGER

Where multiple Slivers legitimately provide the same semantic capability, Coalesce MAY designate:

- active champion;
- candidate challenger.

Replacement requires evidence and explicit supersession.

Do not delete the historical champion.

---

# 109. USAGE TELEMETRY

Runtime observations MAY inform future Sliver evaluation.

Examples:

- failure rate;
- latency;
- frequency of use;
- fallback frequency;
- incompatibility frequency.

Telemetry is evidence, not self-authorizing architecture.

---

# 110. AUTO-OPTIMIZATION

Coalesce MAY propose optimized Recipes based on observed usage.

It MUST NOT autonomously rewrite accepted Alloy composition without applicable authority.

---

# 111. SLIVER EQUIVALENCE

Equivalent Slivers SHOULD be represented through explicit equivalence or substitution relationships rather than duplicated hidden semantics.

---

# 112. PLATFORM ADAPTATION

Platform-specific implementation should normally terminate in:

- adapters;
- providers;
- projection code.

Avoid platform-specific duplicate Slivers unless platform semantics materially change the capability itself.

---

# 113. NETWORK BOUNDARIES

Remote Slivers are not a separate semantic class.

A Sliver may be local or remotely backed provided the same declared capability contract remains valid.

Network topology is implementation/runtime metadata.

---

# 114. DISTRIBUTED ALLOYS

Coalesce MAY eventually materialize Alloys whose Slivers execute across multiple processes or hosts.

The semantic Recipe must remain independent of deployment topology where practical.

---

# 115. CAPABILITY DISCOVERY

Coalesce SHOULD support deterministic discovery of available Slivers and declared capabilities.

Discovery MUST NOT rely solely on scanning filenames.

Canonical registry and graph identity remain primary.

---

# 116. REGISTRY

The Sliver registry SHOULD store authoritative primitives only.

Derived indices such as:

- capability lookup;
- compatibility matrix;
- usage ranking;
- search index

should be deterministically projected.

---

# 117. DECLARATIVE FIRST

Alloy composition SHOULD be declarative where practical.

Recipes describe:

`what capabilities compose the Alloy`

rather than embedding imperative orchestration code for every connection.

Imperative runtime behavior may implement declared semantics.

---

# 118. PURE TRANSFORMS

Sliver operations that can be pure transformations SHOULD remain pure.

Pure operations improve:

- determinism;
- caching;
- testing;
- replay;
- parallelism.

Stateful behavior remains allowed where semantically required.

---

# 119. SIDE-EFFECT DECLARATION

Slivers with side effects MUST declare them.

Potential effect classes:

- filesystem read;
- filesystem write;
- network;
- process;
- database read;
- database write;
- credential access;
- external mutation.

Hidden side effects are defects.

---

# 120. EFFECT GATING

Effectful operations SHOULD pass through explicit capability/authority gates.

A Recipe selecting a Sliver does not itself grant effects.

---

# 121. STATIC ANALYSIS

Coalesce SHOULD be capable of validating much of an Alloy before execution.

Static checks may include:

- Sliver count;
- capability coverage;
- port compatibility;
- required provider presence;
- graph cycles;
- forbidden embedding;
- known conflicts.

---

# 122. RUNTIME VALIDATION

Runtime checks should focus on facts unavailable statically:

- provider availability;
- dynamic data constraints;
- runtime permission;
- resource availability.

Avoid repeating static validation unnecessarily.

---

# 123. COMPOSITION PERFORMANCE

Performance optimization should preserve semantic equivalence.

Valid techniques include:

- memoization;
- lazy activation;
- batching;
- parallel independent execution;
- incremental projection;
- virtualized rendering.

Optimization does not alter canonical semantics.

---

# 124. INCREMENTAL RECOMPUTATION

When only one Sliver input changes, Coalesce SHOULD avoid recomputing unrelated Sliver results where dependency structure permits.

---

# 125. STRUCTURAL SHARING

Different Alloys SHOULD share canonical Sliver definitions and immutable artifacts rather than duplicating them.

This is a core storage and maintenance optimization.

---

# 126. LATE BINDING

Runtime-specific providers MAY be bound late when doing so preserves semantic contract and improves portability.

The Recipe identifies required capability, not necessarily one hardcoded provider.

---

# 127. FEATURE FLAGS

Feature flags MAY enable optional projected or experimental behavior.

A feature flag SHOULD NOT substitute for clear Sliver identity when semantics are materially distinct.

---

# 128. POLICY SEPARATION

Composition policy must remain separable from Sliver implementation.

Examples:

- maximum resource budget;
- allowed providers;
- security policy;
- preferred projection;
- optimization objective.

Do not hardcode system-wide policy into individual Slivers.

---

# 129. MULTIPLE VALID ALLOYS

One capability request may have multiple valid Alloy Recipes.

Coalesce MAY rank them using policy.

Ranking should consider:

- Sliver count;
- compatibility;
- dependency burden;
- determinism;
- performance;
- accessibility;
- reuse;
- runtime availability.

---

# 130. RECIPE LOCKING

An accepted production Alloy MAY pin exact Sliver versions for deterministic reproducibility.

Development Recipes MAY permit compatible version ranges under explicit policy.

---

# 131. SUPPLY-CHAIN SECURITY

External library and repository reuse MUST evaluate:

- license;
- provenance;
- maintenance;
- security history;
- transitive dependencies;
- version pinning;
- reproducibility.

Public popularity alone is not sufficient admission evidence.

---

# 132. EXTERNAL CODE REUSE

Public code MAY be used as:

- technique;
- algorithm;
- adapter primitive;
- optional library.

It MUST NOT be copied blindly into canonical Slivers.

Reuse must preserve license attribution where required.

---

# 133. DEPENDENCY BUDGET

Each Sliver SHOULD minimize external dependencies.

A dependency must materially improve:

- correctness;
- performance;
- compatibility;
- accessibility;
- security;
- maintainability;
- functionality.

---

# 134. PORTABILITY

A Sliver SHOULD avoid unnecessary environmental assumptions.

Runtime-specific requirements must be declared.

---

# 135. SERIALIZABLE CONFIGURATION

Alloy configuration SHOULD be serializable using neutral formats where practical.

Executable code should not be required merely to express ordinary configuration.

---

# 136. SECRET HANDLING

Secrets MUST NOT appear in:

- Alloy Recipes;
- Sliver manifests;
- composition receipts;
- canon;
- lineage records;
- provenance records.

Only secret identifiers or availability state may be referenced.

Credential ownership remains with the legitimate capability owner.

---

# 137. USER EXTENSION

Future user-authored Slivers MAY be supported through the same contract system.

User Slivers do not gain canonical Savant authority automatically.

---

# 138. TRUST CLASSES

Slivers MAY expose trust state such as:

- canonical;
- accepted;
- experimental;
- external;
- user-defined;
- quarantined;
- superseded.

Trust state should affect composition policy.

---

# 139. QUARANTINE

A defective or unsafe Sliver SHOULD be quarantinable without destroying its history or breaking interpretation of historical Recipes.

---

# 140. DEPRECATION

Deprecation warns against new composition.

Supersession identifies the preferred replacement.

Neither operation deletes historical identity.

---

# 141. SLIVER DOCUMENTATION

A Sliver SHOULD be understandable from its manifest and contract without requiring inspection of all implementation code.

Minimum documentation:

- purpose;
- provided capabilities;
- required capabilities;
- configuration;
- effects;
- compatibility;
- examples.

---

# 142. ALLOY DOCUMENTATION

An Alloy's Recipe SHOULD be sufficient to explain its primary structure.

Do not maintain a second manually synchronized architecture description where deterministic projection can generate it.

---

# 143. RECIPE VISUALIZATION

Coalesce MAY project an Alloy Recipe into a graph or visual composer.

The visual representation is projection.

Editing it must result in validated Recipe changes.

---

# 144. INTERACTIVE COMPOSER

A future Coalesce interface MAY allow:

- drag/drop Slivers;
- capability search;
- compatibility indication;
- automatic adapter suggestions;
- live count up to nine;
- dependency preview;
- composition validation;
- projection preview.

The visual composer must not create a second composition authority.

---

# 145. NATURAL-LANGUAGE COMPOSITION

A future interface MAY allow:

`describe application`

→ capability requirements

→ candidate Alloy Recipe

The generated Recipe remains a proposal until validated.

AI-generated composition never becomes authority merely because an AI proposed it.

---

# 146. GAP-DRIVEN SLIVER EVOLUTION

When composition repeatedly fails because of the same capability gap, Coalesce MAY surface evidence that a new Sliver or generalized existing Sliver is warranted.

---

# 147. DIFFERENTIAL TEST SUITE

The Sliver Pool SHOULD eventually be evaluated against a representative application capability corpus.

The purpose is to determine whether the pool can construct materially diverse Alloys within the nine-Sliver cap.

This is more meaningful than maximizing raw Sliver count.

---

# 148. COVERAGE TARGET

The design target is:

**a compact Sliver Pool capable of covering nearly all ordinary Savant application requirements with no more than nine selected Slivers per Alloy.**

"Nearly all" is an engineering target, not a claim of mathematical universality.

Capabilities outside the pool may be handled through:

- lower-order elements;
- adapters;
- providers;
- authorized Exile calls;
- multiple federated Alloys;
- future Sliver admission.

---

# 149. 50-PASS REFINEMENT RESULT

This contract represents the distilled result of fifty conceptual refinement passes over the following optimization objective:

1. maximize Alloy expressiveness;
2. enforce <=9 primary pieces;
3. reduce Sliver overlap;
4. maximize reuse;
5. preserve Savant authority;
6. preserve existing lower-order composition;
7. keep Exiles external;
8. preserve graph visibility;
9. preserve deterministic replay;
10. allow heterogeneous projections;
11. minimize dependency burden;
12. support automated planning;
13. permit static validation;
14. support runtime degradation;
15. preserve historical interpretation;
16. support extensible Sliver admission;
17. minimize hidden coupling;
18. separate semantics from presentation;
19. separate composition from deployment;
20. support future federation.

The fifty iterations are intentionally distilled into the resulting invariants rather than stored as fifty competing architectural drafts.

---

# 150. ADVANCED ENHANCEMENTS — ACCEPTED TARGETS

The following contemporary enhancements are accepted implementation targets where they can be added without violating higher authority:

1. capability manifests;
2. machine-readable Sliver contracts;
3. formal port schemas;
4. typed segues;
5. deterministic composition digests;
6. automatic minimal-set planning;
7. compatibility graphs;
8. semantic composition linting;
9. static Alloy validation;
10. composition receipts;
11. deterministic replay;
12. semantic Recipe diffs;
13. lazy Sliver activation;
14. incremental recomputation;
15. structural sharing;
16. atomic hot recomposition;
17. transaction-safe recomposition;
18. candidate composition sandboxing;
19. shadow Recipes;
20. champion/challenger Slivers;
21. capability gap detection;
22. redundancy detection;
23. automatic adapter recommendation;
24. dependency health projection;
25. explicit degradation states;
26. late provider binding;
27. capability-based security grants;
28. side-effect declarations;
29. resource budgets;
30. dependency-aware scheduling;
31. safe parallel execution;
32. semantic caching;
33. content-addressed immutable artifacts;
34. Sliver lifecycle state;
35. trust classes;
36. quarantine;
37. supply-chain admission checks;
38. schema-driven configuration;
39. headless Alloy execution;
40. multi-projection output;
41. interactive visual composition;
42. natural-language Recipe proposals;
43. Alloy federation;
44. platform-neutral semantics;
45. accessibility-aware projection contracts;
46. runtime observability;
47. provenance explorer;
48. Recipe visualization;
49. Sliver coverage benchmarking;
50. gap-driven Sliver evolution.

These are implementation targets, not authorization to create unnecessary infrastructure in one task.

---

# 151. REQUIRED INVARIANTS

The following are canonical invariants:

1. Coalesce is the system.
2. Alloy is the assembled application.
3. Sliver is the primary reusable application piece.
4. An Alloy contains 1–9 Slivers.
5. Nine is the maximum primary Sliver count.
6. The Sliver Pool has no fixed canonical size.
7. Slivers are reusable and domain-neutral by default.
8. Slivers compose lower-order Savant substance rather than duplicate it.
9. Prodigals and Quirks may be instanced below Slivers.
10. Exiles cannot be embedded in Alloys.
11. Exiles may be called through authorized contracts.
12. Recipes are declarative composition authority for Alloy structure.
13. UI is projection, not Alloy identity.
14. Typed segues expose relationships.
15. Hidden dependencies are defects.
16. Runtime state is not automatically authority.
17. Composition does not confer mutation authority.
18. Equivalent application variations should be configuration before new Sliver creation.
19. Historical 81-piece and 27-piece models remain historical evidence.
20. Functional breadth comes from composition, not raw Sliver count.

---

# 152. PROHIBITED COMPOSITION

The following are prohibited:

- more than nine Slivers in one Alloy;
- hiding additional primary Slivers inside wrapper Slivers;
- embedding an Exile;
- copying Exile implementation into an Alloy;
- application-specific duplicate Slivers where configuration suffices;
- domain-contaminated generic Slivers;
- hidden provider ownership;
- hidden side effects;
- silent authority promotion;
- silent Recipe reinterpretation;
- silent historical deletion;
- duplicate canonical capability definitions;
- using generated projection code as separate application authority;
- bypassing the nine-Sliver cap through nested Alloys;
- treating an entire Alloy as an ordinary Sliver.

---

# 153. PREFERRED COMPOSITION

Prefer:

`Sliver instance`

over copied implementation.

Prefer:

`configuration`

over new Sliver.

Prefer:

`Prodigal/Quirk instance`

over duplicated lower-order behavior.

Prefer:

`typed segue`

over hidden coupling.

Prefer:

`adapter`

over source-specific modifications.

Prefer:

`provider`

over ownership transfer.

Prefer:

`projection`

over duplicated application semantics.

Prefer:

`authorized Exile call`

over embedded Exile.

Prefer:

`federated Alloys`

over one incoherent Alloy exceeding nine Slivers.

Prefer:

`smallest sufficient Alloy`

over maximal composition.

---

# 154. MIGRATION DIRECTIVE

Future Coalesce migration must now target:

`historical pieces`

→ explicit semantic disposition

→ `Sliver Pool + Alloy Recipes`

not:

`historical pieces`

→ `27 permanent primitives`.

Before migration, every historical piece must be classified.

No behavior may be silently discarded.

The separate Coalesce migration/compatibility authority must be superseded where it conflicts with this new Sliver/Alloy model while preserving its historical evidence requirements.

---

# 155. MINIMUM IMPLEMENTATION VALIDATION

For future implementation work, default validation is:

1. syntax/schema validation;
2. one focused Alloy composition test;
3. one relevant integration/projection check.

Do not create oversized validation infrastructure merely to satisfy one localized implementation task.

---

# 156. COMPLETION CONDITION

The Coalesce composition architecture is correctly realized when:

1. a canonical Sliver Pool exists;
2. Slivers expose stable capability contracts;
3. Alloy Recipes select no more than nine Slivers;
4. Coalesce can resolve and validate a Recipe;
5. selected Slivers remain graph-addressable;
6. Prodigal and Quirk instances remain reusable below Slivers;
7. Exiles remain outside Alloy composition;
8. external Exile capability calls remain explicit;
9. a materially different set of applications can be formed from the same Sliver Pool;
10. at least one representative complex Alloy can be built within nine Slivers;
11. composition receipts and lineage identify what was assembled;
12. historical Coalesce capabilities have explicit migration dispositions;
13. browser/UI implementations remain projections rather than canonical Alloy identity;
14. no known architectural blocker prevents additional Alloys from being composed from the same pool.

Once these conditions are satisfied, this architecture is complete.

Do not continue expanding Coalesce merely because additional abstractions are possible.

---

# 157. CANONICAL SUMMARY

**Coalesce** is the composition system.

**Alloy** is an assembled application.

**Sliver** is a reusable application capability.

The canonical structure is:

`Sliver Pool`

→ select the smallest sufficient compatible subset

→ configure instances

→ connect through typed segues

→ compose **1–9 Slivers**

→ materialize an **Alloy**

→ project the Alloy into browser, terminal, API, or other interfaces.

Functional breadth comes from:

`Slivers + configuration + Prodigals + Quirks + adapters + providers + typed segues + projections + authorized external calls`

not from an ever-growing number of application-specific pieces.

The nine-Sliver limit is a design pressure toward stronger primitives, clearer composition, and greater reuse.

Coalesce builds Alloys.

Alloys are made of Slivers.

Slivers remain reusable.

Exiles remain external capability owners.

Authority remains where it belongs.
