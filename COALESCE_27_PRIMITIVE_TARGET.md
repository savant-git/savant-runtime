COALESCE — SLIVER POOL TARGET  Status: SUPERSEDED DESIGN AUTHORITY System: Savant Runtime Component: `prodigal:modus:coalesce` Owner: `exile:modus` Superseded target: `27 native Coalesce primitives` Superseding authority: `/root/savant-runtime/COALESCE_COMPOSITION_CONTRACT.md` Directive date: 2026-08-11  # 1. SUPERSESSION  The former target of:  `27 native Coalesce primitives`  is superseded.  The canonical future target is now:  `extensible Sliver Pool`  with each assembled application represented as an:  `Alloy`  containing:  `1–9 Slivers`  This file remains at its historical path so existing references, provenance, source-dump lineage, and migration tooling can continue to resolve it.  It MUST NOT be interpreted as authority for rebuilding Coalesce around exactly twenty-seven primitives.  ---  # 2. CANONICAL TERMINOLOGY  Coalesce is the application-composition system.  Alloy is an application assembled by Coalesce.  Sliver is a reusable primary application capability.  Sliver Pool is the canonical reusable capability pool from which Alloy Recipes select their constituent Slivers.  An Alloy may contain no more than nine primary Slivers.  ---  # 3. WHY THE 27-PIECE TARGET WAS SUPERSEDED  The twenty-seven-piece target correctly attempted to reduce the historical eighty-one-piece architecture.  Its remaining defect was that it still fixed the reusable vocabulary to an arbitrary cardinality.  The newer architecture instead constrains the composition where complexity matters:  `<= 9 Slivers per Alloy`  while allowing the reusable Sliver Pool to evolve according to actual capability requirements.  The pool therefore has:  - no arbitrary fixed size; - no requirement to reach twenty-seven; - no requirement to remain at twenty-seven; - no permission to grow merely to increase apparent capability.  The optimization target is:  **minimum pool redundancy + maximum compositional coverage + <=9 Slivers per Alloy.**  ---  # 4. PRESERVED PRINCIPLES FROM THE 27-PRIMITIVE DESIGN  The following principles remain valid and are preserved:  1. Coalesce belongs beneath Modus. 2. Coalesce is `prodigal:modus:coalesce`. 3. Coalesce is application-composition infrastructure. 4. Coalesce must not become a new ontology. 5. Coalesce must not become an Exile. 6. Exiles remain external capability owners. 7. Exiles may be called but not embedded. 8. Prodigal instances may participate where their contracts permit. 9. Quirk instances may participate where their contracts permit. 10. configuration should replace unnecessary component proliferation; 11. parameterization should replace near-duplicate components; 12. adapters should normalize incompatible boundaries; 13. providers should preserve external capability ownership; 14. projections should remain separate from application semantics; 15. typed segues should expose composition relationships; 16. deterministic recipes should define composition; 17. lineage and provenance must survive migration; 18. historical implementation must remain recoverable; 19. domain data must not become generic Coalesce substance; 20. Filament integration must remain compatible unless superseded.  These principles transfer directly into the Sliver architecture.  ---  # 5. HISTORICAL 81-PIECE IMPLEMENTATION  The historical eighty-one-piece implementation remains verified historical implementation evidence.  It demonstrated:  - large reusable capability pools; - recipe-driven composition; - heterogeneous application behavior; - Filament projection; - composition digests; - neutral data projection; - generic capability extraction.  It MUST NOT be discarded before every useful historical capability receives an explicit disposition.  Historical piece dispositions may include:  - canonical Sliver; - merged into canonical Sliver; - Sliver parameter; - Sliver mode; - Prodigal instance; - Quirk instance; - adapter; - provider; - typed segue; - projection; - engine behavior; - compatibility layer; - superseded; - historical only.  ---  # 6. NO DIRECT 81-TO-27 MIGRATION  The obsolete migration:  `81 pieces -> 27 primitives`  MUST NOT be implemented as the final architecture.  The new migration is:  `historical 81-piece capability inventory`  → capability normalization  → duplication removal  → lower-order substance extraction  → generic capability classification  → Sliver Pool  → Alloy Recipes containing <=9 Slivers.  Twenty-seven may occur coincidentally as a temporary pool size.  It has no canonical significance.  ---  # 7. SLIVER ADMISSION  A canonical Sliver is admitted only when it provides a distinct reusable application capability.  Admission requires:  - stable semantic identity; - reusable capability; - explicit contract; - declared inputs; - declared outputs; - configuration schema; - declared dependencies; - declared effects; - typed attachment points; - lineage; - provenance; - compatibility metadata; - no existing equivalent primitive.  Before admitting a new Sliver, Coalesce MUST test whether the variation can instead be expressed through:  - configuration; - parameterization; - Prodigal instance; - Quirk instance; - adapter; - provider; - typed segue; - projection.  ---  # 8. SLIVER POOL SIZE  There is no canonical Sliver Pool cardinality.  Pool size is an outcome of capability normalization.  The pool should shrink when capabilities are redundant.  The pool may grow when genuinely new reusable capabilities are required.  The governing metric is not number of Slivers.  The governing metric is:  **how much useful application space can be covered by compositions of nine or fewer Slivers.**  ---  # 9. ALLOY CAP  Each Alloy contains:  `1–9 Sliver instances`  Nine is the maximum primary composition count.  An Alloy exceeding nine Slivers is invalid unless later authority explicitly supersedes this invariant.  The cap MUST NOT be bypassed through:  - wrapper Slivers containing hidden primary Slivers; - treating another Alloy as a Sliver; - recursive composition tricks; - anonymous component bundles.  If one application legitimately exceeds the coherent nine-Sliver boundary, use multiple federated Alloys.  ---  # 10. MINIMAL SUFFICIENT COMPOSITION  Coalesce should select the smallest sufficient compatible Sliver set.  Selection objective:  1. satisfy every required capability; 2. remain at or below nine Slivers; 3. minimize semantic overlap; 4. reuse canonical lower-order elements; 5. preserve explicit ownership; 6. minimize hidden dependencies; 7. minimize unnecessary external dependencies; 8. maximize deterministic behavior.  ---  # 11. CAPABILITY COVERAGE  Every canonical Sliver SHOULD publish machine-readable capability identifiers.  Coalesce SHOULD derive:  `required capability -> compatible Sliver candidates`  from authoritative Sliver manifests.  The capability coverage index is a projection.  It is not separately maintained authority.  ---  # 12. CONSTRAINED COMPOSITION PLANNING  Automatic Alloy planning should be treated as a constrained selection problem.  Input:  - requested capabilities; - available Sliver Pool; - compatibility graph; - runtime constraints; - provider availability; - authority constraints; - projection requirements.  Constraints include:  - maximum nine Slivers; - contract compatibility; - required dependencies; - prohibited relationships; - authorized external calls; - runtime compatibility.  Output:  - proposed Alloy Recipe; - selected Slivers; - adapters; - external requirements; - unresolved capabilities; - deterministic selection metadata.  ---  # 13. IMPLEMENTATION TECHNIQUES  Suitable implementation techniques include:  - deterministic greedy set-cover for simple composition; - branch-and-bound for bounded selection; - SAT/SMT when constraint complexity materially warrants it; - integer programming when optimization materially warrants it; - graph traversal for dependency resolution; - topological sorting for execution planning; - JSON Schema for portable contracts; - Pydantic for typed Python validation; - content hashing for composition identity.  No solver or library becomes Coalesce authority.  ---  # 14. OPTIONAL DEPENDENCIES  Potential dependencies may include:  - `pydantic` - `jsonschema` - `networkx` - `python-constraint` - `z3-solver` - `ortools`  Admission is conditional.  Do not install all of them by default.  A dependency is justified only when existing Savant or standard-library primitives are insufficient for the bounded implementation task.  The preferred initial planner should remain dependency-light.  ---  # 15. CAPABILITY MANIFEST  A Sliver capability manifest SHOULD expose at minimum:  ```text id version status provides requires optional conflicts ports effects configuration_schema dependencies attachments provenance lineage ` 
Derived information should be projected rather than manually duplicated.
  
