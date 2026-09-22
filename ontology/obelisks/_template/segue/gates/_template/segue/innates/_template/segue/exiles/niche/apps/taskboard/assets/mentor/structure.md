nano /root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/niche/apps/taskboard/assets/mentor/structure.md

# savant structure

**document revision:** 3.31.0\
**date:** 2026-09-17\
**document kind:** optimized structural constitution projection and
implementation map\
**runtime root:** `/root/savant-runtime`\
**predecessor:** `savant_structure_current_v3.30.0.md`\
**companion:** `savant_masterplan_v3.31.0.md`\
**source snapshot:** `sdump_savant-runtime_20260917t035631539647z.txt`\
**snapshot sha256:**
`691de6c79079c21a805392c156108ac8ddc9c4f95407d7d211cb86a3b78cfca4`\
**authority effect:** none

> this document is a human-readable structural projection. it does not
> create authority. accepted authority, accepted decisions,
> constitutional canon, and verified implementation retain their
> precedence. proposed optimizations are explicitly identified as
> structural requirements or derived design constraints rather than
> silently promoted to canon.

## 1. structural objective

savant should behave as a semantic organism rather than a pile of
applications.

the optimized structure is governed by one construction law:

`substantiate once → instance → compose → relate through typed segues → project → execute → record → replay`

the first five stages define semantic structure. execution and recording
must preserve the distinction between authoritative substance and
runtime consequence.

the structural target is maximum capability with minimum duplicated
semantic machinery.

## 2. irreducible structural layers

savant's structure is optimized around eight orthogonal layers. these
are conceptual responsibilities, not permission to create eight new
directories or registries.

### 2.1 substance

substance is canonical meaning that is substantiated once.

requirements:

-   stable identity.
-   canonical representation where deterministic identity is required.
-   explicit authority state.
-   provenance.
-   lineage.
-   version/evolution semantics where durable.
-   no runtime cache fields inside canonical identity unless authority
    explicitly requires them.

### 2.2 instance

an instance is a contextual use of substantiated meaning.

an instance may add placement, parameters, role, temporal context,
attachment, or local state without copying the underlying substance.

requirements:

-   reference the substance identity.
-   possess its own instance identity when addressability is required.
-   expose parent/container/composition context.
-   preserve provenance of parameters.
-   never mutate canonical substance merely to specialize one use.

### 2.3 composition

composition forms higher-order capability from instances.

requirements:

-   references rather than copied children.
-   deterministic member ordering where ordering is semantic.
-   explicit composition identity.
-   recursive composition permitted where ownership and cycle semantics
    are defined.
-   effective properties derived rather than manually synchronized.

### 2.4 segue

a segue is a typed, addressable semantic relationship.

segues are the connective tissue of savant.

a segue should expose, where applicable:

-   source identity.
-   target identity.
-   relationship type.
-   directionality.
-   cardinality.
-   authority/provenance.
-   temporal validity.
-   constraints.
-   dependency semantics.
-   inverse relationship or explicit absence.
-   lineage.
-   projection behavior.
-   runtime activation state when the relationship participates in
    execution.

a segue must not become a hidden service locator or generic dumping
ground for unrelated metadata.

### 2.5 shard / semantic partition

where current authority uses shard-like partitioning, the partition is a
bounded semantic slice, not a duplicate mini-database.

a shard-like partition should:

-   reference canonical substance.
-   expose partition criteria.
-   expose lineage to the source corpus.
-   support deterministic recomposition where possible.
-   avoid creating a second semantic owner.
-   remain independently addressable when scale or isolation requires
    it.

historical shard terminology must not override newer accepted
terminology such as `mote` where that supersession is authoritative.
this document therefore uses "shard / semantic partition" descriptively
rather than re-canonizing an obsolete name.

### 2.6 projection

a projection is derived information.

requirements:

-   explicit source identities.
-   deterministic derivation when deterministic output is claimed.
-   explicit projection schema/version.
-   content/digest identity where useful.
-   rebuildability or an explicit reason it cannot be rebuilt.
-   no independent semantic authority by default.
-   dependency/invalidation information.
-   freshness/staleness semantics where materialized.
-   no manual synchronization with its source.

### 2.7 runtime

runtime state is execution state, not automatically canon.

runtime changes should be classified as one of:

1.  ephemeral execution state.
2.  durable operational state.
3.  candidate semantic mutation.
4.  accepted durable semantic mutation.
5.  derived/materialized projection.

that classification prevents "the process changed it" from becoming
"savant believes it."

### 2.8 evidence / replay

execution, mutation, projection, migration, and recovery should emit the
minimum durable evidence needed to establish what occurred.

records should preserve:

-   actor/owner.
-   input identity.
-   operation identity.
-   output identity.
-   timestamp only where time is semantically or operationally relevant.
-   source/provenance.
-   result status.
-   failure information.
-   lineage to prior state.
-   replay information where replay is supported.

## 3. identity topology

the accepted exile set represented in the current audit is:

`carbon`, `cataxis`, `coda`, `envoy`, `filament`, `graffiti`, `lore`,
`mobius`, `modus`, `niche`, `notary`, `opus`, `pact`, `palaver`,
`shatter`, `underscore`, `urge`, `zero`.

identity should not be encoded solely by filesystem nesting. paths are
implementation addresses. semantic identity must survive relocation
where authority permits relocation.

optimized address model:

``` text
semantic identity
├── authority identity
├── type identity
├── substance identity
├── instance identity
├── composition identity
├── segue identity
├── projection identity
└── runtime/evidence identity
```

a physical path may project one or more of these identities, but the
path itself must not become semantic authority merely by existing.

## 4. ownership topology

ownership must be singular at the semantic level even when execution is
collaborative.

the core rule is:

`one semantic owner → many consumers / executors / projections`

examples already established:

``` text
carbon
├── straub
│   └── datrix
│       ├── dyad
│       ├── umbra
│       ├── membrane
│       └── isotope
├── oriel
└── guise

filament
└── deterministic projection execution

opus
└── ai/provider orchestration

palaver
└── dialogue / human interaction boundary

envoy
└── persona / voice / presentation identity

niche
└── task discovery / decomposition / planning / task context

coda
└── authorized durable mutation

notary
└── verification / evidence admission subject to its accepted purpose

kindred
└── admitted relationship semantics within its accepted boundary
```

where an accepted exile purpose remains unresolved, this document
preserves the uncertainty instead of inventing ownership.

## 5. structural separation of authority and execution

the optimized control flow is:

``` text
accepted authority
      │
      ▼
canonical substance
      │
      ├── instance
      │     └── composition
      │            └── typed segue
      │
      ├── deterministic projection ──► filament / other projection owner
      │
      └── requested operation
              │
              ▼
        niche task context
              │
              ▼
        opus orchestration
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
   envoy   palaver   domain owner
      │       │        │
      └───────┼────────┘
              ▼
       proposed mutation
              │
              ▼
            coda
              │
              ▼
       durable mutation
              │
              ▼
        notary/evidence
              │
              ▼
      replay / projections
```

this is a responsibility map, not a requirement that every request
traverse every exile.

## 6. datrix structural boundary

straub remains carbon-owned and manages datrixes.

``` text
datrix
├── canonical registry substance
├── instances
├── umbra metadata
├── membrane typed relationships
├── dyad projections
├── composition/groups
├── immutable history
├── query/dependency projections
├── function-step/execution records
└── isotope
    └── deterministic, non-authoritative projection
```

a datrix is not required merely because an entity exists.

the allocation/splitting/reference law remains unresolved. until
accepted authority settles it, structure must avoid both extremes:

-   one datrix for every object.
-   one universal datrix for all savant meaning.

the correct boundary must follow semantic authority, lifecycle,
composition, recovery, and query requirements rather than arbitrary file
or application boundaries.

## 7. projection topology

all projection-capable systems should converge on a common structural
contract without forcing one implementation.

recommended projection envelope:

``` text
projection
├── projection_id
├── projection_kind
├── schema_version
├── source_refs[]
├── source_digests[]
├── parameters
├── deterministic
├── generated_at
├── content_digest
├── dependency_refs[]
├── freshness
├── authority_effect = none
├── rebuildable
└── lineage
```

this envelope is a derived structural requirement, not accepted canon
until admitted.

filament should use the same principles for visual projection while
preserving its own semantic vector model.

## 8. runtime mutation topology

runtime changes must pass through an explicit mutation classification.

``` text
runtime event
├── read-only observation
├── ephemeral state change
├── projection refresh
├── proposed semantic mutation
└── durable operational mutation
```

only operations whose owner is authorized to mutate the target may cross
into durable semantic mutation.

where coda owns durable mutation, ui, opus, palaver, filament, niche,
and domain projections must not bypass coda merely because they can
write a file.

## 9. dependency and invalidation topology

dependencies should be explicit typed edges.

``` text
source A
├── consumed-by B
├── projected-as C
├── composed-into D
└── required-by E
```

when A changes, Savant should derive the invalidation frontier rather
than globally rebuilding or silently leaving stale projections.

optimized invalidation behavior:

1.  identify changed authoritative identity.
2.  traverse typed dependency segues.
3.  classify dependent as semantic, executable, materialized projection,
    cache, or evidence.
4.  invalidate only rebuildable derived state.
5.  require explicit mutation/migration for durable semantic dependents.
6.  record the operation when durability or recovery requires it.

## 10. lineage and provenance topology

lineage answers "what did this evolve from?"

provenance answers "where did this information come from?"

they must remain separate.

every production-grade semantic mutation should be able to expose:

``` text
current identity
├── authority source
├── provenance source(s)
├── predecessor identity
├── transformation / decision
├── actor / executor
└── resulting dependents
```

a projection should additionally expose the exact source
identities/digests from which it was derived.

## 11. temporal topology

time must be explicit when it affects meaning.

avoid hidden wall-clock semantics.

represent, where applicable:

-   valid_from / valid_to.
-   observed_at.
-   executed_at.
-   accepted_at.
-   projected_at.
-   effective_at.
-   historical query time.

these timestamps have different meanings and must not be collapsed into
one generic `timestamp`.

## 12. composition and emergence

higher-order Savant capability should emerge through composition.

preferred:

``` text
atomic substance
  → reusable instance
    → parameterized composition
      → typed segue network
        → higher-order capability
          → deterministic projection
```

reject:

``` text
feature request
  → new monolithic subsystem
    → duplicate registry
      → duplicate cache
        → manual synchronization
```

this is the primary structural compression mechanism.

## 13. interface boundary

every external interface should terminate in normalization:

``` text
external request
  → strict validation
  → normalization
  → savant-owned primitive / instance
  → accepted owner
  → execution
  → compatibility projection
```

external schemas remain interoperability contracts, not internal
authority.

## 14. concurrency structure

concurrency semantics belong to the owner of mutable state.

straub's verified local compare-and-swap checkpoint behavior is one
concrete implementation:

``` text
loaded digest
  → compare current durable digest
      ├── equal: save
      └── different: reject stale writer
```

this must not be blindly generalized to every exile.

each shared mutable owner must define the minimum appropriate semantics:
single writer, lock, optimistic concurrency, transaction, queue,
append-only log, or another accepted mechanism.

## 15. persistence structure

persistence must preserve authority and recovery.

baseline structural properties where durable state exists:

-   canonical serialization when content identity is required.
-   atomic replacement or transactional equivalent.
-   restrictive permissions appropriate to ownership.
-   no mutation of unrelated parent-directory policy.
-   backup/recovery only where justified.
-   explicit corruption handling.
-   reversible migration where representation changes.
-   durable evidence sufficient to prove recovery.

## 16. security structure

security is a boundary property rather than a bolt-on subsystem.

required structural constraints where relevant:

-   least privilege.
-   scoped capability.
-   secret isolation.
-   no secret serialization into projections.
-   strict path containment.
-   input size/resource bounds.
-   safe parsing/serialization.
-   injection resistance.
-   dependency admission.
-   explicit authentication/authorization boundaries for exposed
    services.
-   expiration/revocation where credentials or leases exist.

## 17. observability structure

observability should report state without becoming state authority.

recommended status vocabulary where applicable:

`configured → discovered → admitted → available → verified`

with orthogonal failure/degradation states:

`degraded`, `unavailable`, `failed`, `stale`, `unknown`.

a health endpoint must not claim "verified" merely because a module
imported successfully.

## 18. structure intelligence

the structure document itself should be projected from authoritative and
verified sources rather than manually becoming a second architecture.

the optimized structure-intelligence loop is:

``` text
authority + accepted decisions + verified implementation
        │
        ▼
normalized structural graph
        │
        ├── masterplan projection
        ├── structure projection
        ├── mentor human interface
        ├── dependency view
        ├── lineage view
        └── completion view
```

the human documents are therefore views over a structural graph, not
competing truth stores.

## 19. mentor interface

the masterplan and structure should be presented through a shared Niche
interface named **mentor**.

mentor is a projection/interaction surface, not a new exile and not a
new semantic authority.

responsibility composition:

``` text
mentor
├── niche
│   ├── task context
│   ├── masterplan projections
│   └── navigation / user workspace
├── opus
│   └── ai orchestration
├── palaver
│   └── conversation contract
├── envoy
│   └── persona/presentation when requested
├── filament
│   └── future deterministic visual projections
├── lore
│   └── knowledge retrieval only within accepted ownership
├── notary
│   └── evidence/verification semantics
└── coda
    └── any authorized durable mutation
```

mentor must never let an AI response directly rewrite accepted
authority.

## 20. mentor interaction model

the human interface should support:

1.  masterplan / structure dual-document switching.
2.  nested section tree.
3.  instant full-text search.
4.  section filtering.
5.  keyboard navigation.
6.  breadcrumb location.
7.  collapsible edifice.
8.  persistent reading position.
9.  deep links to headings.
10. outline minimap.
11. responsive mobile layout.
12. dark high-contrast Savant-native presentation.
13. status chips for completed/active/paused/blocked/unresolved.
14. authority/evidence badges.
15. code-block preservation.
16. table overflow handling.
17. cross-document related-section links.
18. "ask mentor" contextual AI conversation.
19. selected-section context injection into the mentor request.
20. document digest/version display.
21. no implicit mutation.
22. explicit projection-only labeling.
23. graceful AI unavailability.
24. same-origin Niche integration.
25. modular static assets rather than a monolithic inline page.
26. accessible focus/ARIA behavior.
27. print/export-friendly document rendering.
28. deterministic local document parsing/navigation independent of AI
    availability.

