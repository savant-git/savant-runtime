# SAVANT DIMENSION SYSTEM

Version: 1.4.0  
Status: Implementation Candidate  
Canonical path: `/root/savant-runtime/vault/dimensions/sys`

## Purpose

This directory contains every implementation artifact belonging specifically to Savant's nine-dimensional archival subsystem.

It is not a data dimension.

It governs the sibling dimensions:

1. Canon
2. Context
3. Motive
4. Proof
5. Seed
6. Sense
7. Signal
8. Trajectory
9. Affinity

## Structural Law

All nine dimensions are structurally equal beneath:

`/root/savant-runtime/vault/dimensions`

Canon is authoritative by function, not by privileged filesystem placement.

`sys` contains implementation, tracery, tests, reports, and subsystem metadata. It contains no dimensional object data.

## Files

- `VERSION` — subsystem semantic version
- `dimension_registry.json` — accepted dimensional sear candidate
- `schemas/dimensional-record.schema.json` — machine-readable dimensional almanac contract
- `scaffold.py` — migration, scaffold, refresh, reporting, and verification engine
- `dimensionsctl.py` — stable controller
- `kindred_migration.py` — Kindred/Kinship semantic compatibility auditor
- `tests/test_scaffold.py` — focused subsystem tests
- `reports/` — generated execution reports

## Commands

Inspect without mutation:

`python3 /root/savant-runtime/vault/dimensions/sys/dimensionsctl.py plan`

Apply safe dimensional migration and create missing records:

`python3 /root/savant-runtime/vault/dimensions/sys/dimensionsctl.py apply`

Refresh stale generated records after canon changes:

`python3 /root/savant-runtime/vault/dimensions/sys/dimensionsctl.py apply --refresh`

Verify the complete dimensional subsystem:

`python3 /root/savant-runtime/vault/dimensions/sys/dimensionsctl.py verify`

Display current dimensional state:

`python3 /root/savant-runtime/vault/dimensions/sys/dimensionsctl.py status`

Audit Kindred/Kinship terminology:

`python3 /root/savant-runtime/vault/dimensions/sys/kindred_migration.py plan`

Verify that no unresolved Kindred/Kinship semantic conflicts remain:

`python3 /root/savant-runtime/vault/dimensions/sys/kindred_migration.py verify`

## Authority Boundary

Generated dimensional almanacs begin unadmitted and non-authoritative.

The scaffold may:

- migrate identical or non-conflicting trees
- back up existing paths
- create missing directories
- create deterministic almanacs
- identify stale generated material
- refresh generated almanacs when explicitly requested
- preserve manual almanacs
- verify dimensional coverage

The scaffold may not:

- manufacture authority
- admit claims
- resolve contradictions
- overwrite manual dimensional almanacs
- merge non-identical competing trees
- delete history without backup
- treat `sys` as a tenth dimension

## Kindred and Kinship

Kindred and Kinship are separate active Savant concepts.

### Kindred

Kindred is Savant's canonical relationship methodology and universal typed relationship system.

It defines or governs relationship semantics, typed relationship families, constraints, cardinality, authority, lineage, provenance, validity, and graph-addressable relationship structure.

### Kinship

Kinship is an active functional relationship-plane service.

Accepted identity:

`service:kinship`

Implementation:

`runtime/kinship`

Kinship compiles functional relationship planes and depends on:

`system:kindred`

It is implemented through:

`exile:modus`

## Non-Equivalence Law

The following interpretations are invalid:

- Kinship is a historical spelling of Kindred.
- Kindred supersedes Kinship.
- Kinship supersedes Kindred.
- Every occurrence of `kinship` should be rewritten to `kindred`.
- The existence of the Kinship service weakens Kindred's authority.

The correct relationship is:

`Kinship -> depends_on -> Kindred`

Both remain independently graph-addressable.

## Compatibility Auditing

`kindred_migration.py` retains its historical filename for compatibility, but it no longer performs global lexical replacement.

It now classifies Kinship occurrences into:

- active Kinship service/runtime usage
- lexical or historical governance
- suspicious Kindred-intent usage
- obsolete migration assumptions
- unresolved semantic usage

No occurrence is automatically rewritten.

A semantic replacement is valid only when sufficient authority establishes that a particular occurrence uses `Kinship` to mean the Kindred methodology rather than the active Kinship service.

## Preservation Law

Historical migration reports and backups remain historical evidence.

They are not current lexical authority and must not be rewritten merely to conceal earlier terminology decisions.
