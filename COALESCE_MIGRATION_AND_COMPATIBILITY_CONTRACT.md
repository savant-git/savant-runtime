# COALESCE — MIGRATION AND COMPATIBILITY CONTRACT

Status: ACCEPTED DESIGN AUTHORITY
System: Savant Runtime
Component: `prodigal:modus:coalesce`
Owner: `exile:modus`

This document defines how the verified historical Coalesce implementation may eventually migrate to the accepted 27-native-primitive architecture without losing behavior, lineage, provenance, recipe meaning, or recoverability.

This is migration authority.

It is not authorization to begin the migration before the current application-integration task is complete.

---

# 1. BASELINE

The current verified Coalesce implementation is the migration baseline.

Historical implementation evidence includes:

- 81 registered pieces;
- 9 historical service families;
- 9 historical recipes;
- 27 mood bindings;
- neutral record processing;
- deterministic piece execution;
- Filament projection;
- browser projection;
- recipe compilation;
- composition tracing.

The future architecture targets:

- 27 native primitives;
- 3 canonical families;
- Prodigal instances;
- Quirk instances;
- external Exile calls;
- adapters;
- providers;
- projections;
- typed segues;
- deterministic recipes.

Migration must bridge these models.

---

# 2. MIGRATION PRINCIPLE

Migration is:

`semantic projection`

not:

`delete old system and write new system`

Every historical capability must receive an explicit disposition before its historical representation may be retired.

---

# 3. IMMUTABLE HISTORY

Historical identities and historical recipes are evidence of previous implementation state.

Migration must not rewrite history to pretend the 27-primitive architecture always existed.

Where history is retained, preserve:

- old identity;
- old canonical name;
- old family;
- old behavior;
- old recipe membership;
- supersession relationship;
- target representation.

---

# 4. SUPERSESSION

When a historical piece is replaced by a new canonical representation, record:

`historical identity -> superseded by -> target identity/configuration`

Do not silently rename the old piece in historical records.

---

# 5. REQUIRED DISPOSITION CLASSES

Every historical piece must resolve to exactly one primary disposition:

1. `native`
2. `configuration`
3. `prodigal-instance`
4. `quirk-instance`
5. `adapter`
6. `provider`
7. `projection`
8. `compatibility`
9. `external-existing-capability`
10. `superseded`

No historical piece may remain unclassified when migration is accepted.

---

# 6. NATIVE

Use `native` when the historical behavior is intrinsic to Coalesce's generic application-composition grammar.

Its target must be one of the accepted 27 native primitives.

---

# 7. CONFIGURATION

Use `configuration` when the historical piece differs from another capability principally by:

- predicate;
- field;
- mode;
- parameter;
- ordering;
- presentation selection;
- policy.

Example candidates include historical lenses that differ only in which field or predicate they apply.

---

# 8. PRODIGAL INSTANCE

Use `prodigal-instance` when an existing or appropriately canonical Prodigal owns the reusable behavior better than Coalesce.

Coalesce references an instance.

It does not duplicate the Prodigal.

---

# 9. QUIRK INSTANCE

Use `quirk-instance` for narrow reusable behavior that properly belongs as a Quirk.

The Quirk remains canonically independent.

Coalesce stores or resolves only its instance relationship and configuration.

---

# 10. ADAPTER

Use `adapter` when the historical behavior principally converts a source representation into a neutral Coalesce representation.

Adapters do not own the source or destination authority.

---

# 11. PROVIDER

Use `provider` when behavior principally obtains external data or capability.

Providers expose dependencies explicitly.

---

# 12. PROJECTION

Use `projection` when behavior principally determines how semantic application state is represented through an interface or execution surface.

Examples may include:

- browser-specific rendering;
- Filament-specific realization;
- print representation;
- export representation.

---

# 13. COMPATIBILITY

Use `compatibility` when a historical identity must continue resolving temporarily even though its canonical implementation has moved elsewhere.

Compatibility must have an intended retirement condition.

Do not turn compatibility into permanent duplicate architecture.

---

# 14. EXTERNAL EXISTING CAPABILITY

Use `external-existing-capability` when Savant already possesses an authoritative capability that should be called or instanced rather than duplicated by Coalesce.

This classification is especially important during migration.

Historical Coalesce code does not outrank stronger existing Savant ownership merely because Coalesce already implemented something similar.

---

# 15. SUPERSEDED

Use `superseded` only when:

- stronger authority explicitly replaces the behavior;
- the behavior is genuinely redundant;
- the behavior is defective and explicitly rejected;
- its semantics are completely covered by another accepted representation.

A reason is required.

---

# 16. MIGRATION MANIFEST

Before modifying the historical registry, create a machine-readable migration manifest.

Each historical piece entry must identify:

