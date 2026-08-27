# Phase 11 — Fluid Canon Engine

Fluid Canon is the first engine built wholly on the constitutional substrate. It owns no
database, graph, registry, authority table, or history store. `FluidCanonEngine` holds a
constitutional registry snapshot and every contributed canon entry is an immutable
`ConstitutionalObject` accepted through `ConstitutionalAssertionAPI`.

## Assertions and authority

Facts, observations, inferences, hypotheses, constraints, doctrines, rules, exceptions,
decisions, supersessions, evidence, sources, conflicts, and resolutions use the existing
`concept` kind. Their canon form is the authoritative `metadata.assertion_type`; subject
and claim are assertion metadata. Objects declare no local authority. Effective authority
is inherited along Reality → domain:ontology → domain:concept and queried through the
constitutional authority resolver.

Installation contributes `service:fluid-canon` as a normal service assertion. It does not
alter the catalog in place. Batch contribution returns a new immutable semantic snapshot,
leaving the caller’s registry and every earlier canon object unchanged.

## Evolving truth

New truth records previous assertion IDs in `lineage.supersedes`. Existing assertions are
never edited or deleted. Current truth is the deterministic set of assertions not
superseded in the selected snapshot. Historical truth applies the same rule after filtering
by timestamp or semantic version, so any earlier canon state is reconstructible directly
from the assertion set.

## Explanation and evidence

`why` projects claim, asserter, provenance, inherited authority, evidence, conflict, and
supersession chains. Evidence uses `derived_from` relationships with the `evidence` role;
conflicts and resolutions use `references` with `conflict` and `resolves` roles. Queries
walk those constitutional relationships and the existing supersession graph without
creating a Fluid Canon graph or index.

## Validation

Validation rejects orphan parents, missing inherited authority, supersession cycles,
evidence links that do not target Evidence or Source assertions, and provenance lacking an
asserter or source. Constitutional registration independently rejects unknown references,
duplicate identity, invalid kinds, unknown relationship types, and schema violations.

Fluid Canon therefore supplies evolving canonical semantics while preserving the permanent
rule of the runtime: assertions are authoritative; every query result is a projection.