# 16. ALLOY RECIPE
 
An Alloy Recipe SHOULD expose:
 `alloy_id recipe_version slivers instances parameters segues adapters providers external_calls projection policy ` 
The Recipe references canonical Slivers.
 
It does not copy Sliver implementation.
  
# 17. COMPOSITION DIGEST
 
A deterministic composition digest SHOULD be generated from semantic Recipe inputs.
 
The digest enables:
 
 
- replay;
 
- cache identity;
 
- migration comparison;
 
- provenance;
 
- deterministic materialization;
 
- semantic diffing.
 

  
# 18. INSTANCE-FIRST REALIZATION
 
Canonical realization:
 
`Sliver definition`
 
→ `Sliver instance`
 
→ `Alloy Recipe`
 
→ `materialized Alloy`
 
Never prefer:
 
`Sliver definition`
 
→ copied implementation
 
→ Alloy-specific fork.
  
# 19. LOWER-ORDER REUSE
 
Prodigal and Quirk instances remain valid lower-order reusable substance.
 
A Sliver may compose them when their contracts permit.
 
They do not count toward the nine-Sliver primary composition cap.
 
They MUST remain independently graph-addressable.
 
Their existence MUST NOT be concealed as anonymous Sliver implementation when they retain independent identity.
  
# 20. EXILE BOUNDARY
 
