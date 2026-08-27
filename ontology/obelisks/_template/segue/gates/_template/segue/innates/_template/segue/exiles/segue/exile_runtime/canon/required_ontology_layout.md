# EXILE CAPABILITY-MATERIALIZED LAYOUT

STATUS: CANON
OWNER: EXILE RUNTIME
VERSION: 2.0.0
SUPERSEDES: required fixed-folder interpretation
PHYSICAL_MIGRATION_AUTHORIZED: false
DESTRUCTIVE_MUTATION_AUTHORIZED: false

## 1. Governing rule

Every Exile must expose stable identity.

Every Exile does not need to expose every possible facility as a physical directory.

A facility materializes only when the Exile:

- owns canonical substance for that facility;
- owns executable implementation for that facility;
- maintains local state for that facility;
- requires a compatibility surface for that facility;
- explicitly declares that facility in its materialization manifest.

Empty directories do not establish capability.

Missing unused directories are valid.

Missing declared directories are invalid.

Existing historical directories remain valid compatibility surfaces.

This contract does not authorize their deletion.

## 2. Canonical facility vocabulary

Exile facilities may include:

- apps
- authority
- cache
- canon
- composition
- dynamic
- evolution
- facets
- graph
- interface
- introspection
- lifecycle
- lineage
- metrics
- observatory
- registry
- runtime
- sessions
- state
- static
- tests
- validation
- segue

The vocabulary is extensible.

The existence of a facility name in this vocabulary does not require every Exile to materialize it.

## 3. Minimum physical requirement

An accepted Exile requires only:

- its canonical Exile root;
- whatever identity or authority records are already required by accepted authority;
- every facility explicitly declared as materialized.

No empty facility directory is required solely for structural symmetry.

## 4. Materialization manifest

An Exile may declare:

`facility.manifest.json`

Example:

```json
{
  "schema": "savant://ontology/exile/facilities/1.0.0",
  "owner": "exile:niche",
  "materialized": [
    "authority",
    "canon",
    "runtime",
    "registry"
  ],
  "optional": [
    "interface",
    "observatory",
    "tests"
  ],
  "compatibility": [
    "apps"
  ]
}

materialized means the directory must exist.
optional means the directory may exist.
compatibility means the directory exists for compatibility and must not be mistaken for canonical ownership.
5. Living Slot Fabric
Living-substrate capability is attached through the Living Slot Fabric.
An Exile does not need a copied local implementation of:
Scyon;
Splyce;
Scrybe;
Pryme;
Cypher;
Thryce;
Spyral;
Lythe;
Dryve.
It binds to substrate instances through living slots.
A physical directory must not be generated merely because a living slot exists.
6. Recursive Capsule compatibility
The Exile capsule may expose facilities including:
rubric
cabal
kindred
moods
slots
attachments
projections
observatory
history
tasks
segue
These materialize only when used.
Rubrics and Cabals remain implementation-bearing according to their accepted ownership rules.
Kindred, moods, slots, attachments, and projections should normally reference canonical substance rather than duplicate it.
7. Validation law
Exile layout validation must distinguish:
Exile identity existence;
declared materialized facilities;
optional facilities;
compatibility facilities;
undeclared legacy facilities;
living-slot bindings;
missing declared facilities;
invalid manifest entries;
destructive migration state.
Only missing declared facilities are structural layout failures.
Legacy directories are reported, not deleted.
8. Migration boundary
Adoption is non-destructive.
The validator must:
stop requiring unused directories;
continue recognizing existing directories;
validate new facility manifests when present;
preserve old consumers;
report redundant empty directories as observations only.
Removal requires separate migration authority and dependent analysis.
9. Hierarchy
Exiles segue into Prodigals.
Prodigals segue into Quirks.
Quirks continue through the accepted identity hierarchy.
Runtime layers are transition infrastructure.
Runtime layers are not ontology children.
