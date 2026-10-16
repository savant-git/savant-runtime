# carbon avatar forge api

## owner

carbon

## status

active

## purpose

avatar forge is carbon's embodied-simulation ingress and substrate-projection application.

it receives explicitly consented source material and projects normalized, stable, inspectable, reusable embodiment manifests.

## canonical runtime

`apps/avatar_forge/run.sh`

## application

`avatar_forge.api.main:app`

## network defaults

host: `127.0.0.1`

port: `8787`

runtime overrides:

- `CARBON_AVATAR_FORGE_HOST`
- `CARBON_AVATAR_FORGE_PORT`

## projection surfaces

avatar forge may expose:

- source intake
- consent state
- normalized embodiment packets
- identity manifests
- texture projection manifests
- voice profile manifests
- rig export manifests
- packet audits
- lineage
- provenance
- compatibility metadata

## invariants

- explicit consent is required for represented-person reconstruction.
- source possession does not establish consent.
- generated structures are projections, not new identity authority.
- source lineage must remain recoverable.
- provenance must remain attached where available.
- downstream composition does not transfer carbon authority.
- external reconstruction backends may extend avatar forge without replacing its canonical ownership.
- external provider execution remains owned by the appropriate provider-orchestration element.
