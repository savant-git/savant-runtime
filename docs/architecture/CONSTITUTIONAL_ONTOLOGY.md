# Constitutional ontology

## Ontology and recursive object model

Reality is a `ConstitutionalObject`. Its sole child is Ontology; Doctrine,
System, Faculty, Exile, Service, Operator, Instance, Segue, Concept, Runtime,
and Project are ontology-definition objects below it. Registered kinds,
schemas, and relationship semantics are also ConstitutionalObjects. Nothing
has a privileged representation beyond the universal immutable primitive.

Containment is declared once as `lineage.parent`. Children, ancestry, and
descendants are reconstructed iteratively, with no maximum depth and no stored
inverse edges.

## Relationship and dependency model

Relationship types are authority records discovered from
`relationships.json`; application code does not enumerate allowed semantics.
Typed relationship edges and dependency edges share the graph but remain
queryable independently. Dependency queries expose direct, transitive, and
reverse closure. Cycles are reported and exported through visualization hooks;
containment cycles are invalid.

## Authority, lineage, and provenance

Authority remains a direct object primitive. Lineage views derive origin,
ancestry, descendants, revision history, and the authority chain from parent
and supersession assertions. Provenance views combine declared creation
sources with deterministic schema, parent, migration, and projection context.
Derived views are never written to authority.

## Projection model

Projection plugins are discovered from `runtime.constitution.projections`.
Built-in targets cover runtime, JSON, YAML, Markdown, documentation, graph,
future visualization, and future code generation. Every projection is hashed,
deterministic, side-effect free, and guarded against mutation of authority.

## Validation and migration strategy

Validation covers schema, relationship, dependency, projection, lineage,
provenance, recursion, and registry integrity. The migration-readiness query
reports missing lineage/provenance, duplicate identities/authorities, schema,
relationship and dependency inconsistencies, and dependency cycles. It never
repairs data. Runtime migration remains deferred; future phases may attach one
subsystem at a time only after reviewing this report.
