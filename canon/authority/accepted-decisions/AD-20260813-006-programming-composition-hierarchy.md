nano /root/savant-runtime/authority/accepted-decisions/AD-20260813-006-programming-composition-hierarchy.md ` `# AD-20260813-006 — Canonical Programming Composition Hierarchy  Status: accepted Accepted: 2026-08-13 Authority: current user directive Scope: Savant programming composition Supersedes: - section 3, "Canonical content hierarchy", of AD-20260806-002 where inconsistent - older programming/content hierarchies where inconsistent - module/service/suite/estate as programming hierarchy levels  ## 1. Decision  Savant programming substance is recursively instance-composed.  The canonical ascending programming hierarchy is:  ```text character → line → segment → snippet → script → engine → subsystem → system → application ` 
These nine levels are semantic composition levels.
 
They do not require nine unique physical storage models.
 
Every level uses the universal instance model.
 
## 2. Definitions
 
### character
 
Atomic textual or symbolic source unit.
 
### line
 
Ordered composition of characters forming one source line.
 
### segment
 
Ordered, bounded composition of related lines representing a coherent local code region.
 
A segment is smaller than a snippet.
 
A segment may represent:
 
 
- a declaration region;
 
- an expression region;
 
- a control-flow region;
 
- a callable body region;
 
- a configuration region;
 
- another locally coherent sequence of lines.
 

 
Segment boundaries are semantic, not merely blank-line boundaries.
 
### snippet
 
Reusable bounded composition of one or more segments.
 
A snippet owns one coherent reusable implementation responsibility.
 
A snippet is the fundamental reusable programming substance.
 
### script
 
Executable or interpretable composition of snippets and the typed segues connecting them.
 
A script is not authoritative merely because it exists as a file.
 
### engine
 
Coherent executable composition of scripts implementing one bounded operational mechanism.
 
### subsystem
 
Composition of engines implementing one bounded internal capability domain.
 
### system
 
Composition of subsystems implementing one independently coherent operational domain.
 
### application
 
Operable composition of systems presented through one bounded application identity.
 
## 3. Non-hierarchy programming structures
 
The following remain valid programming concepts but are not levels in this hierarchy:
 
 
- token
 
- identifier
 
- literal
 
- expression
 
- statement
 
- block
 
- function
 
- method
 
- callable
 
- class
 
- interface
 
- contract
 
- schema
 
- adapter
 
- command
 
- test
 
- migration
 
- task
 
- receipt
 
- module
 
- service
 
- package
 
- library
 
- provider
 
- validator
 

 
They describe syntax, implementation roles, packaging, interfaces, runtime roles, or operational boundaries.
 
They must not silently become competing hierarchy levels.
 
## 4. Instance law
 
Every stable reusable programming element may be substantiated once as an instance.
 
Higher programming structures emerge through:
 
 
- composition;
 
- instance references;
 
- typed segues;
 
- parameterization;
 
- specialization;
 
- attachment;
 
- projection.
 

 
Canonical implementation substance must not be duplicated merely because it participates in multiple higher structures.
 
## 5. Segue law
 
Every transition between independently meaningful programming units is representable by a typed segue.
 
This includes transitions:
 
 
- between hierarchy levels;
 
- between sibling instances;
 
- between segments;
 
- between snippets;
 
- between scripts;
 
- between callables or functional regions when the transition itself has reusable or governable semantics.
 

 
A segue does not duplicate either endpoint.
 
A segue describes or implements the transition between them.
 
## 6. Projection law
 
Files are implementation projections unless explicitly authoritative.
 
A projected script should be reconstructible from:
 `character instances → line instances → segment instances → snippet instances → typed segues → script instance ` 
Higher programming projections recursively follow the same law.
 
## 7. Rubric and Cabal law
 
Rubrics continue to own executable implementation at the legitimate instance scope.
 
Cabals continue to hold genuinely shared implementation at the narrowest legitimate common scope.
 
Neither Rubric nor Cabal is a programming hierarchy level.
 
## 8. Compatibility
 
Existing physical modules, services, packages, libraries, files, classes, functions, and runtime APIs remain valid.
 
This decision does not require arbitrary renaming merely to match hierarchy terminology.
 
Classification changes before physical migration.
 
Physical migration requires dependency-safe implementation authority.
 
## 9. Historical preservation
 
Historical accepted decisions remain unchanged.
 
Where an earlier document states a conflicting programming hierarchy, this decision governs current interpretation.
 
Historical names remain evidence and lineage.
 