An Exile:
 
 
- cannot become a Sliver;
 
- cannot be embedded inside an Alloy;
 
- cannot have its implementation copied into an Alloy;
 
- cannot have its authority transferred to Coalesce.
 

 
An Alloy may call an Exile through an authorized interface.
 
Canonical relationship:
 
`Alloy -> Sliver -> authorized call -> Exile`
  
# 21. FILAMENT
 
Filament remains a projection/presentation integration path where current verified implementation requires it.
 
Coalesce determines composition.
 
Filament projects composition.
 
Neither subsumes the other.
 
Historical integration around:
 
`exile:filament`
 
and:
 
`prodigal:modus:coalesce`
 
must remain compatible during migration unless stronger authority supersedes that relationship.
  
# 22. SOURCE APPLICATION DECOMPOSITION
 
When an application is supplied for conversion to Coalesce:
 
 
1. inspect the application's useful behaviors;
 
2. distinguish domain data from generic functionality;
 
3. identify existing Slivers;
 
4. identify reusable Prodigal/Quirk instances;
 
5. identify required adapters/providers;
 
6. identify capability gaps;
 
7. create a new Sliver only when no existing primitive can express the capability;
 
8. create the Alloy Recipe;
 
9. validate <=9 Slivers;
 
10. project the Alloy.
 

 
Do not reproduce source application architecture merely because it exists.
  
# 23. DATA NEUTRALITY
 
Source application data is evidence/input.
 
It MUST NOT become generic Coalesce authority.
 
Correct flow:
 
`source data`
 
→ authorized adapter
 
→ neutral projection
 
→ Alloy composition.
  
# 24. SLIVER DIFFERENTIAL
 
Each canonical Sliver should contribute materially distinct application functionality.
 
The pool should maximize:
 
 
- orthogonality;
 
- reuse;
 
- configurability;
 
- compatibility;
 
- compositional leverage.
 

 
The pool should minimize:
 
 
- duplicate functionality;
 
- source-app specialization;
 
- hardcoded schemas;
 
- hidden coupling.
 

  
# 25. POOL NORMALIZATION
 
Coalesce SHOULD support deterministic analysis for:
 
 
- exact duplicates;
 
- semantic near-duplicates;
 
- obsolete capabilities;
 
- source-specific Slivers;
 
- excessive fragmentation;
 
- capabilities that should become parameters;
 
- capabilities that should become adapters;
 
- capabilities already owned lower in Savant.
 

 
Normalization produces proposals.
 
It does not silently mutate accepted Slivers.
  
# 26. COMPATIBILITY GRAPH
 
Sliver relationships SHOULD include typed edges such as:
 `requires conflicts_with compatible_with substitutes_for adapts decorates projects_to supersedes derived_from ` 
Compatibility should not depend on filesystem proximity or import success alone.
  
# 27. PORT MODEL
 
Slivers SHOULD expose explicit semantic ports.
 
Typical ports:
 `input output state events commands queries selection projection provider ` 
