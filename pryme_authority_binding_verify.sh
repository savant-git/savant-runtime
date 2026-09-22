#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

python3 -m py_compile \
  "${ROOT}/runtime/pryme/engine.py" \
  "${ROOT}/runtime/pryme/authority_binding.py" \
  "${ROOT}/runtime/pryme/__init__.py"

PYTHONPATH="${ROOT}" \
python3 -c '
from runtime.constitution import ConstitutionalRegistry
from runtime.pryme import (
    Pryme,
    PrymeAuthorityBinding,
    bind,
)

root = "/root/savant-runtime"

registry = ConstitutionalRegistry.load(root)
pryme = Pryme()

binding = bind(
    registry,
    pryme,
)

assert isinstance(
    binding,
    PrymeAuthorityBinding,
)

records = binding.records()

assert records
assert len(records) == len(
    {
        record.identity
        for record in records
    }
)

assert all(
    record.source
    for record in records
)

assert all(
    record.fingerprint
    for record in records
)

status = binding.status()

assert status["valid"] is True
assert status["authority_manufactured"] is False
assert status["authority_mutated"] is False

projection = binding.projection()

assert projection["source_authority_preserved"] is True
assert projection["authority_manufactured"] is False
assert projection["authority_mutated"] is False
assert projection["authoritative"] is False
assert projection["rebuildable"] is True

print({
    "registry_objects": len(
        registry.values()
    ),
    "bound_records": len(records),
    "unique_identities": True,
    "authority_manufactured": False,
    "authority_mutated": False,
    "source_authority_preserved": True,
    "passed": True,
})
'

PYTHONPATH="${ROOT}" \
python3 -c '
import runtime.pryme

required = (
    "Pryme",
    "PrymeAuthorityBinding",
    "PrymeAuthorityBindingError",
    "bind",
    "bind_registry",
)

missing = [
    name
    for name in required
    if not hasattr(
        runtime.pryme,
        name,
    )
]

assert not missing, missing

print({
    "package_exports": "valid",
    "passed": True,
})
'

printf '%s\n' \
  'PRYME AUTHORITY BINDING: valid'
