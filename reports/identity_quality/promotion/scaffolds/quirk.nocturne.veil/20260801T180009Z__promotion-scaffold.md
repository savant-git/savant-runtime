# Identity Promotion Scaffold

- Generated: `2026-08-01T18:00:09+00:00`
- Digest: `4d27028ebc3aeb54d2976cae14cf61e054d4f0e04f58aa12c4e879506fe5fcb5`
- Subject: `quirk.nocturne.veil`
- Kind: `quirk`
- Parent: `prodigal.nocturne`

## Actions

1. `extend` `definition` at `edifices/identity/exiles/opus/prodigals/nocturne/quirks/veil/definition.json`
2. `create` `contracts` at `edifices/identity/exiles/opus/prodigals/nocturne/quirks/veil/contracts/veil_contracts.py`
3. `extend` `runtime` at `edifices/identity/exiles/opus/prodigals/nocturne/quirks/veil/runtime/veil_runtime.py`
4. `extend` `tests` at `edifices/identity/exiles/opus/prodigals/nocturne/quirks/veil/tests/test_veil_runtime.py`
5. `extend` `controller` at `bin/veilctl`
6. `create` `reports` at `reports/identity_quality/veil`
7. `extend` `definition_attachment` at `edifices/identity/exiles/opus/prodigals/nocturne/quirks/veil/definition.json`
8. `create_or_extend` `parent_attachment` at `None`
9. `create_or_extend` `quality_verifier` at `bin/veil-quality-verify`
10. `create_or_extend` `attestation_builder` at `tools/identity_quality/promotion/attestations/veil/build_reference_attestation.py`

## Contracts

- Request: `VeilRequest`
- Policy: `VeilPolicy`
- Result: `VeilResult`

## Runtime

- Runtime behavior must derive from the authoritative definition.
- Runtime must remain independently useful.
- Runtime must fail closed when authority or implementation evidence is absent.
- Equal requests must produce equal authoritative result digests.
- Volatile telemetry must remain outside deterministic identity.
- No undeclared network, subprocess, filesystem, provider, or secret authority.
- Every result must preserve lineage and provenance.

## Tests

- `test_example_request_succeeds`
- `test_equal_requests_produce_equal_result_digests`
- `test_canonical_serialization_is_stable`
- `test_result_preserves_provenance`
- `test_runtime_fails_closed_without_authority`
- `test_runtime_rejects_undeclared_capability`
- `test_volatile_telemetry_does_not_change_identity`
- `test_parent_authority_is_not_inherited`

## Authority Boundary

- Parent retains its declared authority.
- Subject retains its internal authority.
- No secrets, provider selection, registry mutation, or policy bypass is inherited.
- Attachment is contract-governed.
- Attachment failures preserve reasons and provenance.