## 21. opus integration boundary

mentor should use Opus through Savant's existing interaction composition
rather than creating a second AI router.

the current verified Palaver `/api/chat` contract already accepts
`message` and returns `response` while preserving legacy `answer`.
Palaver composes conversation context and Opus inference.

therefore the correct mentor path is:

``` text
mentor ui
  → niche mentor endpoint
    → palaver.conversation.v1
      → existing palaver context
        → opus orchestration
          → provider
```

this preserves Palaver's dialogue ownership and Opus's orchestration
ownership.

the Niche mentor endpoint is a compatibility/proxy boundary. it must not
become another provider registry.

## 22. modular document model

masterplan and structure should share one document schema:

``` text
mentor_document
├── id
├── kind
├── revision
├── source_digest
├── authority_effect
├── sections[]
│   ├── id
│   ├── level
│   ├── title
│   ├── body
│   ├── status?
│   ├── authority?
│   ├── parent?
│   └── related[]
└── lineage
```

the markdown files remain portable human/machine-readable source
artifacts. the interactive interface deterministically projects them
into the shared schema at runtime.

## 23. physical/runtime layout

the idealized implementation layout, preserving current Niche ownership,
is:

``` text
/root/savant-runtime/
├── authority/
├── canon/
├── canon-system/
├── ontology/
│   └── .../exiles/
│       ├── carbon/
│       │   ├── straub/
│       │   ├── oriel/
│       │   └── guise/
│       ├── filament/
│       ├── opus/
│       ├── palaver/
│       ├── envoy/
│       ├── niche/
│       │   └── apps/taskboard/
│       │       ├── index.html
│       │       ├── app.js
│       │       ├── server.py
│       │       └── assets/
│       │           └── mentor/
│       │               ├── mentor.html
│       │               ├── mentor.css
│       │               ├── mentor.js
│       │               ├── masterplan.md
│       │               └── structure.md
│       └── ...
├── runtime/
├── vault/
└── assurance/
```

this does not require relocating existing authoritative content. it
describes the Mentor projection assets added to the current Niche
taskboard.

## 24. structural optimization register

the following substantive optimizations are justified:

1.  separate substance identity from path identity.
2.  make instances first-class contextual references.
3.  make composition reference-based.
4.  make segues typed/addressable.
5.  keep semantic partitions recomposable and non-authoritative unless
    explicitly owned.
6.  make projections explicitly non-authoritative by default.
7.  classify runtime changes before persistence.
8.  separate lineage from provenance.
9.  separate semantic time from wall-clock execution time.
10. expose dependencies/dependents.
11. derive invalidation frontiers.
12. make materialized projections rebuildable.
13. preserve single semantic ownership.
14. normalize external protocols at boundaries.
15. route durable mutation through its accepted owner.
16. define concurrency at each mutable owner.
17. make representation migrations reversible where needed.
18. distinguish configured/discovered/admitted/available/verified
    states.
19. keep observability non-authoritative.
20. use content digests where deterministic identity adds value.
21. preserve immutable history where destructive mutation would lose
    meaning.
22. make evidence/replay records explicit.
23. avoid generic "timestamp" semantics.
24. avoid generic untyped graph edges.
25. prevent UI state from becoming semantic state.
26. prevent AI output from becoming authority without admission.
27. share one modular document model for masterplan and structure.
28. project both documents through one Mentor interface.
29. compose Mentor through Niche + Palaver + Opus rather than creating a
    new orchestration stack.
30. preserve Filament as the visual projection owner for future
    graph/diagram rendering.
31. preserve Coda as durable mutation owner where applicable.
32. preserve Notary evidence boundaries.
33. preserve Envoy persona/presentation ownership.
34. preserve Palaver dialogue ownership.
35. preserve Niche task-context ownership.
36. keep the authoritative task graph distinct from the human masterplan
    projection.
37. make document lineage/digests visible to the user.
38. support deep links and deterministic nested navigation.
39. support mobile/keyboard/accessibility without a separate UI truth
    system.
40. reject dependencies for document rendering where a small
    deterministic local parser is sufficient.

## 25. unresolved structural questions

the following remain unresolved and must not be silently answered:

-   final Straub storage/database engine.
-   canonical datrix allocation/splitting/reference policy.
-   distributed consensus requirements, if any.
-   exact accepted primary-function wording for exile canon questions
    still open.
-   Atlas ownership/activation where current authority remains
    unresolved.
-   Scyon focal ownership where accepted authority has not settled it.
-   any future physical migration of semantic identity solely for
    aesthetic directory symmetry.

## 26. completion condition for structure

the Savant structure is not "complete" because every directory looks
tidy.

it is complete when:

-   every accepted semantic capability has one owner.
-   every authoritative primitive is substantiated once.
-   contextual uses are instances.
-   higher capability emerges through composition.
-   relationships are typed segues.
-   projections are deterministic/rebuildable where claimed.
-   runtime changes cannot silently become authority.
-   mutation ownership is enforced.
-   lineage/provenance survive evolution.
-   dependencies are visible.
-   persistence/recovery semantics are explicit where needed.
-   external interfaces normalize at boundaries.
-   AI orchestration cannot bypass authority.
-   human interfaces remain projections.
-   unresolved authority remains visibly unresolved.
-   the structure can evolve without requiring duplicated truth.

## 27. predecessor lineage

the complete v3.30.0 structure follows below as historical predecessor
evidence. where it conflicts with sections 1-26, the newer current user
directive and accepted authority govern. historical implementation
remains evidence, not authority.

------------------------------------------------------------------------

# savant structure

**document revision:** 3.30.0\
**date:** 2026-09-17\
**document kind:** current structural and continuation reference\
**runtime root:** `/root/savant-runtime`\
**authority effect:** none\
**predecessor:** `savant_structure_current_v3.29.0.md`\
**companion:** [savant masterplan](savant_masterplan_v3.30.0.md)

> this revision updates the controlling structural projection from the
> new sdump while preserving the complete v3.29.0 structure reference
> verbatim below. the sdump is implementation evidence, not semantic
> authority.

## 0a. v3.30 controlling structural delta

### 0a.1 current source projection

source: `sdump_savant-runtime_20260917t035631539647z.txt`\
generated: `2026-09-17T03:57:08Z`\
snapshot sha256:
`691de6c79079c21a805392c156108ac8ddc9c4f95407d7d211cb86a3b78cfca4`\
profile sha256:
`cb39c05dd572a02fcb6592655bd7819655b302e4fa77c281626dbfc211a7c842`\
projection only: `true`\
authority effect: `none`

the capture reports 5,444 included file records and 5,034 unique content
bodies with 0 dump failures. zero dump failures does not establish zero
runtime defects.

relative to the immediately preceding supplied sdump, this capture adds
18 paths, changes 3 paths, and removes 0 paths.

### 0a.2 controlling carbon → straub → datrix topology

the controlling conceptual topology is:

``` text
carbon
├── straub
│   └── creates / opens / operates datrix
│       ├── dyad
│       ├── umbra
│       ├── membrane
│       └── isotope
├── oriel
└── guise
```

constraints:

-   carbon owns straub.
-   straub is a module, not a datrix.
-   datrix is straub's product.
-   `dyad`, `umbra`, `membrane`, and `isotope` are the active datrix
    component names.
-   isotope is a deterministic projection and has no independent
    semantic authority.
-   oriel remains a carbon-owned sibling of straub, not a child of
    straub.
-   obsolete `radia` is not an active component or compatibility alias.

### 0a.3 current straub physical surface

the new capture adds/restores these straub runtime and command paths
relative to the preceding supplied sdump:

-   `commands/straub-datrix-self-test`
-   `commands/straub-enterprise-self-test`
-   `commands/straub-edifice-self-test`
-   `commands/straub-isotope-self-test`
-   `commands/straub-stale-writer-self-test`
-   `runtime/straub/__init__.py`
-   `runtime/straub/composition.py`
-   `runtime/straub/datrix.py`
-   `runtime/straub/module.py`
-   `runtime/straub/step.py`

and changes these existing straub paths:

-   `runtime/straub/persistence.py`
-   `runtime/straub/query.py`
-   `runtime/straub/resilience.py`

the current source therefore contains the previously missing datrix
integration/module/composition/step surfaces and focused command
self-tests. source presence establishes captured implementation, not
independent authority or fresh runtime success.

### 0a.4 datrix persistence and concurrency structure

current structural flow:

``` text
straub
  │
  ▼
straub datrix
  │
  ├── in-memory registry
  │     ├── canonical substance
  │     ├── instances
  │     ├── metadata
  │     ├── typed membrane relations
  │     ├── composition
  │     ├── history
  │     └── function-step / execution records
  │
  ├── deterministic query/dependency projections
  │
  ├── isotope projection
  │     └── rebuildable materialized isotope index
  │
  └── checkpoint
        │
        ├── expected loaded digest
        ├── local exclusive file lock
        ├── compare current durable digest
        │     ├── same → atomic save
        │     └── different → StraubConflictError
        ├── primary capsule
        └── backup capsule
```

the stale-writer branch rejects a conflict. it does not silently merge
semantic state.

### 0a.5 persistence permission structure

the current persistence boundary distinguishes a directory created by
straub's adapter from a directory that already exists:

``` text
target parent
├── already exists
│   └── preserve its existing mode
└── created by persistence adapter
    └── restrict to 0700

capsule file
└── restrict to 0600
```

this prevents the persistence adapter from changing a pre-existing
shared parent's permissions merely because it stores a capsule there.

### 0a.6 authority and projection separation

the structural rule remains:

``` text
accepted semantic authority
        │
        ▼
canonical substance / instances / typed relationships
        │
        ├── deterministic query projections
        ├── dependency/invalidation projections
        ├── isotope projections
        └── materialized indexes
```

derived representations remain rebuildable where their contract says so.
their presence does not promote them above their source.

### 0a.7 datrix allocation boundary remains unresolved

the current sources establish what straub and a datrix do, but they do
not establish a complete canonical allocation law saying that every
exile, application, character, file, task, location, or other entity
must receive a datrix.

until stronger authority establishes such a policy:

-   do not create one datrix per entity merely because the entity
    exists.
-   do not infer that every carbon application requires exactly one
    datrix.
-   preserve substance-once semantics and prefer
    instances/composition/reference when they are sufficient.
-   treat the exact split/reference/allocation policy as unresolved.

### 0a.8 filament boundary

filament remains the projection owner/execution boundary, distinct from
straub's datrix responsibility.

conceptually:

``` text
straub / other semantic owners
        │
        │ authoritative or accepted structured inputs
        ▼
filament
        │ deterministic visual projection
        ▼
vector scene / renderer target
```

filament must not become a second semantic authority merely because it
constructs visual geometry.

the separately supplied current filament vector runtime contains the
newer semantic scene model and deterministic geometry kernel. historical
compiler/svg patch material is subordinate historical implementation and
must not replace newer current APIs.

### 0a.9 current unresolved structural register

  ---------------------------------------------------------------------
  concern                            current state
  ---------------------------------- ----------------------------------
  final straub database/storage      unresolved
  engine                             

  distributed straub consensus       not established

  automatic stale-state merge        not established and not implied

  datrix allocation/splitting law    unresolved

  opus/cameo integration             paused

  niche executable queue             paused

  filament current-compatible        next non-paused implementation
  compiler/projection layer          boundary

  atlas                              unresolved and paused

  global completion denominator      unknown
  ---------------------------------------------------------------------

### 0a.10 continuation boundary

the bounded straub restoration/hardening structure is complete within
the established live verification scope. further straub changes require
a new defect, new requirement, or stronger authority.

the next non-paused structural implementation boundary is filament's
current-compatible vector compiler/projection layer. preserve current
semantic model and geometry APIs and add only the minimum missing
projection machinery.

## 0b. verbatim predecessor

the complete v3.29.0 structure reference follows unchanged. statements
inside it that conflict with section 0a are historical and superseded
within this revision.

# savant structure current

**document revision:** 3.29.0\
**date:** 2026-09-15\
**document kind:** expanded semantic and implementation reference\
**root:** `/root/savant-runtime`\
**authority effect:** none\
**runtime release implied:** none\
**predecessor:** `SAVANT_STRUCTURE_CURRENT_v3.28.0.md`\
**companion:** [savant masterplan](savant_masterplan_v3.29.0.md)

> this document separates accepted architectural direction, source
> captured in the supplied dump, historical behavioral reports, and
> unimplemented requirements. its diagrams and tables describe the cited
> evidence and governing constraints; they are not an authoritative
> graph export or a claim of a fully operational runtime.

## navigation

