# Phase 4 runtime migration architecture

## Constitutional architecture and runtime mapping

Phase 4 adds a read-only adapter between the existing runtime and the Phase 3 registry. Existing Systems, Exiles, Faculties, Services, Operators, Instances, and Segues remain authoritative and byte-for-byte unchanged. Runtime modules project as constitutional Instances; public top-level classes and functions project as Operators. The most-specific existing `implementation_refs` declaration provides constitutional ownership.

Runtime-specific registries, graphs, and projections remain compatibility APIs. They implement subsystem behavior and are attached to, rather than replaced by, the constitutional graph.

## Migration workflow

1. Recursively discover Python sources beneath `runtime`.
2. Parse with AST without importing modules or triggering behavior.
3. Classify modules and public definitions.
4. Resolve the most-specific constitutional implementation owner.
5. Create immutable adapter objects with source fingerprints and reversible source/qualname coordinates.
6. Register through the existing `ConstitutionalRegistry`.
7. Validate schemas, lineage, authority, relationships, dependencies, projections, coverage, and reversibility.

No manual migration table is used. New runtime modules and public definitions enter the next bootstrap automatically.

## Lifecycles

Bootstrap discovers ontology, schemas, relationships, runtime sources, migrated objects, registers a single graph, validates it, and exposes a report. Extension composition remains available through `ConstitutionalExtensions`; projection providers remain package-discovered. Projection artifacts remain disposable and authority-bearing. Validation reports discrepancies and never repairs source or authority.

## Compatibility guarantees

No existing runtime source is rewritten, imported during discovery, or wrapped on execution. Existing public imports and subsystem semantics remain unchanged. The legacy `ConstitutionalBootstrap.objects` scope is retained while its new `registry`, `runtime_migration`, and `report` fields expose the complete Phase 4 state.
