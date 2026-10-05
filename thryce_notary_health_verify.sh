#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
NOTARY_RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/notary/runtime"

python3 -m py_compile \
  "${ROOT}/runtime/thryce/engine.py" \
  "${ROOT}/runtime/thryce/notary_binding.py" \
  "${ROOT}/runtime/thryce/notary_adapter.py" \
  "${ROOT}/runtime/thryce/__init__.py" \
  "${NOTARY_RUNTIME}/thryce_assurance.py"

PYTHONPATH="${ROOT}" \
python3 -c '
from runtime.thryce import (
    Thryce,
    bind_notary,
    notary_adapter,
)

thryce = Thryce()

health = thryce.health()
validation = thryce.validate()

assert health["healthy"] is True
assert validation["valid"] is True

binding = bind_notary()

binding_status = binding.status()

assert binding_status["thryce_may_validate"] is True
assert binding_status["thryce_may_assure"] is True
assert binding_status["thryce_may_admit_evidence"] is False
assert binding_status["thryce_may_attest"] is False
assert binding_status["thryce_may_create_authority"] is False

adapter = notary_adapter()

adapter_status = adapter.status()

assert adapter_status["verification_owner"] == "exile:notary"
assert adapter_status["delegation"]["validation_mechanics"] == "thryce"
assert adapter_status["delegation"]["verification_decision"] == "notary"
assert adapter_status["delegation"]["evidence_admission"] == "notary"
assert adapter_status["delegation"]["attestation"] == "notary"

print({
    "thryce_health": health["healthy"],
    "thryce_validation": validation["valid"],
    "assurance_binding": True,
    "verification_owner": "exile:notary",
    "evidence_admission_owner": "exile:notary",
    "attestation_owner": "exile:notary",
    "authority_effect": "none",
    "passed": True,
})
'

printf '%s\n' \
  'THRYCE / NOTARY HEALTH INTEGRATION: valid'
