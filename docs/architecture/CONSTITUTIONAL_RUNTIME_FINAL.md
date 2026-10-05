# Constitutional Runtime — Final Converged Architecture

## Constitutional runtime

The runtime has one authoritative semantic substrate: immutable constitutional
assertions, their schemas, constitutional events, identity, authority, relationships,
lineage, and provenance. `ConstitutionalObject` accepts exactly the primitive field set;
derived graphs, indexes, tables, reports, or executable adapters cannot be stored in it.
Reality is itself an assertion and every assertion roots a recursively projectable
constitutional universe.

## Projection runtime and semantic registry

`ConstitutionalRegistry` owns assertions exactly once. Its identity, kind, and version
indexes, graph and reverse graph, dependency maps, recursive universes, documentation,
reflection tables, visualization data, validation results, and diagnostics are in-memory
views regenerated from assertions. Projection caches are disposable, digest-keyed, and
explicitly non-authoritative. Legacy “runtime objects” are source-discovery adapters that
become ordinary constitutional assertions before registration; they have no separate
semantic status.

## Reflection, authority, lineage, provenance, and inheritance

Reflection deterministically answers identity, purpose, declaration, governance,
creation, schema, dependencies, supersession, runtime implementation, documentation,
projection, and graph questions. Effective authority is reconstructed root-to-object.
Lineage and provenance engines rebuild ancestry, descendants, supersession, migrations,
origin, creation method, sources, validation, and implementation evidence. Inheritance
merges authority and metadata, accumulates unique relationships, projection targets,
validators, and schemas, and deliberately leaves dependencies explicit.

## Events and temporal reality

Constitutional events are frozen sequence records protected by canonical SHA-256 digests.
Pure replay reconstructs state by sequence, timestamp, or version, including historical
lineage, authority, relationships, dependencies, and schemas. Event history never mutates
an earlier assertion.

## Validation and self-audit

Recursive validation covers identity, schemas, authority, relationships, dependencies,
projection determinism, lineage, provenance, inheritance, orphans, registry indexes, and
graph integrity. Self-audit additionally verifies single storage ownership, absence of
orphan projections and broken references, and cache freshness. Equal values shared by
multiple assertions are reported as evidence, not misclassified as duplicate storage.

## Deterministic projection pipeline

Every runtime materialization follows independently testable stages:

1. Assertions
2. Validation
3. Inheritance
4. Resolution
5. Relationship expansion
6. Dependency expansion
7. Projection
8. Caching
9. Runtime

The final runtime view contains regenerated registries, indexes, graph and reverse indexes,
dependency maps, projection tree, documentation, reflection table, visualization, and
diagnostics. A canonical digest proves deterministic regeneration.

## Extension model

Future engines contribute constitutional assertion mappings through
`ConstitutionalAssertionAPI`. Contribution validates primitive shape and identity and
returns a new registry snapshot; it does not mutate the active runtime. Plugins use this
same boundary. Direct runtime mutation is outside the extension contract. Fluid Canon,
Memory, Narrative, Persona, Investigation, and subsequent engines therefore extend the
substrate by declaring services, operators, policies, schemas, relationships, and other
constitutional objects.

## Migration model

`ConstitutionalDiffer` compares assertion catalogs and reports additions, removals,
versions, schemas, authority, relationships, dependencies, projections, and lineage. It
emits a deterministic ordered migration plan composed of registration, field-change,
schema-change, projection-change, and retirement actions. Plans are data and become
effective only when expressed as new assertions or immutable events.

## Future engine integration

Higher-level engines may execute specialized algorithms and emit operational projections,
but their identities, authority, contracts, dependencies, schemas, provenance, and
relationships enter only as constitutional assertions. This keeps each future capability
composable with the same resolver, reflection, graph, validation, inheritance, temporal,
diff, audit, and projection machinery instead of creating another architecture.
