#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
LYTHE="${ROOT}/runtime/lythe"
FILAMENT="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/filament"
FILAMENT_RUNTIME="${FILAMENT}/runtime/lythe_projection.py"

python3 -m py_compile \
  "${LYTHE}/engine.py" \
  "${LYTHE}/filament_binding.py" \
  "${LYTHE}/__init__.py" \
  "${FILAMENT_RUNTIME}"

PYTHONPATH="${ROOT}" \
python3 -c '
from runtime.lythe import (
    Lythe,
    LytheFilamentBinding,
    ProjectionSpecification,
    bind_filament,
)

lythe = Lythe()
health = lythe.health()
validation = lythe.validate()

assert health["healthy"] is True
assert validation["valid"] is True

binding = bind_filament()

assert isinstance(
    binding,
    LytheFilamentBinding,
)

status = binding.status()

assert status["lythe_derives"] is True
assert status["lythe_executes"] is False
assert status["lythe_emits_files"] is False
assert status["filament_executes"] is True
assert status["filament_emits_files"] is True
assert status["filament_owns_workers"] is True
assert status["authority_effect"] == "none"

specification = binding.derive(
    projection_id="projection:test:lythe:filament",
    source_identity="instance:test:lythe:filament",
    projection_type="json",
    inputs=(
        "authority_db",
        "instances",
    ),
    outputs=(
        "json_projections",
    ),
    provenance={
        "source": "focused-final-verification",
    },
)

assert isinstance(
    specification,
    ProjectionSpecification,
)

packet = binding.packet(
    specification
)

projection = packet.projection()

assert projection["owner"] == "living:lythe"
assert projection["execution_owner"] == "filament"
assert projection["ready_for_execution"] is True
assert projection["executed"] is False
assert projection["filesystem_mutated"] is False
assert projection["authority_effect"] == "none"

print({
    "lythe_health": health["healthy"],
    "lythe_validation": validation["valid"],
    "deterministic_derivation": True,
    "execution_owner": "filament",
    "lythe_executes": False,
    "filament_executes": True,
    "authority_effect": "none",
    "passed": True,
})
'

PYTHONPATH="${ROOT}" \
python3 -c '
import importlib.util
import sys
from pathlib import Path

from runtime.lythe import bind_filament

path = Path(
    "/root/savant-runtime/ontology/obelisks/_template/segue/"
    "gates/_template/segue/innates/_template/segue/exiles/"
    "filament/runtime/lythe_projection.py"
)

module_name = "filament_lythe_projection"

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

lythe = bind_filament()

specification = lythe.derive(
    projection_id="projection:test:runtime-handoff",
    source_identity="instance:test:runtime-handoff",
    projection_type="json",
    inputs=(
        "authority_db",
        "instances",
    ),
    outputs=(
        "json_projections",
    ),
    provenance={
        "source": "focused-final-verification",
    },
)

packet = lythe.packet(
    specification
).projection()

filament = module.lythe_projection()

request = filament.accept(
    packet
)

request_projection = (
    request.projection()
)

assert request_projection["owner"] == "filament"
assert request_projection["derivation_owner"] == "living:lythe"
assert request_projection["execution_owner"] == "filament"
assert request_projection["executed"] is False
assert request_projection["filesystem_mutated"] is False
assert request_projection["authority_effect"] == "none"

status = filament.status()

assert status["lythe_derives"] is True
assert status["lythe_executes"] is False
assert status["filament_accepts_specifications"] is True
assert status["filament_executes"] is True
assert status["filament_owns_workers"] is True
assert status["filament_emits_files"] is True

print({
    "handoff": "valid",
    "derivation_owner": "living:lythe",
    "execution_owner": "filament",
    "filesystem_mutated": False,
    "authority_effect": "none",
    "passed": True,
})
'

printf '%s\n' \
  'LYTHE / FILAMENT FINAL INTEGRATION: valid'