Bindings are declared in the Alloy Recipe.
  
# 28. EFFECT MODEL
 
Every Sliver SHOULD declare relevant effects.
 
Potential effects:
 `filesystem.read filesystem.write network process.execute database.read database.write credential.access external.mutation ` 
Selecting a Sliver does not automatically grant effects.
 
Applicable Savant authority must permit them.
  
# 29. COMPOSITION RECEIPT
 
Materialization SHOULD emit a non-authoritative receipt containing:
 `alloy recipe composition_digest sliver_ids versions instance_ids configuration_digests dependency_summary projection warnings degraded_capabilities ` 
This preserves auditability without storing duplicate semantic authority.
  
# 30. SEMANTIC DIFF
 
Coalesce SHOULD eventually compare Recipes semantically.
 
A Recipe diff should identify:
 
 
- Sliver addition/removal;
 
- version change;
 
- parameter change;
 
- adapter change;
 
- segue change;
 
- provider change;
 
- projection change.
 

 
Line-oriented source diff is insufficient as the sole composition comparison.
  
# 31. STATIC VALIDATION
 
Before execution, Coalesce SHOULD validate:
 
 
- Alloy contains 1–9 Slivers;
 
- all Sliver IDs resolve;
 
- capability requirements are satisfied;
 
- contracts match;
 
- no forbidden conflicts exist;
 
- required dependencies resolve;
 
- no Exile is embedded;
 
- typed segues resolve;
 
- configuration schemas validate;
 
- graph relationships remain explicit.
 

  
# 32. RUNTIME VALIDATION
 
Runtime validation should be limited to facts unavailable statically, including:
 
 
- provider availability;
 
- runtime permissions;
 
- live external capability availability;
 
- dynamic input constraints.
 

 
Do not repeat static validation without reason.
  
# 33. DETERMINISTIC PLANNING
 
Equivalent semantic inputs SHOULD select equivalent Alloy Recipes under the same:
 
 
- Sliver Pool version;
 
- compatibility graph;
 
- policy;
 
- runtime availability state.
 

 
When multiple equivalent valid Recipes exist, deterministic tie-breaking must be explicit.
  
# 34. HOT RECOMPOSITION
 
Coalesce MAY permit Alloy Sliver membership to change during runtime.
 
Material membership change produces a new composition state.
 
Recomposition should be atomic:
 
 
1. construct candidate;
 
2. validate candidate;
 
3. initialize candidate;
 
4. switch active composition;
 
5. retire old composition.
 

 
Failure preserves the previous valid Alloy.
  
# 35. FEDERATION
 
Multiple Alloys MAY cooperate when one coherent application domain cannot fit inside nine primary Slivers.
 
Federation uses explicit:
 
 
- typed segues;
 
- events;
 
- commands;
 
- queries;
 
- providers;
 
- shared projections.
 

 
Federation does not collapse multiple Alloy identities into one.
  
# 36. HISTORICAL RECIPE PRESERVATION
 
Historical Recipes remain immutable evidence.
 
Do not edit old Recipes to fit Sliver terminology.
 
Migration creates:
 
`historical Recipe`
 
→ explicit migration record
 
→ `new Alloy Recipe`.
  
# 37. MIGRATION CLASSIFICATION
 
Every historical native piece must receive exactly one explicit migration disposition before retirement:
 `sliver merge_into_sliver parameter mode prodigal_instance quirk_instance adapter provider segue projection engine compatibility superseded historical_only ` 
No silent deletion.
  
# 38. MIGRATION ORDER
 
The future bounded migration should proceed in this order:
 
 
1. freeze current verified Coalesce implementation;
 
2. inventory historical pieces;
 
3. identify known dependencies and dependents;
 
4. classify historical pieces;
 
5. identify existing lower-order replacements;
 
6. normalize capabilities;
 
7. define candidate Sliver Pool;
 
8. validate capability coverage;
 
9. map current Recipes to candidate Alloy Recipes;
 
10. add required compatibility adapters;
 
11. validate Filament integration;
 
12. migrate one representative Alloy;
 
13. compare against previous verified behavior;
 
14. migrate remaining necessary Recipes;
 
15. preserve historical implementation;
 
