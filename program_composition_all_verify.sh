#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/runtime"

edifice="${RUNTIME}/program_edifice.py"
COMPOSITION="${RUNTIME}/program_composition.py"
PARENT="${RUNTIME}/program_parent.py"
ENGINE="${RUNTIME}/program_engine.py"
SUBSYSTEM="${RUNTIME}/program_subsystem.py"
SYSTEM="${RUNTIME}/program_system.py"
APPLICATION="${RUNTIME}/program_application.py"
STORE="${RUNTIME}/program_store.py"
REGISTRY="${RUNTIME}/program_registry.py"
INIT="${RUNTIME}/__init__.py"

edifice_VERIFY="${ROOT}/program_edifice_verify.py"
edifice_SEGUE_VERIFY="${ROOT}/program_edifice_segue_verify.py"
SINGLE_AUTHORITY_VERIFY="${ROOT}/program_edifice_single_authority_verify.py"
COMPOSITION_VERIFY="${ROOT}/program_composition_verify.py"
STORE_VERIFY="${ROOT}/program_store_verify.py"
REGISTRY_VERIFY="${ROOT}/program_registry_verify.py"
ENGINE_VERIFY="${ROOT}/program_engine_verify.py"
SUBSYSTEM_VERIFY="${ROOT}/program_subsystem_verify.py"
SYSTEM_VERIFY="${ROOT}/program_system_verify.py"
APPLICATION_VERIFY="${ROOT}/program_application_verify.py"
PARENT_VERIFY="${ROOT}/program_parent_verify.py"
EXPORTS_VERIFY="${ROOT}/program_modus_exports_verify.py"

VERIFY_PYTHONPATH="${RUNTIME}:${ROOT}"


section() {
    printf '\n=== %s ===\n' "$1"
}


pass() {
    printf 'PASS  %s\n' "$1"
}


require_file() {
    local path="$1"

    if [[ ! -f "${path}" ]]; then
        printf \
            'FAIL  missing required file: %s\n' \
            "${path}" \
            >&2

        exit 1
    fi

    pass "${path}"
}


run_python_verifier() {
    local label="$1"
    local path="$2"

    section "${label}"

    PYTHONPATH="${VERIFY_PYTHONPATH}${PYTHONPATH:+:${PYTHONPATH}}" \
        python3 "${path}"

    pass "${label}"
}


section "SAVANT PROGRAM COMPOSITION VERIFICATION"


section "1. REQUIRED FILES"

for path in \
    "${edifice}" \
    "${COMPOSITION}" \
    "${PARENT}" \
    "${ENGINE}" \
    "${SUBSYSTEM}" \
    "${SYSTEM}" \
    "${APPLICATION}" \
    "${STORE}" \
    "${REGISTRY}" \
    "${INIT}" \
    "${edifice_VERIFY}" \
    "${edifice_SEGUE_VERIFY}" \
    "${SINGLE_AUTHORITY_VERIFY}" \
    "${COMPOSITION_VERIFY}" \
    "${STORE_VERIFY}" \
    "${REGISTRY_VERIFY}" \
    "${ENGINE_VERIFY}" \
    "${SUBSYSTEM_VERIFY}" \
    "${SYSTEM_VERIFY}" \
    "${APPLICATION_VERIFY}" \
    "${PARENT_VERIFY}" \
    "${EXPORTS_VERIFY}"
do
    require_file "${path}"
done


section "2. PYTHON SYNTAX"

python3 -m py_compile \
    "${edifice}" \
    "${COMPOSITION}" \
    "${PARENT}" \
    "${ENGINE}" \
    "${SUBSYSTEM}" \
    "${SYSTEM}" \
    "${APPLICATION}" \
    "${STORE}" \
    "${REGISTRY}" \
    "${INIT}" \
    "${edifice_VERIFY}" \
    "${edifice_SEGUE_VERIFY}" \
    "${SINGLE_AUTHORITY_VERIFY}" \
    "${COMPOSITION_VERIFY}" \
    "${STORE_VERIFY}" \
    "${REGISTRY_VERIFY}" \
    "${ENGINE_VERIFY}" \
    "${SUBSYSTEM_VERIFY}" \
    "${SYSTEM_VERIFY}" \
    "${APPLICATION_VERIFY}" \
    "${PARENT_VERIFY}" \
    "${EXPORTS_VERIFY}"

pass "Python syntax"


run_python_verifier \
    "3. edifice" \
    "${edifice_VERIFY}"


run_python_verifier \
    "4. edifice SEGUES" \
    "${edifice_SEGUE_VERIFY}"


run_python_verifier \
    "5. SINGLE edifice AUTHORITY" \
    "${SINGLE_AUTHORITY_VERIFY}"


run_python_verifier \
    "6. BASE BYTE-FOR-BYTE COMPOSITION" \
    "${COMPOSITION_VERIFY}"


run_python_verifier \
    "7. COMPOSITION STORE" \
    "${STORE_VERIFY}"


run_python_verifier \
    "8. PROJECTION REGISTRY" \
    "${REGISTRY_VERIFY}"


run_python_verifier \
    "9. SCRIPT TO ENGINE" \
    "${ENGINE_VERIFY}"


run_python_verifier \
    "10. ENGINE TO SUBSYSTEM" \
    "${SUBSYSTEM_VERIFY}"


run_python_verifier \
    "11. SUBSYSTEM TO SYSTEM" \
    "${SYSTEM_VERIFY}"


