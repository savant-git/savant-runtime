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
binding = bind(registry, pryme)

assert isinstance(binding, PrymeAuthorityBinding)

records = binding.records()
assert records
assert len(records) == len({record.identity for record in records})

health = pryme.health()
validation = pryme.validate()
binding_status = binding.status()

assert health["healthy"] is True
assert validation["valid"] is True
assert binding_status["valid"] is True

assert validation["mutation_authorized"] is False
assert validation["authority_manufacture_authorized"] is False
assert validation["confidence_used_for_precedence"] is False
assert validation["status_used_for_precedence"] is False
assert validation["filesystem_used_for_precedence"] is False

projection = binding.projection()

assert projection["authority_manufactured"] is False
assert projection["authority_mutated"] is False
assert projection["source_authority_preserved"] is True
assert projection["authoritative"] is False
assert projection["rebuildable"] is True

print({
    "registry_objects": len(registry.values()),
    "bound_records": len(records),
    "precedence_count": validation["authority_precedence_count"],
    "health": health["healthy"],
    "validation": validation["valid"],
    "authority_manufactured": False,
    "authority_mutated": False,
    "source_authority_preserved": True,
    "passed": True,
})
'

PYTHONPATH="${ROOT}" \
python3 -c '
from runtime.pryme import Pryme

pryme = Pryme()

assert pryme.substrate_id == "living:pryme"
assert len(pryme.precedence) == 11

print({
    "substrate": pryme.substrate_id,
    "precedence": list(pryme.precedence),
    "passed": True,
})
'

printf '%s\n' \
  'PRYME FINAL INTEGRATION: valid'
