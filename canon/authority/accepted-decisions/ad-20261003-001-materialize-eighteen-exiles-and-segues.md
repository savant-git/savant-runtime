# accepted decision: materialize eighteen exiles and their identity segues

decision id: ad-20261003-001
status: accepted
accepted at: 2026-10-03
authority: current user directive
scope: savant identity edifice
mutation policy: immutable; supersede through a later accepted decision only

## decision

the accepted savant identity edifice must physically expose all eighteen
currently accepted exile identities.

the active exile set is:

1. carbon
2. cataxis
3. coda
4. envoy
5. filament
6. graffiti
7. lore
8. mobius
9. modus
10. niche
11. notary
12. opus
13. pact
14. palaver
15. shatter
16. underscore
17. urge
18. zero

their accepted purpose and ownership semantics remain governed by their
existing accepted authority records at:

`/root/savant-runtime/canon-system/authority/exiles/<exile>.yaml`

this decision does not create alternative purpose authority and does not
duplicate those records.

## physical materialization

each accepted exile must have one stable identity capsule at:

`/root/savant-runtime/edifices/identity/exiles/<exile>/`

each materialized exile capsule must expose an identity projection that
references, rather than copies as authority, its canonical authority record.

filesystem presence does not establish authority.

## segue materialization

segue remains a first-class transition primitive.

where a child identity collection is physically materialized, transition
through the parent segue is canonical.

for exile to prodigal traversal, the canonical physical pattern is:

`<exile>/segue/prodigals/<prodigal>/`

for prodigal to quirk traversal, the canonical physical pattern is:

`<prodigal>/segue/quirks/<quirk>/`

the segue directory must contain transition substance and must not exist as
an empty decorative folder.

a child collection must not be created merely to satisfy visual symmetry.

## compatibility

existing valid implementations must survive.

where an existing direct child collection currently exists at:

`<exile>/prodigals/`

or:

`<prodigal>/quirks/`

its canonical substance may be relocated atomically beneath the appropriate
segue while the old direct path remains as a compatibility symlink.

the compatibility path and canonical path must resolve to the same substance.

no duplicate implementation tree may be created.

## authority

the existing accepted exile authority records remain authoritative.

edifice-local `instance.yaml` files created by this migration are deterministic
identity projections with `authority_effect: none`.

segue-local `instance.yaml` files created by this migration are deterministic
transition projections with `authority_effect: none`.

projections do not become authority.

filesystem layout does not become authority.

deterministic derivation does not become verification.

## preservation

the migration must preserve:

- existing accepted authority;
- existing implementations;
- accepted exile purposes;
- existing prodigals;
- existing quirks;
- lineage;
- provenance;
- dependencies;
- dependents;
- compatibility;
- replayability;
- source identity;
- historical evidence.

historical structures remain evidence.

historical authority is not destructively rewritten.

## conflict handling

unknown extra exile directories must be preserved and reported.

colliding canonical and legacy child trees must block migration.

non-directory objects occupying required structural paths must block migration.

non-generated identity projection files must never be silently overwritten.

## recovery

the current identity edifice must be backed up before structural mutation.

the migration must be reversible.

the migration must emit a receipt containing:

- backup path;
- authority source hashes;
- structural changes;
- verification result;
- deterministic semantic digest.

## empty facilities

empty structural facilities are forbidden.

`prodigals/`, `quirks/`, and deeper collections materialize only when actual
children exist.

a `segue/` facility may materialize without children only when it contains the
governed transition definition itself.

## known implementation continuity

existing niche/masterplan substance must be preserved.

existing opus/nocturne substance must be preserved.

existing nocturne quirks must be preserved.

the accepted modus/coalesce identity may be projected into the edifice by
reference to its existing canonical implementation evidence rather than by
copying that implementation.

## external dependencies

no new external dependency is authorized or required for this migration.

the standard library is sufficient.

## completion condition

this decision is implemented when:

- all eighteen accepted exile directories exist;
- every exile resolves to its existing accepted authority source;
- every exile exposes a non-empty segue transition facility;
- existing prodigal and quirk collections traverse the segue layer;
- legacy direct child paths remain compatible where previously used;
- no canonical substance is duplicated;
- no existing implementation is lost;
- verification passes;
- rollback evidence exists;
- a deterministic migration receipt exists.