- historical piece ID;
- historical canonical name;
- historical service;
- historical moods where applicable;
- historical recipes using it;
- target disposition;
- target canonical identity;
- target parameters where applicable;
- compatibility identity where applicable;
- dependencies;
- dependents;
- migration reason;
- verification status.

The manifest is the deterministic bridge between architectures.

---

# 17. NO UNMAPPED DELETION

A historical piece may not be removed from active resolution unless its migration manifest entry is complete.

This is a hard migration invariant.

---

# 18. RECIPE COMPATIBILITY

Historical recipe identity should remain resolvable where practical.

A historical recipe may compile into a new composition.

Conceptually:

`historical recipe`

-> `compatibility resolver`

-> `27-primitive composition + instances + configuration`

The recipe does not need to retain its historical execution count.

It must retain materially relevant behavior.

---

# 19. RECIPE IDENTITY

If recipe semantics remain materially equivalent, preserve recipe identity.

If semantics materially change, create a new recipe identity and explicitly supersede the old one.

Do not silently alter meaning under an unchanged identity.

---

# 20. RECIPE COUNT

The historical existence of nine recipes does not require Coalesce to contain exactly nine recipes forever.

Recipes are compositions, not native architectural primitives.

New recipes may be added as applications require them.

---

# 21. PIECE COUNT COMPATIBILITY

Historical outputs may report historical piece counts.

Future outputs should distinguish:

- native primitive count;
- instantiated component count;
- compatibility-resolved historical count where relevant;
- executed component count.

Do not label different quantities with the same ambiguous field.

---

# 22. HISTORICAL 81

The historical count of 81 is implementation provenance.

It must not become a future requirement.

The target canonical native count is 27.

---

# 23. COMPOSITION COUNT

A formal composition governed by Coalesce's accepted numerical invariant contains:

- 3 components;

or:

- a positive multiple of 9 components.

Do not add dummy components merely to satisfy the invariant.

Composition structure must remain semantically meaningful.

---

# 24. NO SIX STRUCTURE

Migration must not introduce six as a deliberate canonical structural count.

This applies to newly designed:

- families;
- tiers;
- primitive groups;
- mandatory composition groups;
- canonical migration phases.

Incidental data values are not architectural structure.

---

# 25. EXILE MIGRATION RULE

If historical Coalesce functionality duplicates or embeds Exile-owned behavior:

1. identify the legitimate Exile owner;
2. identify its authorized interface;
3. replace internal ownership with an external provider/call;
4. preserve compatibility where necessary;
5. record the dependency explicitly.

Do not migrate an embedded Exile into the new Coalesce architecture.

---

# 26. PRODIGAL MIGRATION RULE

If historical Coalesce functionality corresponds to an existing Prodigal:

1. preserve the Prodigal's canonical identity;
2. create or resolve an application instance;
3. parameterize it;
4. bind it through typed relationships;
5. remove duplicate Coalesce substance only after compatibility verification.

---

# 27. QUIRK MIGRATION RULE

If historical behavior is properly represented by a Quirk:

1. preserve/create canonical Quirk identity according to authority;
2. use an instance in Coalesce;
3. preserve configuration separately;
4. preserve lineage;
5. avoid application-specific forks.

---

# 28. NATIVE MIGRATION RULE

Historical code mapping to a native primitive should be consolidated by semantics.

Example:

multiple historical filter-like pieces

may become:

`coalesce:substance:filter`

with different configurations.

Do not mechanically combine code merely because names appear similar.

Behavior must be compared first.

---

# 29. DATA COMPATIBILITY

The neutral application record representation should remain compatible where materially useful.

Historical evidence includes fields such as:

- id;
- date;
- title;
- preview;
- body;
- kind;
- status;
- category;
- provenance;
- relationships.

Migration may extend neutral representation.

It must not casually invalidate existing neutral datasets.

---

# 30. SOURCE-DOMAIN DATA

Migration must not preserve Mayorgate or another extracted application's domain data inside generic Coalesce implementation.

Source-specific data is not compatibility substance.

Generic behavior derived from source evidence may remain.

---

# 31. STATE COMPATIBILITY

Where useful, preserve runtime state semantics including:

- bookmarks;
- notes;
- selection;
- query history;
- saved views;
- panel state;
- workspace state.

State schema changes require deterministic migration or explicit invalidation.

Do not silently reinterpret stored state.

---

# 32. BROWSER COMPATIBILITY

The browser UI is a Coalesce projection.

Migration should preserve materially useful browser capabilities while separating them from canonical application semantics.

Browser implementation must not become the definition of Coalesce itself.

---

# 33. FILAMENT COMPATIBILITY

Where Filament remains the verified Coalesce projection path, preserve its integration during migration.

Do not require Filament internals to know the historical 81-piece architecture permanently.

Prefer a stable Coalesce projection contract.

---

# 34. API COMPATIBILITY

