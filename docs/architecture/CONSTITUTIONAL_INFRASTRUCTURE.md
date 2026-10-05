# Constitutional infrastructure

## Philosophy

`ConstitutionalObject` is the only architectural primitive. System, Exile,
Faculty, Service, Operator, Doctrine, and future kinds are registry-defined
semantic identities, not Python subclasses. Existing runtime implementation
remains untouched and authoritative for behavior.

## Storage and schema model

Authority stores only the universal primitive fields. Children, ancestry,
inverse edges, matrices, renderings, and digests are derived. Kinds are loaded
from `kinds.json`; versioned schemas are automatically discovered from
`schemas/*.schema.json`. Specialized schemas inherit the universal schema and
extend only through metadata and typed relationships.

## Registry and graph model

The registry enforces immutable IDs and indexes objects by kind, version,
lineage, dependencies, relationships, and schema. The graph is rebuilt from
object primitives, uses typed nodes and edges, detects containment cycles, and
supports ancestry, descendants, dependency closure, relationship queries, and
deterministic export. Visualization hooks are data contracts only; there is no UI.

## Projection model

The projection engine is pure and deterministic. Runtime, documentation,
graph, JSON, Markdown, visualization, and future-visualization views exist only
in memory or command output and are never written back to authority.

## Bootstrap and migration strategy

Bootstrap loads only constitutional authority: registered kinds, schemas,
Systems, Exiles, Faculties, Services, Operators, and governing domains. The
legacy catalog adapter preserves the already-established mappings, but this
phase adds no runtime imports, wrappers, execution paths, or subsystem
migration. Future migration attaches one subsystem at a time by adding direct
authority assertions; projections remain generated.
