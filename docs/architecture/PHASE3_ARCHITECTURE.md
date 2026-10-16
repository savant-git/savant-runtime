# Phase 3 constitutional architecture

## Philosophy

The constitution is the sole ontology. Runtime, graph, documentation, serialization, schemas, validation, future code generation, and visualization are disposable views of immutable constitutional objects.

## Projection architecture

`ConstitutionalObject → ProjectionContext → registered provider → ProjectionArtifact`. Artifacts contain a deterministic digest, source identities, and the authority chain. Chained artifacts recursively invoke the same pipeline. Providers are independently discovered from the projections package; adding a target requires no engine branch.

## Extension and discovery model

Kinds, schemas, relationship types, constitutional definitions, and projection providers are discovered from authority directories or packages during bootstrap. `ConstitutionalExtensions` exposes compositional registration for kinds, schemas, validators, projections, relationships, doctrines, faculties, services, and operators. Duplicate identity registration fails.

## Identity model

The stored `id` never mutates. Aliases, historical names, and superseded identities resolve through `CanonicalIdentityResolver`; collisions fail at bootstrap. Identity migration records evidence without rewriting authority.

## Authority model

Authority is inherited root-to-leaf. Each local declaration overrides keys inherited above it. Validation rejects empty chains. Traces expose both every declaration and the effective result, and every projection artifact carries its producing authority declarations.

## Version and event models

Five independent semantic versions cover schema, ontology, projection, authority, and migration. Object `version` remains authoritative and revisions retain lineage through supersession. Constitutional events are immutable append-only evidence and are never replayed into authority.

## Query model

The registry provides typed collections, ancestor/descendant traversal, projections, authority/provenance/lineage chains, recursive dependency trees, and relationship subgraphs. Queries return values without mutating objects or catalogs.

## Bootstrap and discovery sequence

1. Discover kind definitions.
2. Discover versioned schemas and inheritance.
3. Discover relationship types.
4. Discover constitutional object authority and adapters.
5. Validate primitives and references.
6. Build identity, kind, version, and graph indexes.
7. Discover projection providers and validators when invoked.

Runtime subsystem migration remains intentionally out of scope until readiness is accepted.