16. retire obsolete runtime paths only after dependents resolve.
 

  
# 39. NO BIG-BANG REWRITE
 
Do not replace the entire historical implementation at once.
 
Prefer compatibility-routed migration.
 
The existing implementation remains the baseline until a candidate Sliver-based path passes its bounded acceptance checks.
  
# 40. COMPATIBILITY
 
Compatibility may include:
 
 
- historical piece ID aliases;
 
- Recipe adapters;
 
- projection adapters;
 
- API adapters;
 
- Filament compatibility;
 
- legacy trace translation.
 

 
Compatibility infrastructure exists to preserve behavior during migration.
 
It MUST NOT become permanent duplicate semantic authority.
  
# 41. TRACE LINEAGE
 
Future traces should identify:
 
 
- Alloy;
 
- Recipe;
 
- Sliver;
 
- Sliver instance;
 
- canonical lower-order instances;
 
- configuration digest;
 
- external providers;
 
- projection;
 
- authority effect.
 

 
Historical traces remain valid historical evidence.
  
# 42. AUTHORITY EFFECT
 
Default Coalesce authority effect remains:
 
`none`
 
Coalesce composes application capability.
 
It does not gain authority-changing power from composition.
 
Authority-changing operations must remain owned and authorized by the relevant external capability.
  
# 43. SECURITY
 
Coalesce MUST preserve:
 
 
- least capability;
 
- explicit effects;
 
- explicit external calls;
 
- explicit credential ownership;
 
- explicit mutation authority;
 
- explicit provider ownership.
 

 
Composition is not permission escalation.
  
# 44. SLIVER TRUST STATE
 
A Sliver MAY expose lifecycle/trust state:
 `candidate evaluated accepted active deprecated superseded quarantined external ` 
Historical state remains attributable.
  
# 45. CHAMPION / CHALLENGER
 
Where two candidate Slivers provide substantially equivalent capability, Coalesce MAY use:
 
 
- accepted champion;
 
- candidate challenger.
 

 
A challenger may be evaluated without replacing the champion.
 
Supersession requires evidence.
  
# 46. SHADOW MIGRATION
 
Candidate Alloy Recipes MAY be materialized in shadow mode against the same neutral inputs.
 
This supports behavior comparison before cutover.
 
Shadow success alone does not establish architectural authority.
  
# 47. COVERAGE BENCHMARK
 
The Sliver Pool SHOULD eventually be evaluated against a representative corpus of application capability requirements.
 
Primary metric:
 
**fraction of representative applications expressible using <=9 Slivers.**
 
Secondary metrics:
 
 
- average selected Sliver count;
 
- unresolved capability gaps;
 
- duplicate capability count;
 
- adapter burden;
 
- external dependency burden;
 
- composition stability.
 

 
This is more informative than measuring raw Sliver count.
  
# 48. GAP ANALYSIS
 
When a requested Alloy cannot be built within nine Slivers, classify the reason:
 `missing_capability excessive_fragmentation contract_incompatibility missing_adapter provider_unavailable authority_conflict projection_gap multi_alloy_required ` 
The remedy should be the smallest justified architectural change.
  
# 49. ADVANCED TARGETS
 
The Sliver migration architecture accepts the following future enhancements:
 
 
1. deterministic capability indexing;
 
2. automatic minimal-set planning;
 
3. schema-validated manifests;
 
4. compatibility graphs;
 
5. semantic Recipe linting;
 
6. semantic Recipe diff;
 
7. deterministic composition digests;
 
8. composition receipts;
 
9. shadow materialization;
 
10. transactional recomposition;
 
11. capability gap detection;
 
12. redundancy detection;
 
13. Sliver equivalence classes;
 
14. champion/challenger evolution;
 
15. dependency-aware execution;
 
16. incremental recomputation;
 
17. safe parallel execution;
 
18. content-addressed immutable artifacts;
 
19. declarative effect manifests;
 
20. capability-based security gating;
 
21. provider late binding;
 
22. resource budgets;
 
23. degraded-mode projection;
 
24. headless Alloy execution;
 
25. multi-projection Alloy output;
 
26. accessibility-aware projection contracts;
 
27. visual Recipe projection;
 
