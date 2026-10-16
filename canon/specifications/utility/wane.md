# wane specification

canonical id: `utility:tactic:wane`

canonical name: `wane`

kind: `tactic`

edifice: `utility`

version: `1.0.0`

## purpose

wane is savant's bounded inward object-transfer tactic.

it maps admitted objects from `s3://savant-ai-cluster/` into the local
directory from which wane is invoked.

## exact-object semantics

if invoked from:

`/root/savant-runtime/foo/bar`

then:

`wane archive.zip`

produces:

`/root/savant-runtime/foo/bar/archive.zip`

## prefix semantics

prefix downloads preserve paths relative to the requested prefix.

## glob semantics

glob downloads preserve paths relative to the stable non-glob prefix.

## invariants

wane never redirects output into an implicit directory.

wane may only execute from within `/root/savant-runtime`.

wane rejects foreign s3 buckets.

wane rejects traversal.

wane stages downloads to temporary files.

an existing destination remains untouched until the replacement has completed.

wane validates object size.

wane validates sha-256 when wax-originated metadata is available.

wane records a non-authoritative receipt.

## command surface

`wane KEY`

`wane s3://savant-ai-cluster/KEY`

`wane PREFIX/`

`wane 'PREFIX/*.zip'`

`wane --dry-run KEY`

`wane --no-clobber KEY`

`wane --json KEY`

`wane --status`

`wane --selftest`

## compatibility

`dow` delegates to wane.

`dow` is not a separate utility identity.

## authority

aws is not authoritative.

s3 object identifiers remain external identifiers.

transfer receipts are evidence rather than authority.

this specification is canon.
