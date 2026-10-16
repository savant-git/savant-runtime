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
import importlib.util
import sys
from pathlib import Path

from runtime.thryce import (
    NotaryAssuranceAdapter,
    ThryceNotaryBinding,
    bind_notary,
    notary_adapter,
)

path = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "notary/runtime/thryce_assurance.py"
)

module_name = "notary_thryce_assurance"

spec = importlib.util.spec_from_file_location(
    module_name,
    path,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(
    spec
)

sys.modules[
    module_name
] = module

try:
    spec.loader.exec_module(
        module
    )
except Exception:
    sys.modules.pop(
        module_name,
        None,
    )
    raise

binding = bind_notary(
    validators={
        "syntax": lambda value: {
            "passed": value is not None,
        },
        "schema": lambda value: {
            "passed": isinstance(
                value,
                dict,
            ),
        },
    }
)

assert isinstance(
    binding,
    ThryceNotaryBinding,
)

adapter = notary_adapter(
    validators={
        "syntax": lambda value: {
            "passed": value is not None,
        },
    }
)

assert isinstance(
    adapter,
    NotaryAssuranceAdapter,
)

packet = adapter.assure(
    subject="integration:test:thryce:notary",
    payload={
        "valid": True,
    },
    validation_layers=(
        "syntax",
    ),
    provenance={
        "source": "focused-final-verification",
    },
)

assert packet.result.passed is True
assert packet.result.authoritative is False
assert packet.result.evidence_admitted is False
assert packet.result.attested is False

notary = module.assurance(
    validators={
        "syntax": lambda value: {
            "passed": value is not None,
        },
    }
)

candidate = notary.candidate(
    subject="integration:test:notary:thryce",
    payload={
        "valid": True,
    },
    provenance={
        "source": "focused-final-verification",
    },
)

projection = notary.projection(
    candidate,
    validation_layers=(
        "syntax",
    ),
)

assert projection[
    "assurance_passed"
] is True

assert projection[
    "verification_decision"
] is None

assert projection[
    "evidence_admitted"
] is False

assert projection[
    "attested"
] is False

assert projection[
    "authority_created"
] is False

assert projection[
    "authority_mutated"
] is False

assert projection[
    "authoritative"
] is False

status = notary.status()

assert status[
    "verification_owner"
] == "exile:notary"

assert status[
    "evidence_admission_owner"
] == "exile:notary"

assert status[
    "attestation_owner"
] == "exile:notary"

assert status[
    "mechanics_owner"
] == "living:thryce"

assert status[
    "thryce_can_verify"
] is False

assert status[
    "thryce_can_admit_evidence"
] is False

assert status[
    "thryce_can_attest"
] is False

assert status[
    "thryce_can_create_authority"
] is False

print({
    "thryce_assurance_mechanics": True,
    "notary_verification_owner": True,
    "notary_evidence_admission_owner": True,
    "notary_attestation_owner": True,
    "authority_transfer": False,
    "authority_manufacture": False,
    "passed": True,
})
'

printf '%s\n' \
  'THRYCE / NOTARY FINAL INTEGRATION: valid'
