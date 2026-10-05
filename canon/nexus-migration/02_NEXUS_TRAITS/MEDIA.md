# MEDIA --- Media intelligence

**Authority status:** migration-canon candidate. This document records
the current target architecture and verified historical evidence. It
must be admitted through Savant's live authority/evolution process
before becoming runtime authority. Historical source statements are
preserved rather than silently rewritten.

## Verified V15 identity

-   **ID:** `trait:media`
-   **Kind:** `trait`
-   **Version:** `0.3.0`
-   **Status:** `candidate`
-   **Provenance:** `nexus-v14`
-   **Authority effect:** `none`
-   **Mobile metadata:** `true`

## Purpose

Handles media metadata, playback integration, transcript synchronization
and cue/time-position behavior. Semantic media records must remain
distinct from player implementation.

## Verified provided capabilities

-   `media.metadata` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.
-   `media.playback` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.
-   `transcript.sync` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.
-   `media.cue` --- canonical capability token carried by the V15
    candidate; final ownership must be reconciled against live
    Traits/Quirks.

## Verified typed relationships

-   No outgoing V15 segue is recorded for this Trait.

## Historical context

Receives media sources from Ingest.

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