## 10. Completion condition
 
Programming hierarchy classification is canonical when all current programming-hierarchy canon resolves to:
 `character → line → segment → snippet → script → engine → subsystem → system → application ` ` Update the direct composition rule:  ```bash nano /root/savant-runtime/ontology/obelisks/segue/authority_graph/canon/SCRIPT_COMPOSITION_RULE.md ` `# SCRIPT COMPOSITION RULE  STATUS: CANON AUTHORITY: USER DIRECTIVE UPDATED: 2026-08-13 SUPERSESSION: AD-20260813-006  Scripts are not atomic.  Canonical programming composition is:  ```text character → line → segment → snippet → script → engine → subsystem → system → application ` 
A line is composed of characters.
 
A segment is a bounded coherent composition of lines.
 
A snippet is a reusable bounded composition of segments.
 
A script is an executable or interpretable composition of snippets and their typed segues.
 
An engine composes scripts around one bounded operational mechanism.
 
A subsystem composes engines around one bounded internal capability domain.
 
A system composes subsystems around one independently coherent operational domain.
 
An application composes systems into one operable application identity.
 
Every stable reusable level is instantiable.
 
Every higher level emerges through composition rather than duplication.
 
Every script projection must expose, directly or transitively:
 
 
- source character instances
 
- source line instances
 
- source segment instances
 
- source snippet instances
 
- source segues
 
- assembled script identity
 
- generated projection path
 
- lineage
 
- provenance
 
- dependencies
 
- dependents where known
 
- future extension slots
 

 
Files are projections unless explicitly authoritative.
 
The authoritative structure is the instance composition graph.
 
Transitions with independently meaningful semantics are represented through typed segues.
 
No hierarchy level requires a unique storage model.
 
Module, service, package, library, class, function, interface, contract, schema, adapter, provider, command, validator, test, migration, task, and receipt remain valid programming structures but are not competing levels in the canonical programming hierarchy.
 ` Update the projection rule:  ```bash nano /root/savant-runtime/ontology/obelisks/segue/authority_graph/canon/INSTANCE_PROJECTION_RULE.md ` `# INSTANCE PROJECTION RULE  STATUS: CANON AUTHORITY: USER DIRECTIVE UPDATED: 2026-08-13 SUPERSESSION: AD-20260813-006  Instances are authoritative where their governing authority declares them authoritative.  Files are projections unless explicitly marked as authority.  Canonical programming projection follows:  ```text character instances → line instances → segment instances → snippet instances → script instances → engine instances → subsystem instances → system instances → application instances ` 
Each higher level composes lower-level instances by reference.
 
A line instance composes character instances.
 
A segment instance composes line instances.
 
A snippet instance composes segment instances.
 
A script instance composes snippet instances and typed segues.
 
An engine instance composes script instances.
 
A subsystem instance composes engine instances.
 
A system instance composes subsystem instances.
 
An application instance composes system instances.
 
A projection must preserve enough information to identify:
 
 
- projection id
 
- source instance id
 
- source child instances
 
- source segues
 
- source policies
 
- authority state
 
- lineage
 
- provenance
 
- dependencies
 
- generated path
 
- future extension slots
 

 
Projected artifacts may be deleted and regenerated.
 
Deleting a projection must never delete its authoritative source instances.
 
Canonical substance must not be reconstructed from a projection when authoritative primitives remain available.
 
Instance chains may be superseded only through governing authority.
 ` Update the universal instance document. This also fixes its stale `shard/gate` identity terminology visible in the August 13 dump. 3  ```bash nano /root/savant-runtime/ontology/obelisks/segue/authority_graph/canon/UNIVERSAL_INSTANCE_STRUCTURE.md ` `# UNIVERSAL INSTANCE STRUCTURE  STATUS: CANON AUTHORITY: USER DIRECTIVE UPDATED: 2026-08-13 SUPERSESSION: AD-20260813-006  Every stable Savant element may be represented as an instance.  Every instance may compose other instances.  Every hierarchy level uses the same recursive structural model.  Files do not become primary architecture merely by existing.  Authority lives in authoritative primitives, instance relationships, segues, policies, lineage, provenance, and accepted governing decisions.  ## Programming hierarchy  ```text character → line → segment → snippet → script → engine → subsystem → system → application ` 
## Identity hierarchy
 `iota → mote → trait → quirk → prodigal → exile → innate → portal → obelisk ` 
## Universal properties
 
A stable instance supports, where applicable:
 
 
- identity
 
