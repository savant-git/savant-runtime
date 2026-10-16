#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
CODA_RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/coda/runtime"

python3 -m py_compile \
  "${ROOT}/runtime/spyral/engine.py" \
  "${ROOT}/runtime/spyral/coda_binding.py" \
  "${ROOT}/runtime/spyral/__init__.py" \
  "${CODA_RUNTIME}/mutation.py" \
  "${CODA_RUNTIME}/spyral_transition.py"

PYTHONPATH="${ROOT}" \
python3 -c '
import importlib.util
import sys
from pathlib import Path

from runtime.spyral import (
    Spyral,
    SpyralCodaBinding,
    bind_coda,
)

root = Path("/root/savant-runtime")

spyral = Spyral()

health = spyral.health()
validation = spyral.validate()

assert health["healthy"] is True
assert validation["valid"] is True
assert validation["mutation_authorized"] is False
assert validation["migration_execution_authorized"] is False

binding = bind_coda()

assert isinstance(
    binding,
    SpyralCodaBinding,
)

transition = spyral.plan(
    subject_id="integration:test:spyral-coda",
    baseline={
        "id": "integration:test:spyral-coda",
        "version": "1.0.0",
    },
    target={
        "id": "integration:test:spyral-coda",
        "version": "1.1.0",
    },
    migration_steps=(
        {
            "operation": "replace_text",
        },
    ),
    recovery_steps=(
        {
            "operation": "restore_previous",
        },
    ),
    provenance={
        "source": "focused-final-verification",
    },
)

request = binding.request(
    transition=transition,
    path="runtime/spyral/final-verification-target.txt",
    content="spyral-coda-final-verification\n",
    authority_witness={
        "id": "authority-witness:focused-final-verification",
        "current": True,
    },
)

projection = request.projection()

assert projection["owner"] == "living:spyral"
assert projection["mutation_owner"] == "coda"
assert projection["spyral_authorizes_mutation"] is False
assert projection["spyral_executes_mutation"] is False
assert projection["coda_must_authorize_commit"] is True
assert projection["coda_must_validate_current_authority"] is True
assert projection["mutation_performed"] is False

module_path = (
    root
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
      "innates/_template/segue/exiles/coda/runtime/spyral_transition.py"
)

module_name = "coda_spyral_transition"

spec = importlib.util.spec_from_file_location(
    module_name,
    module_path,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(
    spec
)

sys.modules[module_name] = module

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

runtime = module.bind_spyral(
    authority_validator=lambda witness: {
        "passed": (
            isinstance(
                witness,
                dict,
            )
            and witness.get(
                "current"
            )
            is True
        ),
    },
)

status = runtime.status()

assert status["mutation_owner"] == "coda"
assert status["commit_owner"] == "coda"
assert status["authority_validation_owner"] == "coda"
assert status["authority_checked_at_commit"] is True
assert status["spyral_authorizes_mutation"] is False
assert status["spyral_executes_mutation"] is False
assert status["coda_authorizes_commit"] is True
assert status["coda_executes_mutation"] is True

target = (
    root
    / "runtime/spyral/final-verification-target.txt"
)

target.unlink(
    missing_ok=True
)

receipt = runtime.commit(
    projection
)

receipt_projection = (
    receipt.projection()
)

assert target.read_text(
    encoding="utf-8"
) == "spyral-coda-final-verification\n"

assert receipt_projection["owner"] == "coda"
assert receipt_projection["planning_owner"] == "living:spyral"
assert receipt_projection["mutation_owner"] == "coda"
assert receipt_projection["commit_owner"] == "coda"
assert receipt_projection["spyral_executed_mutation"] is False
assert receipt_projection["spyral_authorized_mutation"] is False
assert receipt_projection["authority_checked_at_commit"] is True
assert receipt_projection["mutation"]["atomic"] is True
assert receipt_projection["mutation"]["verified"] is True

target.unlink(
    missing_ok=True
)

print({
    "spyral_health": health["healthy"],
    "spyral_validation": validation["valid"],
    "planning_owner": "living:spyral",
    "mutation_owner": "coda",
    "commit_owner": "coda",
    "authority_checked_at_commit": True,
    "atomic_mutation": True,
    "digest_verified": True,
    "spyral_mutation": False,
    "passed": True,
})
'

printf '%s\n' \
  'SPYRAL / CODA FINAL INTEGRATION: valid'