Existing Coalesce API consumers should receive either:

- compatible responses;
- a deterministic compatibility projection;
- an explicit version transition.

Do not silently change response semantics.

---

# 35. TRACE COMPATIBILITY

Historical trace entries identify executed pieces.

Future tracing should identify:

- canonical primitive;
- instance where applicable;
- source canonical identity;
- configuration identity or digest where useful;
- external provider where applicable;
- projection;
- authority effect.

Historical traces remain historical evidence.

---

# 36. AUTHORITY EFFECT

Coalesce migration must not grant new authority-changing powers to Coalesce.

Default authority effect remains:

`none`

unless an external authorized capability explicitly performs an authority-changing operation under its own contract.

---

# 37. DEPENDENCY DISCOVERY

Before migration implementation, inspect:

- imports;
- registry references;
- recipe references;
- tests;
- Filament integration;
- UI integration;
- API integration;
- external callers;
- graph references;
- canonical ownership records.

Filesystem proximity is not sufficient evidence of ownership.

---

# 38. DEPENDENTS

A historical piece must not be retired until known dependents have been:

- migrated;
- compatibility-routed;
- superseded;
- explicitly retired.

Unknown dependents are a migration risk and must be investigated proportionately.

---

# 39. BASELINE COMPARISON

Before migration, preserve a focused baseline for representative behavior.

At minimum use:

- one neutral dataset;
- one representative recipe;
- one representative query/filter operation;
- one representative presentation;
- one projection integration.

The migration must compare against this baseline.

---

# 40. REPRESENTATIVE RECIPE

`chronology-explorer` is a historical candidate for representative verification because it has already been used during Coalesce/Filament integration.

Its current implementation must be read before migration.

This document does not define its exact future component list.

---

# 41. MIGRATION EXECUTION ORDER

When authorized to begin:

1. read current implementation;
2. identify current verified baseline;
3. enumerate historical registry;
4. enumerate recipe usage;
5. identify dependencies and dependents;
6. identify stronger existing Savant equivalents;
7. write migration manifest;
8. validate complete disposition coverage;
9. implement new primitive registry alongside historical resolution;
10. implement compatibility resolver;
11. migrate one representative recipe;
12. run focused comparison;
13. migrate remaining recipes;
14. validate integration;
15. retire only proven superseded paths.

Do not delete first.

---

# 42. PARALLEL PERIOD

A temporary parallel period is permitted where required for safe migration.

During that period:

`historical identity`

may resolve through:

`compatibility mapping`

to:

`new canonical implementation`

This is preferable to maintaining two independent implementations.

---

# 43. SINGLE SUBSTANCE

Compatibility must project to the new canonical substance.

It must not create a second permanent implementation.

Target:

`old identity -> resolver -> new substance`

Reject:

`old identity -> old implementation`

plus:

`new identity -> unrelated new implementation`

unless temporary evidence proves parallel execution is required for comparison.

---

# 44. ROLLBACK

Rollback is warranted during registry migration because many recipes or integrations may depend on resolution semantics.

Before destructive retirement, preserve enough information to restore the previously verified registry and resolution behavior.

Do not create a broad backup system solely for Coalesce if existing Savant recovery mechanisms already provide this capability.

---

# 45. VALIDATION BUDGET

Default migration validation:

1. syntax/compilation;
2. migration-manifest completeness;
3. one representative semantic comparison;
4. one recipe compatibility check;
5. one projection/integration check.

Expand validation only when evidence shows broader shared-interface risk.

---

# 46. FAILURE CONDITION

Migration is not complete if any of these remain:

- unmapped historical pieces;
- unresolved recipe dependencies;
- embedded Exiles;
- duplicate canonical implementations;
- broken neutral-data compatibility without explicit authority;
- unexplained behavior loss;
- lost lineage;
- lost provenance;
- broken projection integration;
- ambiguous old/new identity resolution.

---

# 47. SUCCESS CONDITION

Migration is complete when:

- exactly 27 native primitives constitute Coalesce's canonical native grammar;
- every historical piece has a recorded disposition;
- useful historical behavior remains reachable;
- historical recipe compatibility is deterministic where retained;
- Prodigals and Quirks are instanced rather than duplicated;
- Exiles remain external;
- source-domain data is absent from generic Coalesce substance;
- known dependents remain functional or are explicitly migrated;
- representative semantic comparison passes;
- projection integration passes;
- the old implementation can be retired without losing required behavior.

---

# 48. FINAL MIGRATION INVARIANT

The migration must reduce architectural duplication without reducing semantic capability.

The old architecture is evidence.

The new architecture is canonical target.

The migration manifest is the bridge.

Compatibility preserves continuity.

Lineage preserves history.

Projection preserves interfaces.

Instances preserve reuse.

No behavior disappears merely because its old piece disappears.