- kind
 
- type
 
- level
 
- version
 
- status
 
- authority
 
- lineage
 
- provenance
 
- dependencies
 
- dependents
 
- relationships
 
- composition
 
- segues
 
- capabilities
 
- projections
 
- extensions
 
- attachments
 
- future extensions
 

 
No hierarchy type receives a fundamentally different storage model.
 
Only semantics, authority, relationships, composition, and legitimate facilities differ.
 
A directory is not inherently the instance.
 
A file is not inherently the instance.
 
A projection is not inherently the instance.
 
Canonical substance exists once and is composed by reference wherever possible.
 ` Replace the stale recursive-composition document:  ```bash nano /root/savant-runtime/ontology/obelisks/segue/authority_graph/canon/RECURSIVE_COMPOSITION.md ` `# RECURSIVE COMPOSITION  STATUS: CANON AUTHORITY: USER DIRECTIVE UPDATED: 2026-08-13 SUPERSESSION: AD-20260813-006  Every stable Savant element is recursively composable.  Composition is instance-first.  Duplication is not composition.  Hierarchy describes semantic emergence.  It does not require a different architecture at every level.  ## Programming emergence  ```text character     ↓ line     ↓ segment     ↓ snippet     ↓ script     ↓ engine     ↓ subsystem     ↓ system     ↓ application ` 
## Identity emergence
 `iota     ↓ mote     ↓ trait     ↓ quirk     ↓ prodigal     ↓ exile     ↓ innate     ↓ portal     ↓ obelisk ` 
These are separate semantic axes.
 
They must not be collapsed into one synthetic hierarchy.
 
Programming structures may be owned by or attached to identity structures without becoming identity levels.
 
Identity structures may expose programming implementation without becoming programming levels.
 
Every level uses the universal instance model.
 
Transitions are represented through typed segues where the transition carries independently meaningful semantics.
 
No level introduces a unique storage model merely because of its level.
 
Only semantic responsibility, composition, authority, interfaces, relationships, and legitimate facilities change.
 ` Add the missing code-transition canon. This implements the specific idea that transitions inside code itself can be first-class rather than leaving snippets/functions as opaque monoliths.  ```bash nano /root/savant-runtime/ontology/obelisks/segue/authority_graph/canon/CODE_SEGUE_RULE.md ` `# CODE SEGUE RULE  STATUS: CANON AUTHORITY: USER DIRECTIVE ACCEPTED: 2026-08-13 DEPENDS_ON: AD-20260813-006  ## Core rule  Programming composition is segue-mediated wherever a transition possesses independently meaningful semantics.  Code units do not require artificial direct coupling when the relationship between them can be represented explicitly.  ## Valid endpoints  A code segue may connect:  - line → line - line → segment - segment → segment - segment → snippet - snippet → snippet - snippet → script - script → script - script → engine - engine → engine - engine → subsystem - subsystem → subsystem - subsystem → system - system → system - system → application  A segue may also connect functional structures such as:  - function → function - method → method - callable → callable - block → block - adapter → contract - provider → adapter - command → runtime - validator → subject - test → subject  These structures do not thereby become hierarchy levels.  ## Segue responsibilities  A code segue may encode:  - control transfer - data transfer - type conversion - contract adaptation - lifecycle transition - error transition - state transition - dependency boundary - compatibility boundary - normalization - serialization - deserialization - validation handoff - provider handoff - projection handoff - composition attachment  ## Segue identity  A stable reusable segue exposes:  - id - source - target - type - authority - lineage - provenance - dependencies - compatibility - contract - validation - extensions  ## Non-duplication law  A segue references its endpoints.  It does not duplicate them.  Reusable transition behavior is substantiated once and instanced wherever compatible.  ## Granularity law  Not every adjacency requires a materialized segue.  A segue becomes a stable instance when the transition itself requires identity, reuse, policy, validation, compatibility, observation, extension, or governance.  Pure language syntax remains syntax.  Savant must not create meaningless segue objects between every literal source line merely to satisfy structural aesthetics.  ## Projection  Projected code may render segue behavior as ordinary native source syntax.  The absence of a visible "segue" keyword in generated Python, JavaScript, shell, or another target language does not erase the underlying composition relationship.  Generated source remains a projection of the composition graph. ` 
