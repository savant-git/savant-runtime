# accepted decision: wax, wane, and markdown specification placement

decision id: ad-20261003-002

status: accepted

accepted: 2026-10-03

authority: current user directive

## markdown specification canon

all savant-owned markdown specification files belong beneath:

`/root/savant-runtime/canon/specifications/`

markdown specifications must not establish parallel specification roots
elsewhere in the runtime.

accepted decisions and formal authority records represented as markdown belong
beneath:

`/root/savant-runtime/canon/authority/`

the historical top-level `/root/savant-runtime/authority` path may remain only
as a compatibility projection resolving into canon.

the historical top-level `/root/savant-runtime/specifications` path may remain
only as a compatibility projection resolving into canon.

filesystem compatibility does not create duplicate authority.

## wax

canonical name: `wax`

kind: tactic

edifice: utility

wax transfers admitted local savant-runtime files outward to
`s3://savant-ai-cluster/`.

an individually supplied file is uploaded to bucket root using its basename.

a supplied directory is uploaded beneath bucket root using the directory
basename as its root and preserving its internal relative structure.

wax never silently introduces an uploads prefix.

wax does not own aws credentials.

wax does not expose aws-specific semantics outside its provider boundary.

## wane

canonical name: `wane`

kind: tactic

edifice: utility

wane transfers admitted objects from `s3://savant-ai-cluster/` inward.

wane always writes relative to the directory from which wane is invoked.

wane never redirects downloads into `s3_downloads`, `downloads`, `portable`,
or another implicit location.

exact object downloads use the object's basename.

prefix and glob downloads preserve relative paths beneath the requested prefix.

## independent composition

wax and wane are sibling utility tactics.

each has:

- its own identity;
- its own specification;
- its own filesystem capsule;
- its own runtime entrypoint;
- its own receipts;
- its own command semantics;
- its own validation;
- its own recovery behavior.

they do not form one combined authoritative component.

provider-boundary mechanics that are identical may be reused through a
non-authoritative implementation adapter.

shared provider code does not merge the semantic identities of wax and wane.

## compatibility

`upl` is a compatibility projection of wax.

`dow` is a compatibility projection of wane.

the canonical user-facing names are wax and wane.

compatibility aliases must invoke the canonical implementation and must not
contain duplicate transfer logic.

## security

wax and wane:

- use the existing aws credential chain;
- never print credentials;
- reject paths outside `/root/savant-runtime`;
- reject traversal;
- reject foreign s3 buckets;
- refuse symlink upload traversal;
- protect sensitive-looking files by default;
- use subprocess argument vectors rather than shell interpolation;
- preserve existing destination files until a replacement download has
  completed;
- verify content integrity where wax-originated sha-256 metadata exists.

## provider boundary

aws s3 is implementation infrastructure.

external object identifiers remain external identifiers.

provider-specific mechanics terminate in the aws s3 adapter.

external provider state cannot become savant authority merely because a
transfer succeeds.

## integrity

wax computes sha-256 for uploaded files and records the digest as s3 metadata.

wane validates object size.

wane validates sha-256 when wax-originated metadata is available.

older objects without wax metadata remain downloadable.

## provenance

wax receipts live beneath:

`/root/savant-runtime/runtime/receipts/wax/`

wane receipts live beneath:

`/root/savant-runtime/runtime/receipts/wane/`

receipts are evidence and projections.

receipts are not authority.

## determinism

equivalent admitted content maps to the same object key and sha-256 identity.

wall-clock receipt timestamps and temporary paths are operational evidence and
do not participate in semantic identity.

## completion

this decision is implemented when:

- canonical markdown specifications reside under canon;
- authority markdown resides under canon;
- wax and wane occupy separate utility-edifice folders;
- wax uploads root-bound objects;
- wane downloads into its invocation directory;
- no implicit s3_downloads behavior remains;
- upl resolves to wax;
- dow resolves to wane;
- syntax validation passes;
- isolated tactic self-tests pass;
- one live s3 round-trip passes.
