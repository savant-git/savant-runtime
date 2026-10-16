# policy:supersession

> generated projection. edit authority yaml, not this file.

- id: `policy:supersession`
- kind: `policy`
- status: `canonical`
- version: `1`

## rules

- never delete authoritative history
- a replacement record must declare supersedes
- the replaced record must be marked superseded
- semantic identity remains stable across versions
- breaking changes require migration notes

## future slots

- branching_supersession
- merge_resolution
- signature_policy

## open questions

_none_

## authority

### state

canonical

### tier

0

### confidence

1.0

## lineage

### parents

- foundation:dynamic-canon

### supersedes

_none_

### superseded by

_none_

## provenance

### created at

2026-07-11T00:00:00Z

### created by

canon_bootstrap

### sources

- user directive

## dependencies

- foundation:dynamic-canon

## relationships

_none_

## attachments

_none_
