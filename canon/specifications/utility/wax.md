# wax specification

canonical id: `utility:tactic:wax`

canonical name: `wax`

kind: `tactic`

edifice: `utility`

version: `1.0.0`

## purpose

wax is savant's bounded outward object-transfer tactic.

it maps admitted files beneath `/root/savant-runtime` to the root namespace of
`s3://savant-ai-cluster/`.

## file semantics

for an individual file:

`/root/savant-runtime/path/example.zip`

projects to:

`s3://savant-ai-cluster/example.zip`

for a directory:

`/root/savant-runtime/assets`

projects to:

`s3://savant-ai-cluster/assets/...`

while preserving the directory's internal relative hierarchy.

## invariants

wax never introduces an implicit remote prefix.

wax never accepts a source outside `/root/savant-runtime`.

wax does not traverse symbolic links.

wax rejects sensitive-looking files by default.

wax calculates sha-256 before transfer.

wax records the sha-256 in external object metadata.

wax can skip an object whose current remote size and wax hash already match.

wax records a non-authoritative receipt.

## command surface

`wax FILE`

`wax FILE FILE`

`wax DIRECTORY`

`wax --dry-run FILE`

`wax --json FILE`

`wax --allow-sensitive FILE`

`wax --status`

`wax --selftest`

## compatibility

`upl` delegates to wax.

`upl` is not a separate utility identity.

## authority

aws is not authoritative.

s3 metadata is external evidence.

transfer receipts are not authoritative.

this specification is canon.
