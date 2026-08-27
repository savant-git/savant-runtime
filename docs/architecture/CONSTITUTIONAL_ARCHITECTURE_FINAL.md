# Constitutional Architecture

The constitution is Savant's authoritative semantic layer. It stores immutable declarations and projects disposable runtime, graph, documentation, serialization, schema, validation, code-generation, and visualization artifacts.

## Ontology and object

Kinds are data discovered by `KindRegistry`; they never add subclasses or behavior. Every `ConstitutionalObject` has exactly one kind and fifteen authoritative primitives: identity, names, description, authority, status/version/timestamps, lineage, provenance, relationships, dependencies, and metadata. Nested values are frozen on entry and copied on export.

## Schemas, relationships, and registry

`ConstitutionalSchemaRegistry` discovers versioned inheritable schemas and enforces the primitive boundary. `RelationshipTypeRegistry` discovers allowed edge semantics. `ConstitutionalRegistry` rejects duplicate identities, unknown kinds/relationships, and schema failures; it provides deterministic kind/version indexes and read-only constitutional queries.

## Graph, lineage, provenance, and authority

`ConstitutionalGraph` derives containment, dependency, relationship, and supersession edges. Traversal and strongly connected component detection are iterative. Lineage and provenance chains are reconstructed from stored declarations. `AuthorityResolver` folds root-to-leaf declarations, with local keys overriding inherited keys, and exposes validation and traces.

## Projection and validation

Providers discover themselves from `runtime.constitution.projections`. The pipeline is object set → context → provider → immutable artifact. Artifacts include target, payload, digest, sources, authority declarations, and optional child artifacts. Projection guards compare authority before and after execution. Validators discover the same provider set, verify deterministic repeated output, and report rather than repair discrepancies.

## Bootstrap and migration

Bootstrap discovers authority in dependency order, validates it, discovers runtime source through AST, registers reversible adapter objects, builds one constitutional graph, and returns its report. Runtime behavior is never imported, wrapped, or rewritten by migration. Existing runtime registries and graphs remain compatibility implementations attached through constitutional metadata.

## Extension model

`ConstitutionalExtensions` composes kinds, schemas, validators, projections, relationships, doctrines, faculties, services, and operators without inheritance requirements. Runtime discovery plugins use the `savant.constitution.runtime` package entry-point group. Projection targets use provider package discovery. New source modules are included recursively without registration tables.

## Evidence and versions

`ConstitutionalEventLog` records immutable append-only historical evidence and never becomes authority. `ConstitutionalVersions` independently identifies schema, ontology, projection, authority, and migration semantic versions. Object revisions preserve supersession lineage.
