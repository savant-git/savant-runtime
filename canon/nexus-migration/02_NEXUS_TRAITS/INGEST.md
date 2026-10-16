# INGEST --- Universal ingestion

**Authority status:** migration-canon candidate. This document records
the current target architecture and verified historical evidence. It
must be admitted through Savant's live authority/evolution process
before becoming runtime authority. Historical source statements are
preserved rather than silently rewritten.

## Verified V15 identity

-   **ID:** `trait:ingest`
-   **Kind:** `trait`
-   **Version:** `0.3.0`
-   **Status:** `candidate`
-   **Provenance:** `nexus-v14`
-   **Authority effect:** `none`
-   **Mobile metadata:** `true`

## Purpose

Receives heterogeneous source material, preserves source identity,
normalizes usable representations, records metadata and hashes, and
routes format-specific handling through adapters.

## Verified provided capabilities

-   `source.ingest` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.
-   `source.normalize` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.
-   `source.metadata` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.
-   `source.hash` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.
-   `adapter.route` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.

## Verified typed relationships

-   normalized-records → Proof
-   media-sources → Media

## Historical context

V14 described the predecessor as zero-format heterogeneous source
ingestion and neutral normalization, with workspace source/fragment
effects.

## Current migration treatment

This is an **intermediate candidate Trait**, not automatically final
canon. Search existing Motes, Traits and Quirks before preserving,
splitting, merging or replacing it. Do not mechanically promote this
Trait to Quirk.

## Projection boundary

Any rendering/player/preview capability must be tested for
semantic-versus-projection separation. Nexus identity must remain
independent of HTML, CSS, graph libraries, media players or a future 3D
engine.

## Evidence integrity

Behavior derived from this Trait must preserve the distinction between
source, extraction, normalized record, annotation, machine
interpretation, inference and conclusion.

## Acceptance tests

-   semantic ID resolves or has an explicit successor;
-   every provided capability has one canonical owner/disposition;
-   no duplicate existing Trait/Quirk is created;
-   typed relationships remain inspectable;
-   authority/effects are explicit;
-   V14/V15 lineage remains traversable.
