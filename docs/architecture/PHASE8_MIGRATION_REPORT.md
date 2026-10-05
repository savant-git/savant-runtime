# Phase 8 Migration Report

Generated from the constitutional catalog on 2026-07-21.

## Convergence progress

- Registered semantic objects: 106
- Objects available to projection providers: 106 (100%)
- Unprojectable objects: 0
- Remaining runtime adapters in the authority-only registry: 0
- Remaining legacy systems: 0

## Duplicate-value audit

The read-only convergence audit found 6 repeated authority-value groups, 8 repeated
lineage-value groups, 13 repeated provenance-value groups, and 12 repeated metadata-value
groups. These are equal values declared by distinct authoritative objects, not parallel
runtime registries. They remain visible as migration evidence; runtime consumers now
resolve them from each object's single immutable registration.

No additional duplicated semantic storage was introduced. Identity, schema, authority,
lineage, provenance, relationships, dependencies, and metadata remain primitives of the
catalog object. Resolver indexes, graph edges, reflection results, validation results, and
projection cache entries are regenerated views.

## Projection opportunities

All registered objects expose at least one projection target. Future UI, API, IDE, and
tooling providers are registered as stateless structured projections and can be replaced
by specialized providers without changing constitutional data.

## Legacy compatibility

Existing `ConstitutionalRegistry` query names remain supported as delegates to the Phase 8
engines. Authority files and migration adapters were not rewritten. The runtime migration
scanner remains available for the migrated registry and its reports remain reversible.
