#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

python3 -m py_compile \
  "${ROOT}/runtime/cypher/engine.py" \
  "${ROOT}/runtime/cypher/compatibility_binding.py" \
  "${ROOT}/runtime/cypher/__init__.py"

PYTHONPATH="${ROOT}" \
python3 -c '
from runtime.cypher import (
    Cypher,
    CypherCompatibilityBinding,
    bind_compatibility,
)

cypher = Cypher()

health = cypher.health()
validation = cypher.validate()

assert health["healthy"] is True
assert validation["valid"] is True

binding = bind_compatibility()

assert isinstance(
    binding,
    CypherCompatibilityBinding,
)

binding.register_adapter(
    "compat:test:v1",
    "compat:test:v2",
    lambda value: {
        **value,
        "version": 2,
    },
)

request = binding.request(
    source_type="compat:test:v1",
    target_type="compat:test:v2",
    payload={
        "id": "example",
        "version": 1,
        "unknown_field": {
            "preserve": True,
        },
    },
    authority={
        "class": "constitutional-canon",
    },
    lineage={
        "parent": "example:parent",
    },
    provenance={
        "source": "focused-final-verification",
    },
    metadata={
        "compatibility": "test",
    },
    substance_owner="example:domain-owner",
    transport_owner="example:transport-owner",
)

result = binding.translate(
    request
).projection()

translation = result[
    "translation"
]

assert translation[
    "payload"
][
    "version"
] == 2

assert translation[
    "payload"
][
    "unknown_field"
] == {
    "preserve": True,
}

assert translation[
    "authority"
] == request.authority

assert translation[
    "lineage"
] == request.lineage

assert translation[
    "provenance"
] == request.provenance

assert result[
    "substance_owner"
] == "example:domain-owner"

assert result[
    "transport_owner"
] == "example:transport-owner"

assert result[
    "authority_preserved"
] is True

assert result[
    "lineage_preserved"
] is True

assert result[
    "provenance_preserved"
] is True

assert result[
    "cypher_owns_substance"
] is False

assert result[
    "cypher_owns_transport"
] is False

assert result[
    "transport_executed"
] is False

assert result[
    "authority_effect"
] == "none"

status = binding.status()

assert status[
    "normalization"
] is True

assert status[
    "serialization"
] is True

assert status[
    "deserialization"
] is True

assert status[
    "typed_translation"
] is True

assert status[
    "adapter_selection"
] is True

assert status[
    "version_adaptation"
] is True

assert status[
    "unknown_field_preservation"
] is True

assert status[
    "authority_preservation"
] is True

assert status[
    "lineage_preservation"
] is True

assert status[
    "provenance_preservation"
] is True

assert status[
    "loss_detection"
] is True

assert status[
    "cypher_owns_substance"
] is False

assert status[
    "cypher_owns_transport"
] is False

assert status[
    "cypher_executes_transport"
] is False

assert status[
    "cypher_manufactures_authority"
] is False

assert status[
    "cypher_mutates_authority"
] is False

print({
    "cypher_health": health["healthy"],
    "cypher_validation": validation["valid"],
    "typed_translation": True,
    "unknown_field_preservation": True,
    "authority_preservation": True,
    "lineage_preservation": True,
    "provenance_preservation": True,
    "substance_ownership_transfer": False,
    "transport_ownership_transfer": False,
    "transport_execution": False,
    "authority_effect": "none",
    "passed": True,
})
'

printf '%s\n' \
  'CYPHER COMPATIBILITY FINAL INTEGRATION: valid'