Add the programming lexicon so the rest of the implemented programming vocabulary does not get accidentally promoted into competing hierarchy levels:
 `nano /root/savant-runtime/ontology/obelisks/segue/authority_graph/canon/PROGRAMMING_LEXICON_CANON.md ` `# PROGRAMMING LEXICON CANON  STATUS: CANON AUTHORITY: USER DIRECTIVE ACCEPTED: 2026-08-13 DEPENDS_ON: AD-20260813-006  ## Purpose  This document separates Savant's canonical programming hierarchy from orthogonal programming vocabulary already required by implementation.  A term may be structurally important without being a hierarchy level.  ## Canonical hierarchy terms  ### character  Atomic textual or symbolic source unit.  ### line  Ordered composition of characters occupying one logical source line.  ### segment  Bounded coherent composition of related lines.  ### snippet  Reusable bounded composition of one or more segments.  ### script  Executable or interpretable composition of snippets and their segues.  ### engine  Bounded operational mechanism composed from scripts.  ### subsystem  Bounded internal capability domain composed from engines.  ### system  Independently coherent operational domain composed from subsystems.  ### application  Operable application identity composed from systems.  ## Syntax terms  ### token  Language-level lexical unit recognized by a parser or tokenizer.  ### identifier  Token naming a language-level entity.  ### literal  Source representation of a value.  ### expression  Language construct evaluating to a value or result.  ### statement  Language construct expressing an executable or declarative action.  ### block  Language-defined grouping of statements or declarations.  These are syntax classifications, not Savant programming hierarchy levels.  ## Callable terms  ### function  Named or addressable callable implementation.  ### method  Callable bound through an object, class, or equivalent language construct.  ### callable  General executable invocation surface.  ### class  Language construct defining data and/or behavior according to the target language.  These may occur inside segments, snippets, scripts, or larger projections.  Their native-language boundaries do not override Savant composition identity.  ## Interface terms  ### interface  Declared interaction surface.  ### contract  Explicit requirements governing interaction between participants.  ### schema  Machine-validatable structural contract for data or configuration.  ### adapter  Compatibility mechanism translating one legitimate interface or representation into another.  ### provider  Implementation supplying a bounded capability through a defined interface.  ### validator  Mechanism evaluating a subject against explicit invariants or contracts.  These describe roles and boundaries rather than hierarchy levels.  ## Operational terms  ### command  Invocable user, operator, or machine-facing execution entrypoint.  ### test  Executable verification of behavior or invariants.  ### migration  Governed transition from one compatible state or representation to another.  ### task  Bounded unit of intended work.  ### receipt  Evidence artifact recording execution, validation, mutation, or another governed event.  These are operational structures, not programming hierarchy levels.  ## Packaging terms  ### file  Filesystem artifact.  A file may be a projection, evidence artifact, authority artifact, configuration, source representation, or another declared kind.  Filesystem presence alone establishes no authority.  ### module  Language or packaging boundary grouping implementation.  Module remains valid terminology but is not a canonical Savant programming hierarchy level.  ### package  Packaging or namespace unit containing related implementation.  ### library  Reusable implementation collection exposed for consumption.  ### service  Operational deployment or interface boundary.  Service remains valid terminology but is not a canonical Savant programming hierarchy level.  These describe packaging or deployment.  They do not compete with:  ```text character → line → segment → snippet → script → engine → subsystem → system → application ` 
## Savant composition terms
 
### instance
 
Stable realization of a reusable semantic element.
 
### segue
 
Typed relationship or transition connecting independently meaningful elements.
 
### Rubric
 
Executable implementation set owned by exactly one legitimate Savant element.
 
### Cabal
 
Genuinely shared implementation held at the narrowest legitimate common scope.
 
### projection
 
Reproducible representation derived from authoritative primitives.
 
### attachment
 
Extensible capability or relationship bound without replacing the subject.
 
### specialization
 
Compatible narrowing or extension of an existing canonical implementation.
 
### parameterization
 
Variation through explicit parameters rather than copied implementation.
 
## Classification law
 
One object may possess multiple orthogonal classifications.
 
For example, one projected Python file may simultaneously be:
 
 
- filesystem kind: file
 
- language packaging kind: module
 
- Savant projection kind: script projection
 
- implementation owner: Rubric
 
- hierarchy identity: script
 
- composed from: snippets
 
- containing native syntax: classes and functions
 

 
These classifications do not conflict because they describe different axes.
 
## Anti-duplication law
 
New terminology must not be created merely to rename an existing concept.
 
New programming hierarchy levels require explicit user authority.
 
Implementation roles must not silently become hierarchy levels through repeated filesystem use.
 
Historical terminology remains historical evidence unless current authority adopts it.