28. natural-language Recipe proposal;
 
29. Alloy federation;
 
30. coverage benchmarking.
 

 
These are implementation targets only when required by bounded tasks.
 
They do not authorize uncontrolled infrastructure expansion.
  
# 50. DEPENDENCY POLICY
 
External libraries remain optional implementation primitives.
 
Do not install dependencies merely because they are mentioned in architecture.
 
Before adding one, verify that it materially improves the current implementation.
 
Potential future candidates:
 
 
- Pydantic for Python contract validation;
 
- JSON Schema tooling for portable contracts;
 
- NetworkX for graph analysis;
 
- Z3 or OR-Tools for advanced constraint selection only when simpler deterministic algorithms prove insufficient.
 

 
Standard-library implementation is preferred when it remains clear and sufficient.
  
# 51. PLANNER STARTING POINT
 
The first production Alloy planner SHOULD be simple.
 
Preferred baseline:
 
 
1. normalize required capability IDs;
 
2. reject invalid Slivers;
 
3. score capability coverage;
 
4. greedily select the Sliver with greatest uncovered capability gain;
 
5. apply compatibility constraints;
 
6. stop when all requirements are covered;
 
7. reject if more than nine are required;
 
8. deterministically break ties by stable identity.
 

 
Only adopt heavier constraint tooling if evidence demonstrates a limitation.
  
# 52. SLIVER POOL DISCOVERY
 
The canonical Sliver registry, not filename scanning, should establish available Slivers.
 
Filesystem discovery may assist diagnostics.
 
Filesystem presence does not establish Sliver authority.
  
# 53. PROJECTED INDICES
 
Derived indices may include:
 
 
- capability index;
 
- compatibility matrix;
 
- dependency ordering;
 
- Recipe search;
 
- usage ranking;
 
- coverage report.
 

 
These should be deterministically projected from canonical manifests.
 
Do not hand-maintain duplicate authority.
  
# 54. ENGINE BEHAVIOR
 
Behavior universally required for Coalesce itself should remain engine behavior instead of consuming a Sliver slot.
 
Likely engine responsibilities include:
 
 
- Recipe parsing;
 
- Sliver resolution;
 
- contract validation;
 
- count enforcement;
 
- binding;
 
- lifecycle coordination;
 
- composition digest;
 
- receipt generation.
 

 
Only application-facing capability belongs in Slivers.
  
# 55. SLIVER SLOT DISCIPLINE
 
Do not waste Sliver slots on infrastructure every Alloy necessarily requires.
 
The nine slots represent application capability composition.
 
Universal Coalesce infrastructure belongs to Coalesce.
  
# 56. APPLICATION-SPECIFIC FEATURES
 
An application-specific behavior should first be tested against existing generic Slivers.
 
If generic representation is possible through configuration, do that.
 
New source-specific Slivers are strongly disfavored.
  
# 57. REUSE TEST
 
Before creating a Sliver, ask:
 
**Could this capability reasonably be used in at least one materially different Alloy?**
 
If no, prefer configuration or application-specific data unless the capability cannot be modeled safely any other way.
  
# 58. COMPOSITION STABILITY
 
Changing irrelevant input metadata MUST NOT alter selected Slivers.
 
Selection should react only to semantic capability requirements and explicit policy/runtime constraints.
  
# 59. RECIPE VERSIONING
 
Accepted Recipe versions are immutable.
 
A changed Sliver set, materially changed configuration, or materially changed contract binding produces a new Recipe version.
  
# 60. SLIVER VERSIONING
 
Sliver versions should distinguish:
 
 
- implementation-only change;
 
- backward-compatible contract extension;
 
- semantic contract change.
 

 
Historical Recipe interpretation must remain stable.
  
# 61. OPTIONAL CAPABILITY
 
An Alloy may declare optional capabilities.
 
Failure to satisfy optional capability may produce explicit degraded state without invalidating the Alloy.
 
Required capability failure invalidates composition.
  
# 62. FAILURE ISOLATION
 
A failed optional Sliver operation should not corrupt unrelated Sliver state.
 
Failure boundaries should preserve a coherent Alloy whenever possible.
  
# 63. CACHING
 
Composition plans may be cached by semantic digest.
 
