#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
NICHE_RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/niche/runtime/dryve_lifecycle.py"
OPUS_RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus/runtime/dryve_lifecycle.py"

python3 -m py_compile \
  "${ROOT}/runtime/dryve/engine.py" \
  "${ROOT}/runtime/dryve/owner_binding.py" \
  "${ROOT}/runtime/dryve/__init__.py" \
  "${NICHE_RUNTIME}" \
  "${OPUS_RUNTIME}"

PYTHONPATH="${ROOT}" \
python3 -c '
import importlib.util
import sys
from pathlib import Path

from runtime.dryve import (
    Dryve,
    DryveOwnerBinding,
    bind_owners,
)

root = Path("/root/savant-runtime")

dryve = Dryve()

health = dryve.health()
validation = dryve.validate()

assert health["healthy"] is True
assert validation["valid"] is True

binding = bind_owners()

assert isinstance(
    binding,
    DryveOwnerBinding,
)

status = binding.status()

assert status["dryve_owns_execution_lifecycle"] is True
assert status["dryve_owns_task_governance"] is False
assert status["dryve_may_transition_tasks"] is False
assert status["niche_owns_task_governance"] is True
assert status["niche_owns_task_transitions"] is True

assert status["dryve_owns_provider_execution"] is False
assert status["dryve_may_access_providers"] is False
assert status["dryve_may_access_secrets"] is False
assert status["opus_owns_provider_execution"] is True
assert status["opus_owns_provider_routing"] is True
assert status["opus_owns_provider_credentials"] is True

def load(name, path):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[name] = module

    try:
        spec.loader.exec_module(
            module
        )
    except Exception:
        sys.modules.pop(
            name,
            None,
        )
        raise

    return module

niche_module = load(
    "niche_dryve_lifecycle",
    root
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
      "innates/_template/segue/exiles/niche/runtime/dryve_lifecycle.py",
)

opus_module = load(
    "opus_dryve_lifecycle",
    root
    / "ontology/obelisks/_template/segue/gates/_template/segue/"
      "innates/_template/segue/exiles/opus/runtime/dryve_lifecycle.py",
)

niche = niche_module.lifecycle()

task = niche.prepare(
    task_id="task:test:final",
    operation="execute-task-work",
    payload={
        "work": "focused-final-check",
    },
    task_state="ready",
    priority="normal",
    dependencies=(
        "task:test:dependency",
    ),
)

task_projection = task.projection()
niche_status = niche.status()

assert task_projection["owner"] == "exile:niche"
assert task_projection["mechanics_owner"] == "living:dryve"
assert task_projection["task_governance_owner"] == "exile:niche"
assert task_projection["task_transition_authorized_by_dryve"] is False

assert niche_status["task_governance_owner"] == "exile:niche"
assert niche_status["task_transition_owner"] == "exile:niche"
assert niche_status["execution_lifecycle_mechanics"] == "living:dryve"
assert niche_status["dryve_may_transition_tasks"] is False
assert niche_status["dryve_may_schedule_tasks"] is False

opus = opus_module.lifecycle()

execution = opus.prepare(
    execution_id="execution:test:final",
    operation="text-inference",
    payload={
        "message": "focused-final-check",
    },
    provider_route="text-inference-route",
    model_route="default-model-route",
    retry_policy={
        "owner": "exile:opus",
        "maximum_attempts": 1,
    },
)

execution_projection = execution.projection()
opus_status = opus.status()

assert execution_projection["owner"] == "exile:opus"
assert execution_projection["mechanics_owner"] == "living:dryve"
assert execution_projection["provider_execution_owner"] == "exile:opus"
assert execution_projection["provider_routing_owner"] == "exile:opus"
assert execution_projection["provider_credentials_owner"] == "exile:opus"
assert execution_projection["provider_access_authorized_by_dryve"] is False
assert execution_projection["provider_selection_authorized_by_dryve"] is False

assert opus_status["provider_execution_owner"] == "exile:opus"
assert opus_status["provider_routing_owner"] == "exile:opus"
assert opus_status["model_selection_owner"] == "exile:opus"
assert opus_status["provider_credentials_owner"] == "exile:opus"
assert opus_status["execution_lifecycle_mechanics"] == "living:dryve"
assert opus_status["dryve_may_execute_provider_calls"] is False
assert opus_status["dryve_may_access_provider_credentials"] is False
assert opus_status["dryve_may_select_provider"] is False
assert opus_status["dryve_may_select_model"] is False

print({
    "dryve_health": health["healthy"],
    "dryve_validation": validation["valid"],
    "execution_lifecycle_owner": "living:dryve",
    "task_governance_owner": "exile:niche",
    "provider_execution_owner": "exile:opus",
    "authority_transfer": False,
    "passed": True,
})
'

printf '%s\n' \
  'DRYVE / NICHE / OPUS FINAL INTEGRATION: valid'