run_python_verifier \
    "12. SYSTEM TO APPLICATION" \
    "${APPLICATION_VERIFY}"


run_python_verifier \
    "13. GENERIC PARENT COMPOSITION" \
    "${PARENT_VERIFY}"


run_python_verifier \
    "14. MODUS RUNTIME EXPORTS" \
    "${EXPORTS_VERIFY}"


section "15. edifice AUTHORITY INTEGRATION"

PYTHONPATH="${VERIFY_PYTHONPATH}${PYTHONPATH:+:${PYTHONPATH}}" \
python3 - <<'PY'
import program_edifice


edifice = (
    program_edifice.Programedifice()
)

expected_levels = (
    "character",
    "line",
    "segment",
    "snippet",
    "script",
    "engine",
    "subsystem",
    "system",
    "application",
)

segues = (
    program_edifice
    .PROGRAM_edifice_SEGUES
)

if len(segues) != 8:
    raise RuntimeError(
        "authoritative edifice "
        "must contain 8 segues"
    )

if (
    program_edifice
    .PROGRAM_LEVELS
    != expected_levels
):
    raise RuntimeError(
        "nine-level edifice mismatch"
    )

if (
    program_edifice
    .project_program_levels(
        segues
    )
    != expected_levels
):
    raise RuntimeError(
        "levels are not derived from "
        "authoritative segues"
    )

if (
    edifice.path(
        "character",
        "application",
    )
    != expected_levels
):
    raise RuntimeError(
        "full edifice path mismatch"
    )

if (
    edifice.distance(
        "character",
        "application",
    )
    != 8
):
    raise RuntimeError(
        "full edifice distance "
        "must be 8"
    )

if (
    edifice.segue_path(
        "character",
        "application",
    )
    != segues
):
    raise RuntimeError(
        "full segue path differs from "
        "authoritative segue sequence"
    )

validation = (
    edifice.validate()
)

if (
    validation["valid"]
    is not True
):
    raise RuntimeError(
        "edifice validation failed"
    )

if (
    validation[
        "authority_primitive"
    ]
    != "PROGRAM_edifice_SEGUES"
):
    raise RuntimeError(
        "edifice authority primitive "
        "mismatch"
    )

print(
    "PASS  single authoritative "
    "PROGRAM_edifice_SEGUES topology"
)

print(
    "PASS  9 projected levels"
)

print(
    "PASS  8 authoritative transitions"
)
PY


section "16. MODUS PACKAGE IMPORT"

PYTHONPATH="${VERIFY_PYTHONPATH}${PYTHONPATH:+:${PYTHONPATH}}" \
python3 - <<'PY'
import importlib.util
import sys
from pathlib import Path


runtime = Path(
    "/root/savant-runtime/ontology/obelisks/"
    "_template/segue/gates/_template/segue/"
    "innates/_template/segue/exiles/modus/runtime"
)

spec = (
    importlib.util
    .spec_from_file_location(
        "modus_runtime",
        runtime / "__init__.py",
        submodule_search_locations=[
            str(
                runtime
            )
        ],
    )
)

if (
    spec is None
    or spec.loader is None
):
    raise RuntimeError(
        "cannot load Modus runtime"
    )

module = (
    importlib.util
    .module_from_spec(
        spec
    )
)

sys.modules[
    "modus_runtime"
] = module

spec.loader.exec_module(
    module
)

required = (
    "PROGRAM_edifice_SEGUES",
    "PROGRAM_edifice_LINEAGE",
    "PROGRAM_LEVELS",
    "PROGRAM_LEVEL_INDEX",
    "PROGRAM_CHILD_LEVEL",
    "PROGRAM_PARENT_LEVEL",
    "Programedifice",
    "ProgramedificeSegue",
    "ProgramCompositionGraph",
    "ProgramInstance",
    "CodeSegue",
    "ProgramCompositionStore",
    "ProgramProjectionRegistry",
    "ProgramParentComposer",
    "ProgramEngineComposer",
    "ProgramSubsystemComposer",
    "ProgramSystemComposer",
    "ProgramApplicationComposer",
)

missing = tuple(
    name
    for name in required
    if not hasattr(
        module,
        name,
    )
)

if missing:
    raise RuntimeError(
        "missing Modus runtime exports: "
        + ", ".join(
            missing
        )
    )

print(
    "PASS  Modus runtime public surface"
)
PY


section "17. LIVE RUNTIME COMPATIBILITY"

PYTHONPATH="${ROOT}" \
python3 - <<'PY'
import runtime.cypher
import runtime.spyral

print(
    "PASS  runtime.cypher import"
)

print(
    "PASS  runtime.spyral import"
)
PY


section "18. RESULT"

printf '%s\n' \
    "PROGRAM COMPOSITION: valid" \
    "PROGRAM edifice LEVELS: 9" \
    "PROGRAM edifice TRANSITIONS: 8" \
    "PROGRAM edifice AUTHORITY: PROGRAM_edifice_SEGUES" \
    "PROGRAM edifice AUTHORITY COUNT: 1" \
    "PROGRAM edifice SEGUES: 8 authoritative" \
    "PROGRAM LEVELS: deterministic projection" \
    "PROGRAM CHILD/PARENT MAPS: deterministic projection" \
    "CONCRETE CODE SEGUES: non-authoritative" \
    "PROGRAM STORE: non-authoritative" \
    "PROGRAM REGISTRY: non-authoritative" \
    "SAVANT PROGRAM COMPOSITION VERIFICATION: PASS"