Cache entries are invalidated by relevant changes to:
 
 
- required capabilities;
 
- Sliver Pool version;
 
- compatibility graph;
 
- policy;
 
- availability state.
 

 
Caches are non-authoritative.
  
# 64. INCREMENTAL EXECUTION
 
Dependency structure should permit unrelated Sliver results to remain valid when only one branch of an Alloy changes.
 
Avoid global recomputation where semantics permit incremental update.
  
# 65. PRESENTATION INDEPENDENCE
 
Alloy identity remains independent from browser framework.
 
The same Recipe should be able to support multiple projections where appropriate.
 
React, HTML, terminal, API, or native code are implementation/projection choices.
  
# 66. HEADLESS REPRESENTATION
 
A representative Alloy migration SHOULD prove that core application semantics can execute or be inspected without requiring browser rendering.
 
This prevents the projection from becoming composition authority.
  
# 67. FILAMENT ACCEPTANCE
 
Where Filament remains the selected projection owner, migration acceptance requires one focused check proving:
 
`Alloy Recipe -> Coalesce materialization -> Filament projection`
 
without transferring composition authority into Filament.
  
# 68. CURRENT SOURCE-DUMP FINDINGS
 
The newest admitted source dump still contains:
 
 
- historical eighty-one-piece Coalesce implementation evidence;
 
- a later twenty-seven-native-primitive target;
 
- Coalesce ownership under Modus;
 
- explicit permission for Prodigal and Quirk reuse;
 
- explicit prohibition against Exile constituent composition;
 
- Recipe-based deterministic composition;
 
- Filament projection integration;
 
- composition-digest behavior;
 
- neutral data normalization;
 
- migration and compatibility requirements.
 

 
The current user directive supersedes only the fixed twenty-seven-piece target and related cardinality assumptions.
 
The preserved principles above remain applicable. 
  
# 69. SUPERSEDED STATEMENTS
 
The following statements are no longer authoritative:
 
`Coalesce must contain exactly 27 canonical native pieces.`
 
`The final migration target is 3 families × 9 primitives.`
 
`Future migration completion requires exactly 27 native pieces.`
 
They are replaced with:
 
`Coalesce maintains an extensible canonical Sliver Pool.`
 
`Each Alloy contains 1–9 Slivers.`
 
`Migration completion depends on functional coverage, compatibility, lineage, and bounded composition—not total pool cardinality.`
  
# 70. MIGRATION COMPLETION CONDITION
 
The Sliver migration is complete when:
 
 
1. historical Coalesce behavior has explicit disposition;
 
2. canonical Sliver definitions exist;
 
3. Sliver Pool capability coverage is machine-readable;
 
4. no required historical behavior is silently lost;
 
5. representative historical Recipes can be mapped to Alloy Recipes;
 
6. every Alloy contains <=9 Slivers;
 
7. Prodigal and Quirk reuse replaces unnecessary native duplication;
 
8. Exile embedding is rejected;
 
9. authorized Exile calls remain functional;
 
10. Recipe compilation/materialization is deterministic;
 
11. composition digest remains available;
 
12. lineage and provenance survive migration;
 
13. compatibility for known dependents is explicit;
 
14. Filament integration remains functional where still required;
 
15. one representative complex Alloy materializes correctly;
 
16. browser/API projection remains functional where required;
 
17. source-domain data remains outside generic Sliver substance;
 
18. historical eighty-one-piece implementation remains recoverable;
 
19. obsolete twenty-seven-piece assumptions no longer govern runtime selection;
 
20. no known blocker prevents additional Alloys from being composed from the same Sliver Pool.
 

 
Once these conditions pass, STOP.
  
# 71. FINAL TARGET
 
The canonical future architecture is:
 
`Coalesce`
 
→ `Sliver Pool`
 
→ capability requirements
 
→ smallest sufficient compatible selection
 
→ `1–9 Sliver instances`
 
→ typed bindings
 
→ Alloy Recipe
 
→ Alloy
 
→ projection.
 
The pool is extensible.
 
The Alloy is bounded.
 
The capability space emerges through composition.
 
The twenty-seven-piece target is historical authority that has now been explicitly superseded.