1.  [reading contract and evidence](#1-reading-contract-and-evidence)
2.  [identity and semantic grammar](#2-identity-and-semantic-grammar)
3.  [ownership topology](#3-ownership-topology)
4.  [authority, evidence, mutation, and
    recovery](#4-authority-evidence-mutation-and-recovery)
5.  [straub and datrix architecture](#5-straub-and-datrix-architecture)
6.  [straub physical state and
    interfaces](#6-straub-physical-state-and-interfaces)
7.  [deterministic projection and temporal
    contracts](#7-deterministic-projection-and-temporal-contracts)
8.  [persistence, resilience, and
    concurrency](#8-persistence-resilience-and-concurrency)
9.  [palaver, envoy, opus, and cameo](#9-palaver-envoy-opus-and-cameo)
10. [modus and reusable application
    composition](#10-modus-and-reusable-application-composition)
11. [carbon applications and domain
    boundaries](#11-carbon-applications-and-domain-boundaries)
12. [niche, atlas, kindred, and
    governance](#12-niche-atlas-kindred-and-governance)
13. [physical placement and
    compatibility](#13-physical-placement-and-compatibility)
14. [security, scale, and
    interoperability](#14-security-scale-and-interoperability)
15. [structural conflicts and
    continuation](#15-structural-conflicts-and-continuation)
16. [verbatim predecessor](#16-verbatim-predecessor)

## 1. reading contract and evidence

### 1.1 how to use this reference

read sections 2--5 for meaning and ownership, section 6 for captured
straub source state, and section 15 for unresolved boundaries. use the
masterplan for task sequencing and completion conditions. read the
preserved predecessor only for lineage or detail explicitly needed by
the task.

a semantic parent is not automatically a filesystem parent. a class
export is not an accepted owner. a captured module is not a passing
subsystem. a historical test is not proof after subsequent deletion.

### 1.2 provenance

  -----------------------------------------------------------------------------------------
  reference        source                                                  role
  ---------------- ------------------------------------------------------- ----------------
  s1               current user directive                                  task scope and
                                                                           maximum
                                                                           justified
                                                                           evolution
                                                                           requirements

  s2               `savant_migration_handoff_pre_midjourney_20260915.md`   later semantic
                                                                           corrections and
                                                                           reported
                                                                           migration state

  s3               `CHATGPT_MASTERPLAN_v3.28.0.md`                         prior planning
                                                                           and conflict
                                                                           evidence

  s4               `SAVANT_STRUCTURE_CURRENT_v3.28.0.md`                   predecessor
                                                                           structure,
                                                                           preserved in
                                                                           section 16

  s5               `sdump_savant-runtime_20260915t222611514125z.txt`       latest supplied
                                                                           captured
                                                                           implementation
  -----------------------------------------------------------------------------------------

the masterplan §2 contains the shared source ledger and capture counts;
§15 preserves all of s2 verbatim. this structure document references
that copy instead of maintaining a second editable handoff.

s5 was generated `2026-09-15T22:26:48Z`, targets `/root/savant-runtime`,
and reports snapshot sha256
`028a18a1723cb21ed752ed817ad40d81f724eafc647e93aa2f53a27762ac872e`. it
is projection-only with authority effect none. it reports 5,425 included
records, 5,015 unique contents, 1,351 skipped records, 74 redactions,
and zero capture failures. these are manifest claims, not runtime
validation.

### 1.3 evidence interpretation

-   **accepted/directive-supported structure:** architectural
    requirement with its cited origin.
-   **captured source:** code or record actually present in s5; runtime
    success not implied.
-   **reported proof:** prior execution described by s2 or a
    predecessor; not rerun here.
-   **convention-acknowledged:** the user's unqualified continuation
    acknowledged the previous slice according to the standing protocol.
-   **historical:** retained evidence of an earlier state.
-   **required restoration:** known missing contract or previously
    deleted source, not freshly implemented here.
-   **proposal:** engineering option, not accepted authority.
-   **unknown:** insufficient evidence; do not replace with a guess.

editorial section numbers, table keys, and document version numbers do
not create graph identities or niche tasks.

## 2. identity and semantic grammar

### 2.1 accepted recursive identity edifice

  depth from outermost   identity tier   interpretation
  ---------------------- --------------- -------------------------------------------------
  1                      obelisk         outer tier of the accepted recursive edifice
  2                      gate            tier under obelisk
  3                      innate          tier under gate
  4                      exile           semantic owner tier
  5                      prodigal        tier under exile
  6                      quirk           tier under prodigal
  7                      facet           tier under quirk
  8                      nuance          tier under facet
  9                      trait           innermost named tier in this accepted edifice

this table preserves order; it does not invent universal cardinalities,
automatic containment rules, or a complete instance catalog. the
historical two-to-four composition guidance for prodigals/quirks remains
source-specific guidance, not permission to manufacture filler
components.

earlier edifice formulations using iota, mote, and portal remain in
historical source only where superseded by s2 and the v3.28 controlling
sections. do not infer that those terms have been physically removed
everywhere.

### 2.2 universal instance pattern

**substantiate once → instance → compose → relate through typed segues →
project**

every savant object follows the instance-oriented architectural
direction. substance is reusable semantic content under its legitimate
owner. an instance refers to substance and carries only legitimate
contextual variation. compositions refer to instances rather than
copying their lower-level content. projections derive views without
acquiring source authority.

semantic identity is distinct from labels, source bytes, content hashes,
filenames, and interface names. a hash can identify a representation
without proving authority or semantic equivalence.

### 2.3 structural vocabulary

  -----------------------------------------------------------------------
  term                    supported meaning       boundary
  ----------------------- ----------------------- -----------------------
  rubric                  program-bearing         owned by the relevant
                          semantic surface        semantic/program owner

  cabal                   shared substance at the no generic
                          narrowest proven common dumping-ground
                          scope                   ownership

  kindred                 direct relationships,   not every graph-shaped
                          role/policy semantics,  concern
                          deterministic           
                          relationship algebra    

  segue                   typed transition,       explicit meaning; no
                          relationship, lineage,  hidden owner transfer
                          or connection between   
                          instances               

  mood                    modus-owned methods of  not persona, theme,
                          modularization,         provider settings, or
                          including behavior      arbitrary global state
                          transformation          

  mask                    typed legitimate        not duplicated
                          variation of shared     substance or
                          substance               independent authority

  slot                    capability attachment   distinct from mood
                          surface                 

  attachment              parameterized           maintains owner,
                          reference-first         compatibility, lineage
                          extension               

  projection              derived deterministic   materialization does
                          representation where    not make it
                          the contract requires   authoritative
                          determinism             

  isotope                 straub/datrix           not a worker,
                          deterministic           derivation owner, or
                          projection primitive    mutation authority
  -----------------------------------------------------------------------

### 2.4 independent structural axes

  -----------------------------------------------------------------------
  axis                    question it answers     common error to avoid
  ----------------------- ----------------------- -----------------------
  identity                which semantic entity   deriving identity
                          is this?                solely from current
                                                  filename

  containment             where is it             treating folder nesting
                          conceptually placed?    as authority

  composition             which instances build   duplicating their
                          this structure?         substance

  relationship            how are these instances treating all
                          connected?              relationships as
                                                  containment

  authority               who may establish or    treating evidence
                          change meaning?         storage as acceptance

  transformation          which legitimate        silently changing
                          variation or derivation identity
                          applies?                

  runtime state           what is happening in    persistent runtime
                          this execution?         state becoming canon

  persistence             how is a representation storage adapter owning
                          retained?               semantics

  projection              what view is derived    manual synchronization
                          from stronger inputs?   or self-promotion
  -----------------------------------------------------------------------

### 2.5 required element properties

where relevant, an element needs stable identity, addressability, owner
reference, reusable substance reference, legitimate variation,
composition links, typed segues, provenance, lineage, dependencies,
dependents, lifecycle, and compatibility semantics.

this is a contract checklist. it does not prescribe a new universal json
envelope, require every field on every object, or claim that all
existing modules already implement those properties.

## 3. ownership topology

### 3.1 primary semantic owners

  -----------------------------------------------------------------------
  concern                 owner                   consumer relationship
  ----------------------- ----------------------- -----------------------
  tasks and masterplan    niche                   application surfaces
  projection                                      consume task
                                                  projections

  provider/model routing  opus                    palaver/cameo request
  and inference                                   execution through the
                                                  owning boundary

  conversation and        palaver                 coordinates context,
  workstation                                     persona, tasks, review,
                                                  and execution

  persona, voice,         envoy                   presents orobouros and
  expression                                      other legitimate
                                                  persona substance

  verification and        notary                  evaluates claims
  evidence admission                              without generation
                                                  self-admission

  authorized durable      coda                    applies authorized
  mutation                                        changes and preserves
                                                  mutation history

  contracts and           pact                    supplies constraints
  permissions                                     without absorbing other
                                                  owners

  composition and mood    modus                   applications reuse
                                                  compositions

  simulation; straub      carbon                  simulation and datrix
  module                                          responsibilities retain
                                                  their distinct
                                                  semantics

  projection              filament                executes projections
  workers/execution                               without owning source
                                                  truth

  canonical               lore / fluid canon      context systems
  knowledge-memory                                reference accepted
                                                  substance

  refinement              urge                    candidates remain
                                                  candidates until
                                                  authorized acceptance

  fault isolation         shatter                 decomposes within
                                                  permitted boundaries

  structural              underscore              supports without hidden
  normalization                                   mutation authority

  custody, replay,        vault                   preserves authoritative
  retention, recovery                             substance and evidence
                                                  without promoting it
  -----------------------------------------------------------------------

the historical "fixed 18" list and later six-exile promotion list
overlap and contain superseded oriel placement. this revision does not
invent a reconciled total or assign new purposes to covenant, endgame,
praxis, graffiti, occam, tempo, or mobius merely from their names.
retain accepted purposes when supplied by their authoritative records.

### 3.2 reusable living substrates

  -----------------------------------------------------------------------
  substrate               retained responsibility explicit non-ownership
  ----------------------- ----------------------- -----------------------
  scyon                   living structural       proposal tools do not
                          implementation          settle focal owner

  splyce                  living                  not a new identity tier
                          interface/interaction   

  scrybe                  recall/context          not second canon
                          projection              

  pryme                   authority               cannot create
                          interpretation and      acceptance
                          supersession            

  cypher                  translation,            external schema does
                          normalization,          not gain internal
                          serialization           authority

  thryce                  assurance mechanics     not evidence admission
                                                  owner

  spyral                  evolution/migration     not mutation authorizer
                          compatibility           

  lythe                   deterministic           not source authority
                          derivation              

  dryve                   delegated execution     not delegating semantic
                          lifecycle               owner
  -----------------------------------------------------------------------

these nine remain mechanisms, not exiles or edifice levels.

### 3.3 typed owner-to-owner contracts

meaningful cross-owner interactions should expose source and target
identity, relationship type, direction, permitted effects, provenance,
lineage, version/compatibility behavior, dependencies, failure
semantics, and lifecycle where applicable.

this requirement is fulfilled by existing primitives when adequate. do
not create a new contract registry merely to repeat established records.
a function call alone does not transfer ownership. a receipt records an
event; it does not authorize the next effect by itself.

## 4. authority, evidence, mutation, and recovery

### 4.1 authority precedence

current user directive; accepted graph; accepted decisions;
constitutional canon; verified implementation; admitted evidence;
deterministic projection; historical implementation; historical
documents; inference; speculation.

immutable accepted decisions are superseded by new authorized records,
never silently edited. unresolved equal-authority conflicts remain
explicit. a document's repeated assertion does not strengthen its
authority.

### 4.2 lifecycle boundaries

  -----------------------------------------------------------------------
  activity               legitimate boundary    output classification
  ---------------------- ---------------------- -------------------------
  generate or refine     owning generator /     candidate
  candidate              urge / opus as         
                         applicable             

  interpret applicable   pryme                  interpretation tied to
  authority                                     cited authority

  assess constraints and pact and relevant      constraint/permission
  permission             owner                  result

  validate mechanics     thryce / focused       validation evidence
                         assurance              

  verify or admit        notary                 attestation/admitted
  evidence                                      evidence according to
                                                contract

  apply authorized       coda                   mutation result and
  durable change                                history

  retain and recover     vault                  custody/replay/recovery
                                                representation

  derive                 lythe within owner     derived result
                         contract               

  execute projection     filament within owner  projection output
                         contract               
  -----------------------------------------------------------------------

these boundaries describe responsibilities, not a newly mandated fixed
ordering of all calls. actual workflows must preserve their existing
contracts and appropriate preconditions.

### 4.3 provenance and lineage

provenance answers where substance originated, how it entered, its
authority/evidence class, referenced inputs, transformation
identity/version, and output classification. lineage answers what
evolved from what, through which instance, composition, migration, or
supersession.

retain source record identity even when the view changes. an exported
document should point to evidence rather than become the evidence's
replacement. replay should recover supported historical state, not
reinterpret old records through an undocumented new policy.

### 4.4 recovery

recovery uses preserved substance, history, and legitimate custody
contracts to reconstruct state and rebuild derived projections. a cache
can be discarded only if its source and rebuild semantics survive. do
not conflate immutable mutation history with arbitrary application logs
or backups.

a successful read from a backup is not permission to promote backup
contents to new semantic authority. corruption or ambiguity must
preserve available evidence and report the failure rather than silently
invent a repaired canon.

## 5. straub and datrix architecture

### 5.1 corrected conceptual placement

  ------------------------------------------------------------------------
  parent            child / product   relationship      status
  ----------------- ----------------- ----------------- ------------------
  carbon            straub            owns module       explicit user
                                                        correction
                                                        recorded in s2

  carbon            oriel             owns sibling      explicit user
                                      module            correction
                                                        recorded in s2

  carbon            guise             owns simulation   retained
                                      system            structure/source
                                                        evidence

  straub            datrix            creates and       explicit user
                                      operates product  correction

  datrix            dyad              component         recorded
                                                        conceptual
                                                        contract

  datrix            umbra             component         recorded
                                                        conceptual
                                                        contract

  datrix            membrane          component         recorded
                                                        conceptual
                                                        contract

  datrix            isotope           deterministic     explicit isotope
                                      projection        correction
                                      component         
  ------------------------------------------------------------------------

straub is not a datrix. oriel is not inside straub. a datrix's intended
greater capability than a conventional database is a product aspiration,
not proven general superiority.

the obsolete `radia` term is removed from active straub semantics, not
retained as a compatibility alias. its appearance in historical
quotations and these removal instructions preserves evidence rather than
reintroducing it as a component.

### 5.2 known component meanings

  -----------------------------------------------------------------------
  component / surface   supported description       source boundary
  --------------------- --------------------------- ---------------------
  dyad                  derived pairing             s2's implementation
                        representation              history; captured
                                                    `dyad` function

  umbra                 metadata definitions and    s2 history; captured
                        values in the recorded      `umbra_definition` /
                        implementation              `umbra_value`
                                                    functions

  membrane              typed relation              s2 history; captured
                        representation              `membrane` function

  isotope               deterministic projection    explicit user
                                                    authority; captured
                                                    implementation

  registry              substance-once              captured source
                        registration, instances,    surface; incomplete
                        metadata and capsule        dependencies remain
                        interfaces                  

  capsule               export/replay/persistence   captured schemas and
                        representation              s2 history

  history               event/replay evidence       does not compete with
                        representation              coda mutation history
                                                    ownership

  materialized isotope  rebuildable derived lookup  captured source
  index                 representation              

  function-step records reusable                    does not execute
                        step/function/execution     delegated action
                        trace semantics             itself
  -----------------------------------------------------------------------

do not invent richer isotope semantics, unprovided component ontologies,
storage-engine guarantees, or extra identity tiers.

### 5.3 boundaries around straub

  -----------------------------------------------------------------------
  external owner         retained authority     straub's permitted
                                                contribution
  ---------------------- ---------------------- -------------------------
  coda                   authorized durable     evidence/replay
                         mutation and mutation  representations and
                         history mechanics      approved persistence
                                                mechanics

  vault                  custody, retention,    compatible recovery
                         replay, recovery       representation and
                                                persistence adapters

  pryme                  authority              store/filter exact
                         interpretation         metadata without deciding
                                                precedence

  lythe                  derivation             dependency/invalidation
                                                representations

  filament               projection             isotope representation
                         execution/workers      and local cache machinery

  dryve                  delegated action       function-step identity
                         lifecycle              and replay records

  carbon                 module ownership       straub remains
                                                carbon-owned despite
                                                physical root placement
  -----------------------------------------------------------------------

no persistence adapter becomes semantic authority. no viscera-specific
assumption belongs in generic straub. the presence of file-backed
persistence does not settle a database-engine choice.

## 6. straub physical state and interfaces

### 6.1 captured runtime files

all paths below are absolute runtime paths represented in s5, not paths
created or modified by this documentation task.

  ---------------------------------------------------------------------------------------------------------------------
  path                                                            captured named surface              interpretation
  --------------------------------------------------------------- ----------------------------------- -----------------
  `/root/savant-runtime/runtime/straub/model.py`                  `StraubError`,                      primitive/model
                                                                  `StraubValidationError`,            support
                                                                  `StraubConflictError`;              
                                                                  normalization and component         
                                                                  constructors                        

  `/root/savant-runtime/runtime/straub/registry.py`               `StraubRegistry`; schema            isotope-native
                                                                  `savant.straub.registry.v3`         source captured;
                                                                                                      prior migration
                                                                                                      proof reported

  `/root/savant-runtime/runtime/straub/dependency.py`             `StraubDependencyIndex`             dependency,
                                                                                                      invalidation,
                                                                                                      lookup surface

  `/root/savant-runtime/runtime/straub/isotope.py`                `isotope`, `validate_isotope`;      deterministic
                                                                  schema                              projection
                                                                  `savant.carbon.straub.isotope.v1`   primitive

  `/root/savant-runtime/runtime/straub/history.py`                `build_event`, `validate_history`   history
                                                                                                      representation

  `/root/savant-runtime/runtime/straub/persistence.py`            `StraubPersistencePort`,            persistence port
                                                                  `MemoryPersistence`,                and adapters
                                                                  `AtomicCapsulePersistence`          

  `/root/savant-runtime/runtime/straub/migration.py`              keyed-representation                reversible
                                                                  conversion/validation, receipt,     representation
                                                                  migration verification              mechanics

  `/root/savant-runtime/runtime/straub/representation_store.py`   `AtomicRepresentationStore`         stored keyed
                                                                                                      representation

  `/root/savant-runtime/runtime/straub/resilience.py`             `ResilientCapsulePersistence`       local locks,
                                                                                                      primary/backup
                                                                                                      mechanics

  `/root/savant-runtime/runtime/straub/function_registry.py`      `StraubFunctionRegistry`            step/function
                                                                                                      definitions and
                                                                                                      recorded
                                                                                                      execution traces

  `/root/savant-runtime/runtime/straub/materialized.py`           `StraubIsotopeIndex`,               restored
                                                                  `AtomicIsotopeCache`,               isotope-native
                                                                  `validate_materialized`             materialization

  `/root/savant-runtime/runtime/straub/projection_refresh.py`     `ContentionSafeIsotope`, private    captured advance
                                                                  `_ProjectionLock`                   beyond the
                                                                                                      handoff
  ---------------------------------------------------------------------------------------------------------------------

twelve captured files do not form proof of a complete importable
package. some refer to the missing restoration surfaces below.

### 6.2 remaining source gaps

  ---------------------------------------------------------------------------------------------------
  required path                                          handoff state   latest      necessary
                                                                         capture     retained
                                                                         state       contract
  ------------------------------------------------------ --------------- ----------- ----------------
  `/root/savant-runtime/runtime/straub/query.py`         intentionally   no file     deterministic
                                                         deleted, not    record      query; explicit
                                                         restored                    time

  `/root/savant-runtime/runtime/straub/composition.py`   intentionally   no file     types, groups,
                                                         deleted, not    record      composition,
                                                         restored                    effective
                                                                                     definitions

  `/root/savant-runtime/runtime/straub/step.py`          intentionally   no file     function steps,
                                                         deleted, not    record      execution
                                                         restored                    records,
                                                                                     trace/replay

  `/root/savant-runtime/runtime/straub/datrix.py`        intentionally   no file     `StraubDatrix`
                                                         deleted, not    record      integration
                                                         restored                    

  `/root/savant-runtime/runtime/straub/module.py`        intentionally   no file     `Straub`
                                                         deleted, not    record      create/open
                                                         restored                    surface

  `/root/savant-runtime/runtime/straub/__init__.py`      intentionally   no file     exact exports
                                                         deleted, not    record      and unaffected
                                                         restored                    public surface
  ---------------------------------------------------------------------------------------------------

the explicit deletion history supports this restoration status. a
filtered dump alone cannot prove the present state of a remote
filesystem. no current remote server inspection occurred here.

### 6.3 refresh source correction

s2 said refresh restoration was next. s5 now contains:

-   schema `savant.straub.projection-refresh.v1`.
-   imports of `AtomicIsotopeCache`, `StraubIsotopeIndex`, and
    `StraubValidationError`.
-   `ContentionSafeIsotope.load(capsule_digest=...)`,
    `refresh(capsule)`, and `status(capsule_digest=...)` surfaces; the
    ellipses in this prose denote signature arguments, not a supplied
    implementation.
-   local shared read and exclusive refresh locks through `fcntl.flock`.
-   reuse of a fresh cache for the supplied capsule digest.
-   rebuild, save, reload, freshness verification, and digest
    comparison.
-   explicit `projection_only=True`, `semantic_mutation=False`, and
    authority effect none in refresh results.

the current source class names match those captured in materialized
source. that is source-level compatibility evidence, not a performed
import or integration test.

the schema's `owner = "savant"` module field does not supersede carbon's
accepted semantic ownership. preserve external/class syntax when
documenting it; do not perform aesthetic renaming.

### 6.4 content references for continuation

  ----------------------------------------------------------------------------------------------
  captured file             source/rendered sha256 reported by s5
  ------------------------- --------------------------------------------------------------------
  `materialized.py`         `09d9814ab68cb9766ababde07858afbbcd0056a9e2033199ff471bdb7c78a03b`

  `projection_refresh.py`   `1ad30d0b3ded4b291f1fe4e53c9fb5be90b2d7c2512fe1a1f53190d85df027ea`

  `registry.py`             `be338aba0f4c3f6b4c8916074f9111fd241cc1ade152c0b4e3be61a6248382dd`

  `dependency.py`           `665f5a3d151c2da195b1dea41f4c799625173deff54b27a85fbb2fc0c49e2aa9`
  ----------------------------------------------------------------------------------------------

these identify captured bodies for accurate retrieval. they are not new
semantic ids or a claim that current remote files still have these
hashes.

### 6.5 restored integration contract

the handoff requires `Straub.create_datrix(...)` and
`Straub.open_datrix(...)`, with exile `carbon`, module name `straub`,
product `datrix`, and `straub_is_datrix=false`. `StraubDatrix` remains
the product class. these are required compatibility surfaces, not
currently captured restored classes.

exports must use the exact classes/functions present when restoration
completes. preserve unaffected exports, avoid invented aliases, and keep
the removed terminology out of active schemas, methods, health fields,
suffixes, comments, and focused commands.

### 6.6 command state

s5 records:

  ----------------------------------------------------------------------------------------
  path                                                           current evidence
  -------------------------------------------------------------- -------------------------
  `/root/savant-runtime/commands/straub`                         captured presence;
                                                                 runnable state not proven

  `/root/savant-runtime/commands/straub-migration-self-test`     captured presence

  `/root/savant-runtime/commands/straub-persistence-self-test`   captured presence
  ----------------------------------------------------------------------------------------

s2 records the datrix, enterprise, edifice, and isotope focused
self-tests as deleted and awaiting restoration. the obsolete
removed-term self-test must remain absent. restore legitimate command
contracts after runtime dependencies are coherent.

## 7. deterministic projection and temporal contracts

### 7.1 input and output separation

a deterministic projection should identify referenced inputs, input
version/digest, projection version, normalization, stable ordering,
serialization when bytes matter, digest semantics when identity matters,
and failure behavior. a presentation timestamp or operational lock must
not silently affect semantic identity.

do not assume every function in the runtime is deterministic merely
because the architecture requires deterministic projections. for
example, model source contains a `utc_now` helper; its existence alone
does not prove query or isotope behavior uses an implicit clock.

### 7.2 isotope versus source

canonical datrix substance supplies projection inputs; an isotope is a
derived representation. materializing an isotope does not make it source
truth. authority metadata may be carried exactly, but carrying it does
not interpret or promote it.

dependency and invalidation views should reference existing identity
rather than create parallel authoritative graphs. reverse dependents can
be projected rather than maintained as an independent truth set where
existing contracts permit that.

### 7.3 freshness

  -----------------------------------------------------------------------
  condition               valid interpretation    invalid interpretation
  ----------------------- ----------------------- -----------------------
  cache matches requested usable according to the source is authoritative
  source digest           cache contract          because a cache exists

  cache stale             rebuild required        mutate canonical
                                                  substance to match
                                                  cache

  cache missing           recompute where         source is absent
                          supported               

  cache corrupt           reject/rebuild with     silently trust partial
                          preserved source        bytes

  lock acquired           local operation         stale source cannot
                          coordinated             overwrite newer state

  repeated digest matches byte/representation     universal correctness
                          determinism under       or authority
                          tested inputs           
  -----------------------------------------------------------------------

### 7.4 time

the query v2 contract recorded by s2 is explicit: omitted `at` means no
implicit temporal filter and remains null. supplied time selects the
temporal interpretation. metadata validity and query time must not
acquire an implicit wall clock merely to simplify implementation.

preserve deterministic temporal boundaries from the exact prior source
when restoring query. do not invent timezone, interval inclusivity, or
missing-time semantics beyond the established contract.

### 7.5 dependency and replay

replay references preserved inputs and history with known version
semantics. invalidation reports affected derived results rather than
rewriting authority. deterministic reproduction requires compatible code
and serialization rules as well as the same nominal input values.

do not hardcode an example's digest into a general test. reported
historical digests belong to their exact fixtures and versions.

## 8. persistence, resilience, and concurrency

### 8.1 representation responsibilities

  -----------------------------------------------------------------------
  surface                 permitted purpose       retained limit
  ----------------------- ----------------------- -----------------------
  memory persistence      reference/test          not durable by
                          representation          implication

  atomic capsule          durable representation  not semantic authority
  persistence             with atomic replacement 
                          and synchronization     

  resilient capsule       primary/backup recovery not distributed
  persistence             and local lock          consensus
                          coordination            

  representation store    preserve reversible     no semantic mutation by
                          keyed representation    conversion

  materialized isotope    accelerate derived      rebuildable,
  cache                   access                  non-authoritative

  lock file               operational             excluded from semantic
                          coordination            identity
  -----------------------------------------------------------------------

the handoff reports prior atomic replace, file/directory fsync, and mode
`0600` proof. this revision does not rerun those checks after
deletion/restoration.

### 8.2 failure behavior

where covered by the existing contract, malformed capsules should fail
validation, interrupted writes should not silently destroy the last
usable representation, and damaged primary state should support bounded
backup recovery. recovery must preserve provenance and distinguish
repaired representation from accepted semantic change.

do not imply that all filesystem crash, network filesystem, hardware, or
multi-host failures are covered by a local-host test.

### 8.3 stale-writer gap

separate processes can load the same capsule, acquire a save lock at
different times, and sequentially write stale state unless the save
contract compares expected current state. exclusive writes prevent
simultaneous writes; they do not automatically solve stale updates.

the handoff's future proposal is
`save_capsule_if_current(capsule, expected_digest)`, with loaded digest
retained and stale checkpoint rejected. this method is a proposal, not
an existing captured export. do not automatically merge divergent states
or call the mechanism distributed.

### 8.4 permission caveat

atomic adapters are reported to chmod a parent directory to `0700`. this
may be inappropriate for an existing caller-selected shared directory.
prior focused tests used fresh temporary directories. before production
path binding, preserve unrelated directory permissions through dedicated
ownership or a justified implementation correction.

restrictive file permissions and path normalization serve distinct
purposes. neither by itself proves safe handling of every symlink,
traversal, or concurrent path replacement.

### 8.5 storage-engine boundary

no specific database or storage engine becomes authoritative through
this reference. the existing file adapters are implementation resources.
a future engine must preserve semantic identity, replay, owner
boundaries, and migration properties; performance convenience does not
authorize schema ownership transfer.

## 9. palaver, envoy, opus, and cameo

### 9.1 execution relationships

  -----------------------------------------------------------------------
  surface                 request/response role   evidence state
  ----------------------- ----------------------- -----------------------
  frontend `:5173`        same-origin `/api`      prior repair/live
                          client                  success reported

  palaver `:8787`         conversation and        prior readiness and
                          workstation             browser proof reported
                          orchestration           

  envoy / orobouros       persona and             reported
                          cognitive/voice         default-persona
                          expression              restoration

  opus                    model/provider routing  source captured; live
                          and execution           status task-dependent

  configured provider     external inference      availability not
  pool                    boundary                inferred from
                                                  historical probes

  scrybe                  context projection      owns recall projection,
                                                  not canon

  niche / coda / notary   task, mutation,         ownership remains
                          evidence boundaries     independent of palaver
                                                  calls
  -----------------------------------------------------------------------

the historical transport fix used `const API = ""` in `App.jsx`. this is
compatibility evidence, not a request to edit a frontend in this turn.
credentials must not be copied into persona, conversation, or
documentation.

### 9.2 newer opus capture

the common captured opus runtime root is:

`/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus/runtime`

  ---------------------------------------------------------------------------------------
  file relative to that root    captured source fact                   what remains
                                                                       unproven here
  ----------------------------- -------------------------------------- ------------------
  `model_discovery.py`          schema                                 complete
                                `savant.opus.model-discovery.v3`;      ranking/provider
                                dotted-version and date parsing        correctness
                                separated                              

  `provider_admission.py`       schema                                 successful live
                                `savant.opus.provider-admission.v3`;   admission
                                configuration/probe surfaces           

  `admission_projection.py`     normalize/write/load projection        complete execution
                                functions captured                     integration

  `providers/catalog_text.py`   schema `savant.opus.catalog-text.v4`;  live failover and
                                admitted/selection candidate surfaces  cameo success
  ---------------------------------------------------------------------------------------

this advances the handoff's older broad-dump account. the older probe's
`rate_limited` and `admitted=false` remain reported results for that
probe, not present universal provider status.

### 9.3 distinct provider states

credential presence, credential validity, configured profile, discovered
model, capability match, admitted provider, selected route, and
successful inference are different claims. no one state establishes all
the others.

the specific date-as-minor concern is addressed in the inspected v3
source through a dotted minor-version pattern and independent date
scoring. this is a source observation, not a new ranking test. preserve
exact source when resuming.

### 9.4 cameo and failover

cameo's ninefold expansion, invocation correction, admission execution
linkage, and focused integration remain paused under the recorded user
priority. the exact latest cameo behavior is not established by the
targeted opus inspection.

predecessor sections disagree about failover proof. retain that conflict
until the exact deployed replacement and relevant evidence are
available. do not turn the known same-origin/browser success into proof
of every provider-failure path.

## 10. modus and reusable application composition

### 10.1 composition model

reusable substance is referenced by instances; typed masks constrain
legitimate variation; moods express modular methods; slots attach
capabilities; typed segues expose relationships; application and
interface views project the resulting composition.

variation must not silently create an alternate owner. shared mask
content can itself be reused where semantic identity is proven. a
composition view should not become a manually synchronized clone of its
components.

### 10.2 coalesce continuity

s2 reports coalesce identity migration and application extraction
complete. it also records an extensible sliver pool replacing a fixed
27-piece target, with alloy limited to nine slivers or fewer.

older accepted modus references coalesce while migration-canon material
describes privileged historical layers as superseded. preserve both the
reported implementation achievement and unresolved authority tension. do
not infer a new universal edifice from composition labels.

### 10.3 application-building surfaces

the durable direction includes reusable application composition, state
projections, semantic navigation, responsive composition, interaction
attachments, accessibility, commands, visual systems, lifecycle,
provenance, reversible evolution, degraded operation, geometry/renderer
separation, justified caching, and stable instance reuse.

these are strategic capabilities, not claims of universal present
implementation. add abstractions only when a real bounded application
need demonstrates reusable semantics.

### 10.4 filament vector structure

  -----------------------------------------------------------------------------------------
  stage                                    purpose                        authority
                                                                          boundary
  ---------------------------------------- ------------------------------ -----------------
  reusable vector primitives               semantic input substance       remain under
                                                                          legitimate source
                                                                          owners

  instances and scene composition          organize                       do not copy
                                           geometry/style/relationships   source truth

  transforms, paint, text, clips, masks,   represent scene meaning        exact support
  filters                                                                 depends on
                                                                          current
                                                                          implementation

  definitions and reference normalization  resolve reusable dependencies  deterministic
                                                                          ordering and
                                                                          reference
                                                                          semantics

  validation and geometry                  enforce relevant constraints   proof must cover
                                                                          actual risks

  svg compilation and serialization        produce deterministic output   svg remains
                                                                          projection

  optimization/diagnostics/compatibility   derived outputs                no new source
                                                                          authority
  -----------------------------------------------------------------------------------------

this is the retained target structure. the predecessor records a
rotated-arc endpoint regression and incomplete implementation. no
external geometry or rendering dependency is adopted here.

## 11. carbon applications and domain boundaries

### 11.1 oriel

oriel is a carbon-owned module for world chronology/logistics and
simulation-related capability. its historical purpose includes importing
characters, locations, and objects; evolving world state; accepting plot
decisions; previewing consequences; and exposing chronology/logistical
inconsistencies.

preserved interface intentions include module dashboard, draggable world
clock, zoom, pane-to-truss nesting, link interface, import loader,
approval window, timeline details, running log, json persistence,
color-coded modules, and versioning. `corpus → oriel` and `pulse → reso`
naming history remains recorded. these intentions do not prove feature
completion.

preserve the prohibition on casually renaming or restructuring oriel,
its anti-cliché direction, and "no gates in oriel naming" as
domain/interface guidance without using it to rewrite the global
accepted gate edifice.

### 11.2 oriel boundaries

the predecessor records implementation semantics including:

  concern                               retained owner/meaning
  ------------------------------------- -------------------------------------------
  oriel specialization                  carbon
  chronology/logistics                  carbon
  capability projection application     filament
  capability transformation             modus
  worldline/reachability/causal views   derived projections
  reality binding                       derived constraint projection
  possibility selection                 simulation selection, not canon promotion

oriel may not move verified historical anchors, claim a projection as
history, promote a simulated selection directly to canon, or infer
availability from missing evidence.

### 11.3 guise

guise is a carbon simulation/projection system. the predecessor records
commands `carbon-guise` and `guise-import-sgis-crew`,
graph/capability/manifest records, runtime concerns for behavior,
continuity, relationships, arcs, memory, pressure, restraint, debt,
motif, echo, counterfactuals, falsification, and scene projection.

the prior count of 29 runtime files, three focused test files, and 49
character heads is dated evidence from the earlier capture. it is not a
claim that all character state is canonical or that this documentation
pass retested guise.

### 11.4 domain import

savant provides general infrastructure; viscera is a domain consumer.
domain-specific canon belongs in explicit imports and accepted knowledge
paths. simulation uses references/projections of canon rather than
silently taking ownership.

the full handoff preserves the luka's-father fact set and its unknowns.
those facts were not verified as persisted into the ubuntu canon store.
this revision does not write narrative canon to that store or infer
missing biography.

## 12. niche, atlas, kindred, and governance

### 12.1 niche physical reference

the retained backend path is:

`/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/niche/apps/taskboard/server.py`

the retained task-store path is:

`/root/savant-runtime/runtime/niche/tasks.sqlite3`

these are inherited implementation references, not a new database
selection for straub. niche remains task owner; coda remains durable
mutation owner.

the predecessor records these interface surfaces:

  method   path
  -------- ------------------------------------
  GET      `/api/health`
  GET      `/api/tasks?include_terminal=true`
  GET      `/api/dashboard`
  GET      `/api/state`
  GET      `/api/history`
  GET      `/api/living`
  GET      `/api/living/fabric`
  GET      `/assets/command.html`

preserve contracts when relevant; do not redesign the backend solely for
frontend convenience. this table does not claim current endpoint
reachability.

### 12.2 atlas projection layering

  -----------------------------------------------------------------------
  layer                   content                 owner boundary
  ----------------------- ----------------------- -----------------------
  authoritative task      legitimate task         niche
  state                   primitives and          
                          transitions             

  normalized shared       consistent semantic     derived from niche
  projection              task view               

  atlas projection        spatial geography and   application view, not
                          relationships           task authority

  ephemeral interface     selection, viewport,    no silent durable task
  state                   local interaction       mutation
  -----------------------------------------------------------------------

preserve task identity, shared selection, recommendations,
inspector/theme integration, navigation, scrolling, and api
compatibility. do not add duplicate polling or a second recommendation
engine.

geometry and rendering should remain separable. accessibility can
present the same semantics through another view. mobile uses shared
primitives with an appropriate composition rather than a squeezed
desktop sidebar.

the historical non-clickable atlas report remains unresolved in the
reviewed sources. no new activation defect was reproduced here.

### 12.3 kindred

kindred's supported direction is direct admitted relationships, reusable
role/profile semantics, policy, deterministic
generational/collateral/adoption/affinity calculations, explainable
derived relationships, and disposable graph/tree views.

the predecessor records `lexicon/kindred/` modules for
adoption/step/guardian handling, alliance/affinity, collateral and
generational calculus, descent and propagation policy, roles,
resolution, validation, legacy bridging, and registries. filenames
establish implementation presence in that earlier capture, not
correctness.

the broader discipline-engine expansion remains disputed where it claims
unrelated graph concerns. `kinship` historical compatibility must not
become a second canonical methodology.

### 12.4 living governance and scyon

living governance semantics/evaluation/projections remain separate from
coda apply, pryme interpretation, and niche task context. consumer
packets carry evidence, not jurisdiction.

scyon compatibility inventory, focal-owner resolution, and
owner-proposal compiler filenames show tooling, not accepted ownership.
final faculty catalog and unique placement remain unknown unless
stronger authoritative sources establish them.

## 13. physical placement and compatibility

### 13.1 root areas

these are retained root-level structural reference areas, not an
exhaustive current inventory:

  -------------------------------------------------------------------------
  area                  structural role in the        caution
                        reference                     
  --------------------- ----------------------------- ---------------------
  `authority/`          authority-related records     presence is not
                                                      acceptance

  `assurance/`          validation/scanner/compiler   proposal is not
                        mechanics                     authority

  `canon/`,             canonical knowledge-related   accepted status must
  `canon-system/`       surfaces                      be established

  `commands/`           executable entry surfaces     commands may depend
                                                      on incomplete modules

  `context/`            context-related               not duplicate canon
                        representation                

  `docs/`               reference artifacts           no authority by
                                                      documentation

  `evolution/`          evolution mechanics           preserve authorized
                                                      transitions

  `frontend/`           interface implementation      ui state is not task
                                                      truth

  `edifices/`        edifice-related             graph semantics
                        representation                govern

  `lexicon/`            semantic vocabulary           names alone do not
                        mechanisms                    decide ownership

  `ontology/`           recursive implementation      do not flatten for
                        spine                         convenience

  `runtime/`            runtime mechanisms/state      physical location
                        surfaces                      does not assign
                                                      semantic owner

  `tests/`              assurance source              existence is not a
                                                      passing result

  `vault/`              custody/replay-related        retained evidence is
                        material                      not automatically
                                                      canon
  -------------------------------------------------------------------------

### 13.2 recursive physical spine

the inherited semantic-owner implementation root is:

`/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles`

actual owner paths beneath it must come from current source evidence. do
not use a conceptual diagram to manufacture missing folders.

straub's placement at `/root/savant-runtime/runtime/straub` does not
make it ownerless or outside carbon. a compatibility path or symlink
does not create a second semantic instance unless accepted authority
says so.

### 13.3 compatibility and evolution

retain external contracts, class names, imports, schemas, command
surfaces, and path dependencies when valid. lowercase applies to new
savant-owned prose and identifiers unless compatibility or stronger
authority requires preserved spelling.

the removal directive explicitly overrides compatibility for the
obsolete straub term: no alias survives there. that exception does not
authorize blind replacement in unrelated historical evidence.

a changed representation should preserve semantic continuity and
deterministic or reversible migration where needed. append supersession
lineage; do not rewrite accepted past decisions to make the new
representation appear timeless.

### 13.4 historical recovery assets

s2 lists `/mnt/data/straub-current.tar`,
`/mnt/data/straub_remove_radia_nano.txt`, and standalone corrected
files. those paths belonged to the source conversation and are not
confirmed attachments in this workspace.

the current supplied dump contains the twelve captured straub files but
does not establish the missing six bodies. if those bodies are required
for exact preservation, obtain the actual recovery source rather than
inventing it. historical archives must be translated under current
isotope-only authority before use.

## 14. security, scale, and interoperability

### 14.1 effect boundaries

separate read, projection, verification/admission, provider execution,
delegated action, and durable mutation. a successful projection request
does not grant write permission. an authenticated provider call does not
authorize changing canon.

secrets stay outside source/dump/report content. use only necessary safe
diagnostics. do not expose raw credentials, persist them in handoffs, or
treat secret hashes as necessary documentation by default.

### 14.2 input and path boundaries

validate external input before normalization into owner-controlled
primitives. reject malformed or incompatible representations without
destructive reinterpretation. preserve exact authority metadata rather
than "repairing" it by inference.

path safety, restrictive permissions, atomic writes, and allowed
operations must be considered at the effect boundary. do not claim
generic path safety solely from `Path.resolve()` or an atomic rename.

### 14.3 performance mechanisms

  -------------------------------------------------------------------------
  technique               legitimate trigger         authority limit
  ----------------------- -------------------------- ----------------------
  streaming/batching      large input or repeated    no omission of
                          operations                 required provenance

  lazy projection         expensive views not always stale state remains
                          needed                     explicit

  incremental             known dependencies and     no parallel truth
  recomputation           frequent changes           

  deterministic caches    reproducible expensive     cache keys include
                          derived work               relevant
                                                     inputs/version

  content deduplication   proven equal               text equality does not
                          representation/substance   prove semantic
                                                     equivalence

  indexes                 credible lookup/traversal  indexes remain
                          cost                       rebuildable

  bounded concurrency     parallel work with         guarantees scoped to
                          resource contention        actual coordination

  backpressure/resource   producers can outrun       failure cannot
  limits                  consumers                  silently discard
                                                     authority
  -------------------------------------------------------------------------

no benchmark or scale certification is claimed. choose mechanisms only
for credible workload or architectural need.

### 14.4 external compatibility

external interface → validation/normalization → savant-owned primitive →
legitimate owner execution/composition → compatibility projection.

external protocols and dependencies are implementation resources. they
must not redefine internal ownership or create vendor-bound truth.
existing savant primitives and the standard library are preferred when
equivalently capable. current upstream research belongs to a concrete
later adoption decision, not a speculative dependency survey.

## 15. structural conflicts and continuation

### 15.1 controlling resolutions

  ---------------------------------------------------------------------
  issue                              current supported resolution
  ---------------------------------- ----------------------------------
  accepted edifice versus old      current obelisk-to-trait edifice
  iota/mote/portal text              controls

  oriel-as-exile historic roster     later explicit carbon-owned
                                     sibling placement controls

  straub versus datrix               module versus created product;
                                     distinct identity

  isotope semantics                  deterministic projection

  obsolete straub term               removed from active
                                     implementation; historical
                                     evidence retained

  refresh absent in handoff          source now captured; behavioral
                                     proof still separate

  old opus broad-dump description    discovery/admission/catalog newer
                                     source captured

  old `/mnt/data` paths              historical asset references, not
                                     guaranteed local availability
  ---------------------------------------------------------------------

### 15.2 unresolved matters

do not silently settle coalesce privileged-layer tension, final
exile/faculty enumeration, scyon focal ownership, kindred discipline
scope, failover proof conflict, missing restoration source availability,
or database-engine selection.

do not certify stale-writer safety, production directory permission
safety, universal mask/mood execution, complete owner-to-owner contract
coverage, atlas usability, or vector renderer correctness without the
relevant evidence.

### 15.3 precise implementation continuation

when the user resumes straub implementation, use the captured refresh
source and exact materialized exports as the immediate baseline.
preserve the known classes `ContentionSafeIsotope`,
`AtomicIsotopeCache`, and `StraubIsotopeIndex`; do not recreate an
already captured file blindly.

restore query, composition, step, datrix, module, and exports from exact
source contracts, then restore focused commands. perform only necessary
compilation and the focused end-to-end isotope/datrix proof. check
active straub source/commands for the removed term; historical
appendices are outside that removal scope.

the package remains incomplete until those dependencies are restored and
integration is demonstrated. this document does not advance
implementation merely by describing it.

### 15.4 reference completion

this structural update is complete when its supported topology, current
captured file state, unresolved boundaries, and companion references are
coherent and the document is saved. its version indicates reference
evolution only.

## 16. verbatim predecessor

the following complete predecessor is preserved for lineage. it contains
nested older edifices, stale baseline metadata, historical
priorities, and conflicting completion claims. those remain evidence
only; the current sections above control this document's present
interpretation within the stated authority edifice.

```{=html}
<details>
```
```{=html}
<summary>
```
complete structure v3.28.0, preserved verbatim

```{=html}
</summary>
```
# SAVANT STRUCTURE CURRENT --- DETERMINISTIC REFERENCE PROJECTION

**Version:** 3.28.0\
**Date:** 2026-09-14\
**Status:** deterministic structure/reference projection; not
independent authority\
**Root:** `/root/savant-runtime`\
**Task governance / Masterplan projection owner:** Niche\
**Durable mutation owner:** Coda\
**Authority effect:** none\
**Baseline:** `SAVANT_STRUCTURE_CURRENT_v3.27.0.md`\
**Implementation evidence:**
`sdump_savant-runtime_20260914t041253398022z.txt`\
**Snapshot SHA-256:**
`a5358640313ce68249a60aa7036008aa5b9896ce5dabca088699d48d7c78d335`

## 0A. v3.28 controlling structural delta

This delta supersedes stale structural metadata and status statements
retained from v3.27 and earlier. Retained sections remain lineage only
where they disagree with this section.

### 0A.1 projection identity

``` text
target                         /root/savant-runtime
generated                      2026-09-14T04:13:29Z
tool                           sdump-enterprise 5.1.1
schema                         savant.sdump.bundle.v5
profile                        code
files seen                     6453
included records               5332
unique contents                4927
duplicate files                405
source bytes represented       132229908
rendered content bytes         93617490
duplicate bytes avoided        38612560
skipped records                1338
redactions                     74
symlinks                       5
failures                       0
snapshot hash                  a5358640313ce68249a60aa7036008aa5b9896ce5dabca088699d48d7c78d335
projection only                true
authority effect               none
```

The profile had an unbounded cumulative content budget and a 16 MiB
per-file ceiling. Excluded and oversized bodies remain unknown. This
structure document must not infer them.

### 0A.2 universal recursive structural law

``` text
substance
  └─ instance
      └─ composition
          └─ typed segue
              └─ deterministic projection
```

The recursive identity spine remains:

``` text
obelisk
└─ gate
   └─ innate
      └─ exile
         └─ prodigal
            └─ quirk
               └─ facet
                  └─ nuance
                     └─ trait
```

The identity edifice is semantic. Filesystem nesting is a projection
of it, not its source of truth.

### 0A.3 structural properties required of Savant-owned elements

Where applicable, elements remain:

-   identifiable;
-   graph-addressable;
-   instanceable;
-   composable;
-   attachable;
-   reusable;
-   extensible;
-   lineage-aware;
-   provenance-aware;
-   dependency-aware;
-   dependent-aware;
-   authority-aware;
-   deterministically projectable;
-   replay/recovery compatible.

A representation that cannot preserve these properties requires explicit
justification.

### 0A.4 authority versus structure

Structure does not create authority.

``` text
authority primitive
      ↓ references
semantic instances
      ↓ composition
typed graph
      ↓ deterministic derivation
runtime / interface / migration projections
```

A cache, UI state, generated index, simulation, dump, receipt, migration
artifact, or compatibility projection cannot become authoritative merely
by persistence.

### 0A.5 ownership topology

``` text
                         ┌──────── Pryme ────────┐
                         │ authority resolution  │
                         └──────────┬─────────────┘
                                    │
        ┌─────────────── semantic/runtime ownership ───────────────┐
        │                                                          │
   Palaver ──conversation──► Envoy ──persona/voice intent──► Opus
      │                        │                              │
      │                        │                              └─ provider/model execution
      │                        └─ Orobouros default persona
      │
      ├─► Scrybe context projection
      ├─► Niche task governance
      └─► Coda authorized mutation ──► Notary evidence/admission boundary

   Modus ── Mood + modular composition
   Filament ── deterministic projection execution
   Carbon ── simulation, including Guise
   Lore ── canonical knowledge substance
   Pact ── contracts/constraints/permissions
   Thryce ── assurance
   Spyral ── migration/evolution compatibility
   Lythe ── deterministic derivation
   Dryve ── delegated execution lifecycle
   Urge ── candidate refinement
   Vault ── custody/replay/recovery
```

Arrows indicate consumption/delegation, not transfer of ownership.

### 0A.6 accepted Exile state

Decision `AD-20260913-001` remains accepted authority for:

``` text
lore
mobius
notary
pact
palaver
shatter
```

Promotion changes status, not purpose. Existing boundaries remain unless
separately superseded.

### 0A.7 Palaver / Envoy / Opus execution topology

``` text
mobile/desktop browser
        │
        ▼
production frontend :5173
        │ same-origin /api
        ▼
Palaver :8787
        │
        ├──► Scrybe context projection
        │
        ├──► Envoy
        │      └──► Orobouros persona/cognitive projection
        │
        └──► Opus
               └──► provider/model route
```

Current continuation evidence establishes the same-origin browser
transport repair and Orobouros as the normal/effective workspace
persona. Provider credentials and provider selection remain Opus
concerns.

Execution-time provider failover must remain marked
**authored-unverified** until live evidence establishes the replacement
behavior.

### 0A.8 Guise structural projection

Guise is structurally present under Carbon.

Observed projected surfaces include:

``` text
commands/
├─ carbon-guise
└─ guise-import-sgis-crew

carbon/
├─ graph/guise.json
├─ registry/capabilities/guise.json
├─ registry/manifests/guise.json
├─ runtime/guise.py
├─ runtime/guise_arc.py
├─ runtime/guise_behavior.py
├─ runtime/guise_blindspot.py
├─ runtime/guise_compare.py
├─ runtime/guise_continuity.py
├─ runtime/guise_counterfactual.py
├─ runtime/guise_debt.py
├─ runtime/guise_echo.py
├─ runtime/guise_extract.py
├─ runtime/guise_falsify.py
├─ runtime/guise_generate.py
├─ runtime/guise_interrogate.py
├─ runtime/guise_memory.py
├─ runtime/guise_motif.py
├─ runtime/guise_negative_space.py
├─ runtime/guise_pressure.py
├─ runtime/guise_projection.py
├─ runtime/guise_provider.py
├─ runtime/guise_reciprocity.py
├─ runtime/guise_reconcile.py
├─ runtime/guise_relationship.py
├─ runtime/guise_restraint.py
├─ runtime/guise_runtime.py
├─ runtime/guise_scene.py
├─ runtime/guise_state.py
├─ runtime/guise_store.py
├─ runtime/guise_surprise.py
└─ runtime/guise_temporal.py
```

The projection also contains three Guise-focused test files and 49
character head-state records under
`runtime/state/carbon/guise/characters/`.

Structural interpretation:

``` text
canonical character substance / admitted evidence
        │ reference / projection
        ▼
Carbon.Guise simulation instance
        │
        ├─ temporal state
        ├─ behavior
        ├─ relationship
        ├─ continuity
        ├─ arc
        ├─ memory
        ├─ pressure / restraint / debt
        ├─ motif / echo / negative space
        ├─ counterfactual / falsification
        └─ scene projection
```

This diagram is a structural interpretation of observed implementation
names and established Carbon ownership. It does not elevate runtime
character state to canon.

### 0A.9 Modus and Mood structure

Mood remains Modus-owned compositional semantics.

``` text
reusable semantic primitives
        ↓ instances
Modus composition
        ↓
Mood / Alloy / application composition as applicable
        ↓
interface or runtime projection
```

Mood must not become a duplicate persona system, global configuration
bucket, or UI theme authority.

### 0A.10 Filament vector-rendering target structure

The accepted specification targets a Filament-owned deterministic vector
projection system:

``` text
vector primitive registry
        ↓ instances
scene graph
        ├─ geometry
        ├─ transforms
        ├─ paint
        ├─ text
        ├─ masks/clips
        ├─ filters/compositing
        ├─ symbols/instances
        ├─ constraints/anchors
        └─ animation/interaction metadata
        ↓
definition/reference normalization
        ↓
deterministic SVG compiler
        ├─ readable projection
        ├─ production projection
        └─ diagnostic projection
```

The specification is not implementation evidence. No renderer runtime
should be added to this structural projection until verified
implementation exists.

### 0A.11 reusable living substrates

Retain the recognized reusable substrate set and its ownership
boundaries:

``` text
Scyon   living structural implementation
Splyce  living interface/interaction
Scrybe  context/recall projection
Pryme   authority interpretation
Cypher  translation/normalization/serialization
Thryce  assurance
Spyral  evolution/migration compatibility
Lythe   deterministic derivation
Dryve   delegated execution lifecycle
```

These are mechanisms, not identity tiers and not a second Exile
edifice.

### 0A.12 typed segue requirement

Cross-element relationships should be explicit typed segues when they
carry semantic meaning.

A segue should expose, where applicable:

-   source identity;
-   target identity;
-   relationship type;
-   directionality;
-   authority effect;
-   provenance;
-   lineage;
-   constraints;
-   lifecycle;
-   compatibility/version semantics;
-   dependencies;
-   deterministic projection behavior.

Hidden coupling through filenames, import accidents, shared mutable
globals, or undocumented state is structurally inferior to an explicit
relationship.

### 0A.13 source, instance, and projection separation

Use three distinct questions:

1.  **What is substantiated?** The authoritative or reusable primitive.
2.  **What is instantiated/composed?** Context-specific use of the
    primitive.
3.  **What is projected?** Derived runtime, UI, compatibility,
    migration, or reporting representation.

Do not answer all three by copying the same substance into three files.

### 0A.14 lineage topology

For evolvable elements, preserve:

``` text
origin
  ↓
version / accepted decision / admitted evidence
  ↓
instance lineage
  ↓
composition lineage
  ↓
projection lineage
```

Supersession appends lineage. It does not erase prior accepted state.

### 0A.15 provenance topology

Provenance should answer:

-   where the substance came from;
-   under what authority/evidence class it entered;
-   what transformation produced the current representation;
-   what inputs were referenced;
-   what implementation/version performed the transformation;
-   whether the result is authoritative, evidentiary, simulated, or
    projected.

### 0A.16 dependency topology

Dependencies and dependents should be queryable rather than implicit.

``` text
primitive
  ├─ dependencies[]
  └─ dependents[]
       ├─ instances
       ├─ compositions
       ├─ segues
       └─ projections
```

This enables safe evolution without centralizing all behavior into a
monolith.

### 0A.17 deterministic projection contract

A deterministic projection should define:

-   authoritative/referenced inputs;
-   projection version;
-   normalization rules;
-   stable ordering;
-   canonical serialization where byte identity matters;
-   hash semantics where content identity matters;
-   rebuild behavior;
-   stale-state detection where necessary;
-   failure behavior;
-   authority effect `none` unless separately authorized.

### 0A.18 derived-state lifecycle

Derived state should normally be:

``` text
compute → persist/cache optionally → validate identity → consume → invalidate/rebuild
```

It should not require manual synchronization with its source primitives.

### 0A.19 mutation topology

``` text
requested change
    ↓
authority / permission interpretation
    ↓
evidence / constraint evaluation
    ↓
Coda authorized mutation
    ↓
immutable mutation history
    ↓
dependent deterministic reprojection
```

A projection must not mutate its own source authority merely because it
detects drift.

### 0A.20 verification topology

``` text
claim / candidate / mutation result
        ↓
Notary verification/admission
        ↓
attestation / admitted evidence
        ↓
authorized downstream use
```

Generation, simulation, and verification remain separate
responsibilities.

### 0A.21 simulation topology

Carbon simulations must preserve a hard semantic boundary:

``` text
referenced canonical/evidentiary inputs
        ↓
simulation instance
        ↓
simulated state / trajectories / counterfactuals
        ↓
projection / analysis
```

Simulation output does not become canon without an explicit admission
path.

Guise inherits this rule.

### 0A.22 external interoperability boundary

``` text
external protocol/schema/provider
        ↓
validation
        ↓
normalization / Cypher compatibility
        ↓
Savant-owned primitive
        ↓
existing owner execution/composition
        ↓
optional compatibility projection
```

External schemas terminate at the boundary. They do not dictate internal
ownership.

### 0A.23 security boundary structure

Secrets belong outside source projections and dumps. Provider
credentials remain execution configuration under the appropriate owner.
Diagnostics may expose presence, identity hashes, or safe metadata when
justified, never secret values.

Mutation, admission, provider execution, and externally reachable
interfaces should remain distinct effect boundaries.

### 0A.24 performance structure

Performance mechanisms should attach to the primitive they accelerate
rather than create a parallel semantic model.

Preferred forms:

-   content-addressed deduplication;
-   stable hashing;
-   bounded concurrency;
-   streaming;
-   lazy projection;
-   incremental recomputation;
-   deterministic cache keys;
-   disposable indexes;
-   resource budgets;
-   backpressure where producers can outrun consumers.

### 0A.25 recovery structure

Recovery should flow from preserved authority and immutable lineage:

``` text
authoritative primitives + accepted history
        ↓
replay
        ↓
rebuild deterministic projections
        ↓
verify hashes/invariants
        ↓
resume
```

Backups and receipts support recovery but do not become parallel truth
systems.

### 0A.26 compatibility structure

When a representation evolves:

``` text
old accepted representation
        ↓ explicit migration / adapter
new representation
        ↓
compatibility projection when required
```

Do not destructively rewrite history merely to simplify the current
schema.

### 0A.27 architectural compression tests

Before adding structure, ask:

-   can an existing primitive be parameterized?
-   can this be an instance rather than new substance?
-   can this be a typed segue rather than a registry?
-   can this be a deterministic projection rather than stored authority?
-   can one stronger primitive replace several wrappers?
-   can compatibility be projected rather than duplicated?

Only add a new owner when the concept has an irreducible jurisdiction
not already owned.

### 0A.28 structural anti-pattern register

Reject by default:

1.  duplicate authority;
2.  duplicate canonical substance;
3.  parallel registries for the same identity;
4.  manual projection synchronization;
5.  hidden cross-owner mutation;
6.  provider selection outside Opus;
7.  persona ownership outside Envoy;
8.  conversation ownership outside Palaver;
9.  task authority inside UI state;
10. verification ownership inside generators;
11. mutation ownership inside projections;
12. simulated state treated as canon;
13. filesystem presence treated as authority;
14. historical implementation treated as current;
15. compatibility aliases treated as new semantic identity;
16. application-specific copies of reusable primitives;
17. caches with independent truth semantics;
18. external schemas leaking into internal ownership;
19. secret-bearing diagnostics;
20. irreversible migrations without necessity.

### 0A.29 structural evidence states

Every important structural claim should be classifiable as:

``` text
accepted-authority
verified-implementation
admitted-evidence
deterministic-projection
authored-unverified
historical
inference
unknown
superseded
```

This prevents architecture diagrams from quietly converting intention
into implementation fact.

### 0A.30 current unresolved structural register

At v3.28:

-   Opus execution-time failover replacement remains unverified from the
    supplied continuation evidence.
-   Filament vector-renderer implementation is not established; only its
    specification/target architecture is established.
-   Niche task work remains paused by user directive.
-   Guise implementation presence is established, but its runtime
    character states remain simulation/projection evidence rather than
    canonical character authority.
-   Retained historical sections may contain stale priorities; section
    0A controls.

### 0A.31 finite continuation structure

``` text
current reference packet
    ├─ newest sdump implementation projection
    ├─ Masterplan v3.28
    ├─ Structure v3.28
    └─ external task specifications that must survive migration
            │
            ▼
read only mandatory live files
            │
            ▼
next user-selected bounded implementation
            │
            ▼
minimum validation
            │
            ▼
stop
```

### 0A.32 v3.28 structural compression summary

Savant's architecture should be understood as a small set of strong laws
rather than a growing catalog of exceptions:

``` text
authority is explicit
substance exists once
identity is semantic
instances reuse substance
composition builds higher order
typed segues expose relationships
owners retain jurisdiction
derived state is projected
history is immutable
evolution is reversible where practical
simulation is not canon
verification is not generation
mutation is authorized
external systems normalize at the boundary
recovery rebuilds from preserved authority
```

Everything else should emerge from those laws unless a stronger accepted
authority requires otherwise.

## 0B. retained v3.27 structure body

The complete v3.27 structure follows for lineage. Where it conflicts
with section 0A, section 0A controls as the newer deterministic
reference projection.

# SAVANT STRUCTURE CURRENT --- DETERMINISTIC REFERENCE PROJECTION

**Version:** 3.27.0\
**Date:** 2026-09-13\
**Status:** deterministic structure/reference projection; not
independent authority\
**Root:** `/root/savant-runtime`\
**Task governance / Masterplan projection owner:** Niche\
**Durable mutation owner:** Coda\
**Authority effect:** none\
**Baseline:** `SAVANT_STRUCTURE_CURRENT_v3.25.0.md`\
**Implementation evidence:**
`sdump_savant-runtime_20260911t214015003093z.txt`

## 0A. v3.26 structural delta

This section is the controlling continuation delta over v3.25.0 where
newer verified evidence differs.

### newest runtime evidence

``` text
target: /root/savant-runtime
generated: 2026-09-11T21:40:54Z
tool: sdump-enterprise 5.1.1
schema: savant.sdump.bundle.v5
files seen: 4827
included files: 4355
unique contents: 4089
duplicate files: 266
rendered bytes: 180476724
failures: 0
redactions: 71
snapshot hash: 5c92366eae093eed0f23d7e61d6e51dddfd26eeab663e785b0256d3ea5f5c0f2
projection_only: true
authority_effect: none
```

The effective dump profile had no cumulative content ceiling. That
output behavior is now targeted for correction so migration artifacts
remain small without changing SAVANT authority semantics.

### current self-hosted execution path

``` text
browser / production frontend :5173
        ↓ same-origin /api proxy
palaver :8787
        ↓ conversation ownership
envoy / orobouros persona projection
        ↓ provider execution request
opus text_inference_route
        ↓
configured external inference provider pool
```

Verified live boundaries:

-   Palaver owns conversation;
-   Envoy owns persona/cognitive expression;
-   Opus owns provider/model selection and execution;
-   Scrybe owns memory/context projection;
-   Coda owns durable mutation;
-   Niche owns task governance;
-   Notary owns verification/evidence admission.

Browser transport is operational. OpenAI credential identity in
`/root/.env` matches the running Palaver process and authenticates
directly. The latest Palaver/Orobouros request reached inference and was
rate limited.

### current unresolved implementation boundary

The verified router behavior executes one selected text provider.
Runtime provider failure does not yet have proven failover to the next
configured provider. The pending authored change adds execution-time
fallback inside Opus without transferring provider authority to Palaver
or Envoy.

### persona state

Explicit request persona `orobouros` is verified to resolve. Workspace
state still projects `historical_research_mode`; normal
workspace/default selection must be returned to Orobouros after
inference is proven.

### paused work

The earlier Niche/Masterplan task queue is paused by current user
directive while self-hosted migration is completed. Do not resume it
automatically.

## 0A. v3.27 structural delta

### newest implementation projection

Current implementation evidence baseline is
`sdump_savant-runtime_20260913t182202499576z.txt`, generated
`2026-09-13T18:22:22Z` by `sdump-enterprise 5.1.1` for
`/root/savant-runtime`, snapshot SHA-256
`3f2fa7cd7ceb0a7a88b8161b05d7b6645a35d4c199d5be6837959b4fa5ee2d39`.

The artifact is projection-only and has no authority effect. It observed
4,600 files and 4,374 candidates, emitted 1,006 source/canon records
representing 883 unique bodies, and retained 3,368 files as
metadata-only. The effective compact profile exhausted its 8 MiB body
budget. Metadata-only or excluded bodies remain unknown from the dump.

### accepted exile state

Accepted decision `AD-20260913-001` establishes these six exiles as
accepted rather than provisional:

``` text
lore
mobius
notary
pact
palaver
shatter
```

Their ownership scopes are unchanged by the promotion.

### recursive modularity law

After truth and authority, maximum semantic modularity governs
structural evolution:

``` text
canonical substance
→ typed mask / modular method where legitimate
→ configured instance
→ recursive composition
→ typed segue / relationship
→ deterministic projection
```

Every Savant object remains an instance. Canonical substance exists once
at the narrowest legitimate authoritative owner. Higher structures
emerge by reference and composition rather than copying lower-level
substance.

A mask expresses only legitimate variation. A mask is not independent
authority. If the mask filler itself contains proven shared substance,
that substance should be recursively canonicalized and instanced rather
than copied.

### mood structural clarification

Retained v3.26 canon says Mood is behavior transformation and canonical
Mood definitions belong under Modus. Current user directive broadens the
working structural role: moods are multiple distinct methods for making
Savant elements modular. Behavior transformation remains one specialized
Mood. This current directive outranks the narrower reference projection
but does not silently rewrite historical authority records.

### Modus structural role

Modus owns modular composition, composition modes, module boundaries,
and canonical Mood organization. Its accepted authority record
explicitly requires shared prodigals and quirks to be instanced with
masks rather than duplicated and functional substance to be instantiated
once and composed by reference.

Modus masking should therefore be interpreted recursively across
meaningful semantic levels while preserving identity, ownership,
lineage, provenance, dependencies, dependents, authority, and typed
relationships.

### current interaction boundary

The self-hosted conversation chain is now practically proven:

``` text
browser/frontend :5173
→ same-origin /api
→ palaver :8787
→ envoy/orobouros persona projection
→ opus route/provider execution
→ provider
```

Ownership remains separate even when one runtime calls another:

-   Palaver owns conversation/workstation orchestration;
-   Envoy owns persona/voice/outward expression;
-   Opus owns provider/model routing and AI execution.

Execution-time provider failover is Opus-owned and has been
installed/proven in the post-v3.26 development state. The prior v3.26
migration blocker is historical.

### Filament structural boundary

Filament owns projection execution/workers. The vector renderer under
development is a semantic vector scene compiler whose SVG is a
deterministic projection rather than source truth. It must remain
separated into semantic model, geometry/style, composition/definitions,
validation, compiler, and serializer concerns. The renderer is
incomplete and must not be represented as accepted implementation merely
because specification or staging files exist.

### current architecture priority

Implementation is presently paused by current user directive while
architecture/reference state is refreshed. When explicitly resumed,
prioritize executable instance/reference/mask/Mood/Segue/Slot/attachment
infrastructure and incremental convergence of proven duplicate substance
before unrelated feature expansion.

## 0. interpretation rule

This document describes the current supported structural model using the
newest supplied runtime evidence and current user directives.

It is not the authoritative graph.

Filesystem presence is evidence of implementation, not proof of semantic
ownership or acceptance.

Authority precedence:

``` text
current user directive
→ accepted authoritative graph
→ accepted decisions
→ constitutional canon
→ verified implementation
→ admitted evidence
→ deterministic projection
→ historical implementation
→ historical documents
→ inference
→ speculation
```

## 1. snapshot identity

Newest supplied runtime snapshot:

``` text
target: /root/savant-runtime
generated: 2026-09-07T19:56:34Z
tool: sdump-enterprise 5.1.1
schema: savant.sdump.bundle.v5
files seen: 4392
included files: 4006
unique contents: 3740
duplicate files: 266
failures: 0
redactions: 34
snapshot hash: c22fa366fce898430c411cffe466283388a4fb78976faeb442a15b0a35260cb8
profile hash: b720b361e58a495fa5a26756abf4d5c5bf2bd48a6ab5f0831153cb52ae7419bf
projection_only: true
authority_effect: none
```

The compact snapshot excludes several generated/runtime/history
categories and an oversized ownership graph. It must not be used as an
exhaustive absence test.

## 2. universal structural law

``` text
instance
├── identity
├── substance/reference
├── authority/provenance
├── attachments
├── slots
├── moods
├── typed segues
├── state/history where applicable
└── deterministic projections
```

Every SAVANT object is an instance.

Higher structures emerge through composition, parameterization,
attachment, projection, and typed Segues.

Canonical lower-level substance should not be duplicated merely because
a higher-level application needs it.

## 3. accepted identity edifice

``` text
obelisk
└── portal
    └── innate
        └── exile
            └── prodigal
                └── quirk
                    └── trait
                        └── mote
                            └── iota
```

Forward shorthand:

``` text
iota → mote → trait → quirk → prodigal → exile → innate → portal → obelisk
```

Typed Segues mediate edifice/transition semantics.

Inverse edifice is a projection.

## 4. semantic grammar

### rubric

Program-bearing semantic surface owned by the relevant program/semantic
owner.

### cabal

Shared substance materialized once at the narrowest proven common scope.

### kindred

Relationship methodology centered on direct admitted relationships,
reusable roles/profiles, policies, deterministic relationship algebra,
and explainable derived relationships.

Kindred is not generic ownership of every graph.

### segue

Typed transition, lineage, or direct connection between
instances/edifice levels.

### mood

Behavior transformation. Canonical Mood definitions belong under Modus.

### slot

Capability attachment. Slot is not Mood.

### attachment

Parameterized reference-first extension.

### projection

Deterministic derived view. Projection does not become source authority
by being materialized.

## 5. primary semantic ownership

``` text
niche
├── task discovery
├── decomposition
├── blockers/readiness
├── scheduling
├── task transitions
└── masterplan projection

coda
├── authorized durable mutation
└── mutation-history mechanics

opus
├── provider routing
├── model routing
└── ai execution

notary
├── verification
├── evidence admission
└── attestation

pact
├── contracts
├── constraints
├── permissions
└── agreements

modus
├── modular composition
└── canonical mood ownership

underscore
└── structural normalization / hidden support

shatter
└── controlled decomposition / fault isolation

palaver
├── conversation
├── workstation
└── patch-review orchestration

envoy
├── persona
├── voice
└── outward/cognitive expression

filament
└── projection execution / workers

lore / fluid canon
└── canonical knowledge-memory jurisdiction

scrybe
└── recall/context projection

pryme
├── authority interpretation
├── precedence
├── conflict interpretation
└── supersession interpretation

thryce
└── assurance / validation mechanics

spyral
└── migration / evolution transition mechanics

lythe
└── derivation mechanics

dryve
└── delegated action/execution substrate

urge
└── iterative candidate refinement

vault
├── custody
├── retention
├── replay
└── recovery

carbon
└── generalized simulation and simulation state/branch semantics
```

No owner may silently absorb another owner's authority because its code
calls or displays that owner's data.

## 6. current root-level structural projection

The exact live filesystem may contain additional material excluded by
the compact snapshot. The supported conceptual projection remains:

``` text
/root/savant-runtime
├── authority/
├── assurance/
├── canon/
├── canon-system/
├── commands/
├── context/
├── docs/
├── evolution/
├── frontend/
├── edifices/
├── lexicon/
│   └── kindred/
├── ontology/
│   └── obelisks/
├── runtime/
├── tests/
└── vault/
```

Physical placement does not determine semantic ownership.

## 7. recursive ontology spine

Current implementation continues to use the deep recursive template
spine:

``` text
/root/savant-runtime/ontology/obelisks/_template/
└── segue/
    └── gates/_template/
        └── segue/
            └── innates/_template/
                └── segue/
                    └── exiles/
```

Current active Exile implementations are materialized beneath this
spine.

Do not infer that every directory under the spine is independently
authoritative.

## 8. Niche current structure

Primary Niche application/backend location:

``` text
.../exiles/niche/apps/taskboard/
├── server.py
└── assets/
```

Task store:

``` text
/root/savant-runtime/runtime/niche/tasks.sqlite3
```

Known Niche runtime/state areas include:

``` text
/root/savant-runtime/runtime/niche/
/root/savant-runtime/runtime/living-state/
/root/savant-runtime/runtime/living-fabric/
```

The compact snapshot may exclude dynamic runtime state.

### 8.1 Niche semantic projection

``` text
authoritative task primitives
→ niche normalized semantic projection
→ synchronized application views
```

Niche remains task owner.

Dryve may provide mechanics without governing task semantics.

Coda remains durable mutation owner.

### 8.2 Niche frontend implementation families observed September 7

``` text
assets/
├── command.*
├── niche.*
├── niche-bootstrap.*
├── niche-navigation.*
├── niche-vnext.*
├── niche-causal-field.*
├── niche-causal-lens.*
├── niche-causal-vector.*
├── niche-consequence-map.*
├── niche-consequence-preview.*
├── niche-constraint-field.*
├── niche-continuity.*
├── niche-critical-channel.*
├── niche-cross-view-continuity.*
├── niche-dependency-gravity.*
├── niche-evidence-gate.*
├── niche-executable-environment.*
├── niche-execution-tunnel.*
├── niche-focus.*
├── niche-graphics.*
├── niche-motion.*
├── niche-objective-graphics.*
├── niche-projection-health.*
├── niche-provenance-thread.*
├── niche-readiness-boundary.*
├── niche-replay.*
├── niche-resilience.*
├── niche-semantic-runtime.*
├── niche-spatial-state.*
├── niche-themes.*
├── niche-unknowns.*
├── niche-unlock-horizon.*
└── niche-viewport-guard.*
```

This is a structural inventory of observed source families, not an
instruction to preserve every module forever.

Where multiple modules own the same semantic responsibility,
consolidation should prefer the strongest legitimate owner rather than
adding another layer.

## 9. Atlas current target structure

Atlas is a Niche/SAVANT application surface.

Desired modular decomposition:

``` text
niche shared projection
└── atlas application
    ├── composition
    ├── semantic projection
    ├── geometry
    ├── renderer
    ├── shell
    ├── lifecycle
    ├── interaction
    ├── accessibility projection
    ├── responsive composition
    └── ephemeral ui state
```

State boundary:

``` text
task authority
→ niche shared normalized projection
→ atlas derived projection
→ ephemeral atlas ui state
```

Atlas must not own:

``` text
task authority
task recommendation authority
duplicate polling
duplicate persistent task state
evidence admission
durable mutation
```

### 9.1 Atlas implementation chronology boundary

The September 7 sdump predates the later R13 modular Atlas work.
Therefore the current reference distinguishes:

``` text
September 7 sdump
→ verified captured implementation evidence

later R13.x Atlas files
→ later proposed/local implementation evidence

user report after R13.5
→ Atlas still not clickable
```

Do not collapse these evidence classes.

## 10. Kindred current implementation structure

Observed September 7:

``` text
/root/savant-runtime/lexicon/kindred/
├── __init__.py
├── adoption_step_guardian.py
├── alliance_affinity.py
├── collateral_calculus.py
├── descent_policy.py
├── discipline_engine.py
├── discipline_registry.yaml
├── generational_calculus.py
├── kindred.schema.yaml
├── kindred_engine.py
├── kindred_registry.yaml
├── kindred_validator.py
├── legacy_bridge.py
├── propagation_policy.py
├── relationship_resolver.py
└── role_calculus.py
```

Supported semantic direction:

``` text
direct relationship
→ role calculus
→ descent/propagation policy
→ generational/collateral calculus
→ adoption/step/guardian and alliance/affinity handling
→ explainable derived relationship
→ disposable projection
```

`discipline_engine.py` and `discipline_registry.yaml` remain physically
present but semantically disputed where they attempt to broaden Kindred
into unrelated graph disciplines.

Historical `kinship` paths remain compatibility evidence. New canonical
terminology is `kindred`.

## 11. Carbon / Oriel current implementation structure

Oriel is nested conceptually under Carbon simulation.

Observed September 7:

``` text
.../exiles/carbon/
├── lineage/
│   └── oriel_specialization.json
├── runtime/
│   ├── oriel.py
│   ├── oriel_boundary.py
│   ├── oriel_canon.py
│   ├── oriel_capabilities.py
│   ├── oriel_causality.py
│   ├── oriel_closure.py
│   ├── oriel_composition.py
│   ├── oriel_consequence.py
│   ├── oriel_graph.py
│   ├── oriel_horizon.py
│   ├── oriel_interface.py
│   ├── oriel_introspection.py
│   ├── oriel_inverse.py
│   ├── oriel_lineage.py
│   ├── oriel_observatory.py
│   ├── oriel_quantum.py
│   ├── oriel_quantum_capabilities.py
│   ├── oriel_reality.py
│   ├── oriel_simulation.py
│   └── oriel_worldline.py
├── tests/
│   └── oriel_integration.py
└── validation/
    └── oriel_closure.json
```

Conceptual boundary:

``` text
carbon
└── simulation
    ├── scenario/counterfactual
    ├── quantum possibility/cause-effect space
    └── oriel
        ├── chronology
        ├── logistics
        ├── inverse chronology
        ├── reality bindings
        ├── causal feasibility
        ├── consequences
        ├── reachability horizons
        ├── worldlines
        ├── interface
        └── introspection
```

Projection application may use Filament.

Capability transformation may use Modus.

Simulation output never self-promotes into historical canon.

## 12. Living Governance current implementation structure

Observed September 7:

``` text
/root/savant-runtime/runtime/
├── living_governance.py
├── living_governance_constitutional.py
├── living_governance_packets.py
└── living_governance_receipts.py
```

Semantic ownership remains:

``` text
living governance
├── governance semantics
├── evaluation evidence
└── governance projections

coda
└── durable mutation/apply

pryme
└── authority/supersession interpretation

niche
└── task context
```

The compact snapshot is not an exhaustive deletion/inventory oracle for
other runtime governance files.

## 13. Scyon focal compatibility/ownership structure

Observed September 7:

``` text
/root/savant-runtime/assurance/
├── scanners/
│   ├── inventory_scyon_focal_compatibility.py
│   └── resolve_scyon_focal_owner.py
└── compilers/
    └── compile_scyon_service_owner_proposal.py
```

Structural meaning supported by filenames:

``` text
compatibility inventory
→ ownership resolution
→ owner proposal compilation
```

A proposal is not accepted authority.

No Scyon focal owner should be asserted from these files alone.

## 14. application-building structural direction

Current user directive adds a durable interpretation to the existing
system:

``` text
current builder-facing exile/utility
→ reusable SAVANT primitive/mechanism
→ parameterized composition
→ SAVANT-native application surface
→ eventual end-user capability
```

This does not mean every current utility must become a public UI
unchanged.

The structural requirement is to separate:

``` text
durable semantic/runtime substance
from
temporary builder-facing presentation
```

Application construction should reuse:

``` text
instances
typed segues
moods
slots
attachments
rubrics
cabals
normalized projections
explicit state owners
lineage/provenance
```

rather than creating a parallel application ontology.

## 15. projection and authority boundaries

### source primitive

Stores admitted/canonical/authorized substance according to its owner.

### deterministic projection

Derived, reproducible, disposable.

### interface state

Ephemeral unless an owner explicitly persists it.

### cache/index

Performance structure only. Never authority merely because it exists.

### simulation

Derived possibility/state branch. Never history unless independently
admitted through the normal authority/evidence path.

### migration artifact

Transition evidence/mechanics. Does not become canonical structure
merely because migration produced it.

## 16. structural anti-patterns

Do not introduce:

-   duplicate task stores;
-   duplicate recommendation engines;
-   duplicate evidence authority;
-   duplicate mutation owners;
-   second canonical relationship methodology beside Kindred;
-   generic graph ownership swallowed into Kindred;
-   Oriel promoted to peer Exile without authority;
-   simulation promoted to canon;
-   frontend modules that fetch/store the same state independently
    without need;
-   presentation-specific copies of canonical substance;
-   file-count growth as a proxy for modularity;
-   generated projections treated as authority;
-   historical terminology globally rewritten without compatibility
    analysis.

## 17. current unresolved structural conflicts

### 17.1 Kindred discipline expansion

Present in implementation, not accepted as canonical broad Kindred
ownership.

### 17.2 kinship compatibility

Historical paths/tests remain. Canonical methodology term remains
`kindred`.

### 17.3 Scyon focal owner

Ownership proposal tooling exists. Accepted owner is not established by
that fact.

### 17.4 Atlas activation

Atlas remains structurally intended as a first-class Niche/SAVANT
application surface, but the latest user-visible result is that the
button does not open it.

This is an implementation defect, not a reason to create a second Atlas
authority or navigation system.

## 18. current implementation priorities

``` text
1. repair atlas activation without another competing event owner
2. preserve natural scrolling and top navigation
3. consolidate atlas/niche semantic ownership where duplication is proven
4. continue reusable savant application-composition primitives
5. continue kindred from current calculus/policy implementation
6. preserve carbon/oriel simulation boundaries
7. resolve scyon focal ownership only through accepted authority
```

## 19. deterministic structural summary

Current supported SAVANT shape:

``` text
savant
├── authority + accepted decisions + constitutional canon
├── recursive instance edifice
│   └── iota → mote → trait → quirk → prodigal → exile → innate → portal → obelisk
├── typed segues
├── rubric / cabal
├── moods under modus
├── slots / attachments
├── kindred relationship algebra
├── specialized semantic owners
│   ├── niche
│   ├── coda
│   ├── opus
│   ├── notary
│   ├── pact
│   ├── palaver
│   ├── envoy
│   ├── carbon
│   └── others under established ownership
├── deterministic projections
├── application surfaces
│   └── niche / atlas current workstream
├── runtime state
├── assurance
├── migration/evolution
└── vault custody/replay
```

The direction is compositional:

``` text
substantiate once
→ instance
→ attach/compose
→ typed segue
→ transform through mood where appropriate
→ project deterministically
→ render/application surface
→ act through the legitimate owner
```

That structure supports the current user goal of SAVANT becoming a
sophisticated application-building system without creating a competing
application authority.

## 20. retained v3.26 continuation boundary

The current system is structurally ready for self-hosted development,
but practical migration remains incomplete until Opus returns one live
provider-backed response through Palaver and the normal workspace
persona is Orobouros. The next change belongs in Opus runtime failover,
not in Palaver conversation ownership or Envoy persona authority.

## 21. v3.27 deterministic structural summary

``` text
savant
├── authority / accepted decisions / constitutional canon
├── universal instance substrate
│   └── identity edifice: iota → mote → trait → quirk → prodigal → exile → innate → portal → obelisk
├── modus modular composition
│   ├── moods: modularization methodologies
│   ├── masks: typed legitimate variation
│   └── reference-first recursive composition
├── typed segues
├── slots / attachments
├── rubric / cabal
├── kindred relationship methodology
├── explicit semantic owners
│   ├── niche: task governance
│   ├── opus: provider/model routing + ai execution
│   ├── palaver: conversation/workstation orchestration
│   ├── envoy: persona/voice/expression
│   ├── notary: verification/evidence admission
│   ├── pryme: authority interpretation
│   ├── pact: contracts/constraints/permissions
│   ├── coda: authorized durable mutation
│   ├── lore: canonical knowledge-memory jurisdiction
│   ├── scrybe: recall/context projection
│   ├── vault: custody/replay/recovery
│   ├── spyral: migration/evolution mechanics
│   ├── urge: candidate refinement
│   ├── lythe: deterministic derivation
│   ├── filament: projection execution
│   ├── dryve: delegated execution substrate
│   ├── shatter: controlled decomposition/fault isolation
│   ├── underscore: structural normalization/hidden support
│   └── carbon: generalized simulation
├── deterministic projections
├── savant-native application surfaces
└── reversible, evidence-aware evolution
```

The structural objective is not to centralize all behavior. It is to
make independently owned semantic substance reusable without
duplication. Containment, composition, relationship, authority,
transformation, runtime state, persistence, and projection remain
distinct axes even when they share common primitives.

## 22. v3.27 unresolved structural work

-   final authoritative Faculty catalog and the unique edifice for
    every Faculty remain incomplete unless stronger authority exists
    outside the emitted source bodies;
-   Modus masking and broadened Mood semantics are not yet universally
    executable across the runtime;
-   accepted Modus still references Coalesce while migration-canon
    material describes privileged historical composition layers as
    superseded, so reconciliation requires authority rather than
    inference;
-   Kindred compatibility/history around `kinship` remains separate from
    canonical `kindred` terminology;
-   Scyon focal ownership remains unresolved unless later accepted
    authority establishes it;
-   Atlas activation/frontend consolidation remains historical
    unfinished implementation work but is paused by newer user
    direction;
-   Filament vector rendering remains incomplete;
-   many current files were metadata-only in the newest compact dump, so
    their current bodies cannot be promoted from filesystem evidence
    into architectural claims;
-   universal owner-to-owner contracts, dependency/dependent
    introspection, canonical common primitives, and complete
    self-hosting lifecycle remain strategic implementation work rather
    than completed fact.

```{=html}
</details>
```

