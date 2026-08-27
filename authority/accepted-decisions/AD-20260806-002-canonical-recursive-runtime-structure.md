# AD-20260806-002 — Canonical Recursive Runtime Structure

Status: accepted  
Accepted: 2026-08-06  
Authority: current user directive  
Scope: complete Savant Runtime organization  
Implementation state: canon accepted; structural migration pending  
Supersedes: prior competing runtime-organization proposals where inconsistent  

## 1. Decision

Savant Runtime shall use a recursively nested, instance-composed architecture.

Canonical hierarchy substance remains nested.

Rubrics own executable implementation.

Cabals hold genuinely shared implementation at the narrowest legitimate scope.

Kindred expresses universal extended-family relationships.

Segues govern transitions between hierarchy levels.

Moods transform behavior.

Slots attach capabilities.

Authority governs durable meaning.

Projections expose reproducible views.

Receipts prove execution and validation.

No physical path becomes authority merely by existing.

## 2. Canonical identity hierarchy

Ascending emergence:

```text
iota
→ mote
→ trait
→ quirk
→ prodigal
→ exile
→ innate
→ portal
→ obelisk

Nested ownership:

obelisk
→ portal
→ innate
→ exile
→ prodigal
→ quirk
→ trait
→ mote
→ iota

mote supersedes shard only as the second identity level.
portal supersedes gate only as the eighth identity level.
Historical records remain unchanged.
Programming gates remain gates.
Uses of shard outside the identity-level meaning remain valid.

3. Canonical content hierarchy

character
→ line
→ snippet
→ script
→ module
→ service
→ application
→ suite
→ estate

Definitions:
character — atomic textual or symbolic unit.
line — ordered composition of characters.
snippet — reusable bounded composition of lines.
script — executable or interpretable composition of snippets.
module — reusable composition of scripts and interfaces.
service — independently bounded operational composition of modules.
application — independently operable composition of services.
suite — coordinated family of related applications.
estate — governed total environment containing suites and shared operational surfaces.

4. Universal instance law

Every stable Savant element is an instance.
An instance:
has stable identity independent of path;
binds one archetype;
may compose other instances;
may own Rubrics;
may consume Cabals;
may bind moods;
may expose slots;
may carry attachments;
may participate in Kindred;
may traverse Segues;
exposes authority, lineage, provenance, dependencies, and compatibility;
remains recursively composable;
remains independently reusable;
supports future extension without architectural replacement.
A directory is not the instance.
A file is not the instance.
A projection is not the instance.
Canonical substance exists once.

5. Universal capsule grammar

A stable element may materialize these facilities:
instance.yaml
authority/
rubric/
cabal/
kindred/
moods/
slots/
attachments/
segue/
projections/
observatory/
history/
tasks/
Facilities materialize only when used.
Empty structural folders are forbidden.
Inherited, referenced, or projected facilities need not be copied locally.

6. Rubric law

A Rubric is a complete executable implementation set owned by exactly one element.
Every executable implementation file resolves to exactly one Rubric owner.
Canonical Rubric form:

rubric/
├── rubric.cue
├── source/
├── contracts/
├── schemas/
├── adapters/
├── commands/
├── tests/
├── migrations/
├── tasks/
└── receipts/

The nine Rubric facilities are:
source
contracts
schemas
adapters
commands
tests
migrations
tasks
receipts
rubric.cue is the Rubric declaration and is not counted as a facility folder.
Rubric rules:
implementation remains with its semantic owner;
internal reuse does not justify Cabal promotion;
one Rubric may contain reusable internal components;
a Rubric never spans unrelated owners;
public entrypoints declare contracts;
commands remain thin;
tests remain beside their Rubric;
durable actions emit receipts;
environment and dependencies are declared reproducibly;
ambiguous ownership fails validation.

7. Cabal law

A Cabal is genuinely shared implementation placed at the narrowest common semantic scope containing all legitimate consumers.
Canonical Cabal form:

cabal/
├── cabal.cue
├── members/
├── contracts/
├── schemas/
├── adapters/
├── tests/
├── compatibility/
├── lineage/
├── tasks/
└── receipts/

A Cabal may be promoted only after satisfying all nine laws:
Chorus — independent reuse by multiple owners.
Commons — no single consumer owns its meaning.
Covenant — stable declared interface.
Equinox — consumer-neutral implementation.
Gauntlet — verification against every active consumer.
Distillate — actual duplicated substance is removed.
Severance — no concealed consumer coupling.
Cascade — acyclic dependency direction.
Bridge — compatibility remains intact during promotion.
Canonical qualification:

qualification:
  chorus: confirmed
  commons: confirmed
  covenant: confirmed
  equinox: confirmed
  gauntlet: confirmed
  distillate: confirmed
  severance: confirmed
  cascade: confirmed
  bridge: confirmed

Anticipated reuse is insufficient.
Shared placement never overrides semantic ownership.
A Cabal rises only as high as proven reuse requires.

8. Segue law

A Segue is a first-class governed transition between adjacent hierarchy levels.
A Segue:
joins a parent level to its child level;
may provide transition-scope Cabals;
may expose adapters, contracts, projections, and policies;
may govern admissible transition behavior;
may be both child-facing and parent-facing;
never duplicates endpoint substance;
never becomes a false hierarchy child.
Shared hierarchy infrastructure belongs under the correct level Segue.
The ontology root contains hierarchy roots only.

9. Kindred law

Kindred is Savant’s universal extended-family topology.
Kindred replaces shallow parent-child interpretation with typed, recursively derivable family relationships.
Relations are not toggles.
Every relation is an addressable edge instance.

9.1 Canonical Kindred trees

Exactly nine Kindred trees exist:
structural
semantic
rubric
authority
composition
dependency
provenance
succession
compatibility
Runtime state is projected across relevant trees.
Historical state is expressed through immutable lineage, provenance, succession, and receipts.

9.2 Canonical relation families

Exactly nine relation families exist:
Descent
Fraternity
Collateral
Union
Guardianship
Adoption
Composition
Succession
Affinity

9.3 Family vocabulary

Kindred supports, without limitation:

parent
mother
father
child
daughter
son
sibling
sister
brother
grandparent
grandmother
grandfather
grandchild
granddaughter
grandson
aunt
uncle
pibling
niece
nephew
nibling
cousin
spouse
wife
husband
partner
guardian
ward
adoptive-parent
adoptive-child
foster-parent
foster-child
step-parent
step-child
ancestor
descendant
predecessor
successor
mentor
protege
sponsor
beneficiary
composer
constituent

pibling means a parent’s sibling.
nibling means a sibling’s child.

Gendered and non-gendered terms resolve to the same underlying relation class when authoritative role data permits.
Kindred never guesses gender, role, direction, or inverse.

9.4 Nine-coordinate relation vector

Every resolved relation exposes:

K(
  generation,
  collateral,
  affinity,
  authority,
  dependency,
  composition,
  temporal,
  provenance,
  compatibility
)

Intrinsic coordinates:
generation
collateral
affinity
Contextual coordinates:
authority
dependency
composition
temporal
provenance
compatibility
Unknown coordinates remain null.
Contextual coordinates are derived from graph evidence whenever possible.
No coordinate is manually invented.

9.5 Edge requirements

Every Kindred edge exposes:

id
subject
object
tree
family
relation
inverse
directness
generation
collateral
affinity
authority
dependency
composition
temporal
provenance
compatibility
basis
derivation
authority_state
lineage
valid_from
valid_until
confidence
conflicts
status

Direct authoritative edges may be stored.
Derived relations are projected from supporting edges.
Derived relations store derivation receipts rather than duplicate endpoint substance.

9.6 Deterministic derivation examples

parent + parent
→ grandparent

parent + sibling
→ pibling, aunt, or uncle

sibling + child
→ nibling, niece, or nephew

parent + sibling + child
→ cousin

accepted succession chain
→ ancestor or descendant

shared authoritative ancestor
→ sibling or semantic kin

10. Mood law

There are exactly nine canonical moods:
anima
weld
kiln
graft
aria
mantle
fulcrum
echelon
ascent
Moods are operators.
Moods are not hierarchy levels.
Moods do not determine physical placement.
Canonical mood definitions exist once in the Modus-owned Rubric.
Elements expose bindings, parameters, combinations, lineage, provenance, projections, and receipts.
Exactly two mood applications participate in one combination instance.
Ordered combinations are permitted.
Self-combination legality remains governed by mood policy.
Nine ordered moods permit eighty-one ordered pairs.

11. Slot law

Slots attach capabilities.
Moods transform behavior.
Slots and moods are separate mechanisms.
A slot attachment never creates duplicate capability substance.
Slot capacity is derived from nine factors:
semantic stability
interface maturity
isolation strength
dependency fan-out
statefulness
authority sensitivity
failure containment
replay confidence
validation coverage
Capacity calculations emit receipts.

12. Masterplan law

The Masterplan is a dynamic living task list.
It is not an ontology domain.
It is not a hierarchy level.
It is not executable implementation.
It is not independent task authority.
Niche owns task discovery, decomposition, prioritization, blockers, readiness, scheduling, leases, transitions, and projection.
Canonical task meaning remains locally owned by the scope requesting the outcome.
The root Masterplan projects every eligible task into one global priority order:

/root/savant-runtime/MASTERPLAN.md
/root/savant-runtime/masterplan.json

Task substance exists once.
Local task views are projections.
Parent scopes expose roll-ups rather than copied descendant task substance.

12.1 Nine Masterplan domains

The root projection groups tasks into exactly nine domains:
authority
canon
ontology
rubrics
context
runtime
vault
assurance
evolution
These are task projections, not mandatory physical root folders.

13. Authority law

Authority precedence:
current user directive
accepted authoritative graph
accepted decisions
constitutional canon
verified implementation
admitted evidence
deterministic projection
historical implementation
historical documents
inference
speculation
Recency resolves conflicts only between sources of equal authority or where a newer accepted source explicitly supersedes an older source.
Filesystem presence does not establish authority.
AI output does not establish authority.
Accepted decisions are immutable.
Changes create superseding decisions.
Unresolved conflicts remain explicit.

14. Projection law

A projection:
references stable source identities;
records source digests;
records transformation identity;
records lineage and provenance;
records dependencies;
remains reproducible;
remains disposable;
never becomes authority through repeated use;
may be deleted and rebuilt without loss of canonical substance.
Indexes discover.
Hierarchy owns.
Views reveal.
Receipts prove.

15. Vault law

Vault is a custody, retention, replay, and recovery surface.
Vault may contain:

authority indexes
canon stores
context stores
graphs
fields
lineage
evidence
receipts
snapshots
manifests
dimensions

Vault placement does not create authority.
Every Vault artifact declares:

stable identity
authority state
custody owner
source identity
source digest
retention class
replay role
projection state
lineage
provenance

16. Runtime law

Runtime state is not canonical substance.
Runtime includes active:

executions
queues
leases
sessions
transactions
events
caches
provider activity
temporary projections
telemetry

Runtime state must be rebuildable or explicitly classified otherwise.
Telemetry is evidence, not truth.

17. Compatibility law

Compatibility may use:

adapter
launcher
alias
symlink
facade
schema translation
protocol bridge
generated view

Compatibility paths declare their authority state.
Every compatibility surface records active consumers.
Retirement is legal only after reverse-dependency evidence proves exhaustion.
Historical paths remain preserved in history and migration receipts.

18. Dependency law

Every external dependency records exactly nine properties:
owner
purpose
version constraint
lock or digest
license
supply-chain source
failure mode
fallback
removal strategy
A dependency is admitted only when it materially improves at least three of:

correctness
determinism
validation
replayability
recoverability
observability
security
maintainability
execution efficiency

External tools validate or project Savant semantics.
External tools never become Savant authority.

19. Security law

Capability access is deny-by-default.
Nine controlled capability boundaries exist:
filesystem reading
filesystem mutation
subprocess execution
network access
provider access
secret access
authority mutation
evidence admission
task transition
Every durable mutation requires a current authority witness at commit time.

20. Validation law

Canonical acceptance uses nine validation layers:
syntax
type
schema
policy
property
graph
integration
replay
regression
Validation depth is proportional to authority, impact, reversibility, and risk.
Disposable projections do not require canonical-mutation ceremony.
Canonical, destructive, or compatibility-breaking changes require the full witness chain.

21. Migration law

No blind filesystem rearrangement is permitted.
Every movable artifact requires:

stable_id
current_path
canonical_path
artifact_kind
semantic_owner
rubric_owner
shared_scope
authority_state
projection_state
history_state
source_digest
dependencies
dependents
compatibility_paths
migration_action
rollback_action
validation_contract

Unresolved ownership means no movement.
Migration proceeds through exactly nine governed phases:
inventory
classification
authority reconciliation
graph construction
destination compilation
compatibility staging
reversible migration
integrated validation
monitored retirement

22. Canonical organization

The canonical organization is Recursive Capsules with generated short-path development views.
Hierarchy substance remains nested.
Rubrics remain physically owned by their elements.
Cabals exist at proven shared scopes.
Generated views may expose compact owner-addressed paths without moving canonical ownership.
Canonical root responsibilities:

/root/savant-runtime/
├── MASTERPLAN.md
├── masterplan.json
├── authority/
├── canon/
├── context/
├── lexicon/
├── ontology/
├── runtime/
├── vault/
├── assurance/
├── evolution/
├── projections/
├── bin/
└── docs/

This root shape is semantic guidance.
Existing roots are migrated only through verified classification.

22.1 Canonical nested identity pattern

ontology/
└── obelisks/
    └── <obelisk>/
        ├── instance.yaml
        ├── authority/
        ├── rubric/
        ├── cabal/
        ├── kindred/
        ├── moods/
        ├── slots/
        ├── attachments/
        ├── projections/
        ├── observatory/
        ├── history/
        ├── tasks/
        └── segue/
            └── portals/
                └── <portal>/
                    └── segue/
                        └── innates/
                            └── <innate>/
                                └── segue/
                                    └── exiles/
                                        └── <exile>/
                                            └── segue/
                                                └── prodigals/
                                                    └── <prodigal>/
                                                        └── segue/
                                                            └── quirks/
                                                                └── <quirk>/
                                                                    └── segue/
                                                                        └── traits/
                                                                            └── <trait>/
                                                                                └── segue/
                                                                                    └── motes/
                                                                                        └── <mote>/
                                                                                            └── segue/
                                                                                                └── iotas/
                                                                                                    └── <iota>/

Only actual instances and used facilities materialize.
Templates never become competing substance.

23. Ownership statement

Rubric owns.
Cabal shares.
Kindred relates.
Segue transitions.
Mood transforms.
Slot attaches.
Authority governs.
Projection reveals.
Receipt proves.

24. Non-negotiable prohibitions

Savant shall not:
flatten canonical hierarchy;
duplicate lower-level substance;
promote speculative Cabals;
infer authority from path;
copy moods into every element;
copy complete instance substance into consumers;
mix unrelated Rubric ownership;
place substantive logic in thin launchers;
store generated views as competing authority;
destructively rewrite history;
silently reconcile conflicts;
guess unknown Kindred coordinates;
mutate canonical state without current authority;
retire compatibility without consumer proof;
require architectural replacement merely to extend.

25. Acceptance

This decision establishes the canonical target architecture.
It authorizes:
canon records;
schemas;
validators;
inventory;
classification;
migration planning;
compatibility planning;
reversible staging.
It does not authorize unclassified destructive movement.
Full structural migration requires a verified migration manifest and commit-time authority witness.

