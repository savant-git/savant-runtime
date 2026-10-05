# normalized-records

**Authority status:** migration-canon candidate. This document records
the current target architecture and verified historical evidence. It
must be admitted through Savant's live authority/evolution process
before becoming runtime authority. Historical source statements are
preserved rather than silently rewritten.

## Verified V15 edge

`trait:ingest` → `trait:proof`

**Type:** `normalized-records`

## Meaning

Normalized output from ingestion becomes neutral evidence-record input.

## Migration rule

The semantic dependency survives even if final Trait/Quirk boundaries
change. If both endpoints become internal to one Quirk, preserve the
relationship as internal dependency/lineage rather than erasing it.

## Validation contract

Validate endpoint identity, source-provided capability, target
requirement, compatibility, cardinality if defined, effects/authority,
provenance and lifecycle compatibility.

## Anti-pattern

Do not replace this with an undocumented direct call. Hidden
dependencies are defects.
