#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/runtime"

edifice="${RUNTIME}/program_edifice.py"
COMPOSITION="${RUNTIME}/program_composition.py"
PARENT="${RUNTIME}/program_parent.py"
STORE="${RUNTIME}/program_store.py"
REGISTRY="${RUNTIME}/program_registry.py"

printf '%s\n' \
    "=== PROGRAM SEGUE SEPARATION INSPECTION ==="

printf '%s\n' \
    "" \
    "=== AUTHORITATIVE edifice SEGUE ==="

grep -nE \
    'class ProgramedificeSegue|PROGRAM_edifice_SEGUES|authoritative|authority_effect|functional_role|semantic_axis|parent_instance|child_instance' \
    "${edifice}" \
    || true

printf '%s\n' \
    "" \
    "=== NON-AUTHORITATIVE CODE SEGUE ==="

grep -nE \
    'class CodeSegue|authoritative|authority_state|segue_type|source:|target:' \
    "${COMPOSITION}" \
    || true

printf '%s\n' \
    "" \
    "=== CONCRETE SEGUE CREATION ==="

grep -nE \
    'CodeSegue\(|ProgramedificeSegue\(|add_segue|segue_type=' \
    "${COMPOSITION}" \
    "${PARENT}" \
    || true

printf '%s\n' \
    "" \
    "=== PERSISTENCE OF CONCRETE SEGUES ==="

grep -nE \
    'CodeSegue|segues|authoritative|authority_state' \
    "${STORE}" \
    "${REGISTRY}" \
    || true

printf '%s\n' \
    "" \
    "=== POSSIBLE AUTHORITY LEAK ==="

grep -nE \
    'ProgramedificeSegue|PROGRAM_edifice_SEGUES' \
    "${COMPOSITION}" \
    "${PARENT}" \
    "${STORE}" \
    "${REGISTRY}" \
    || true

printf '%s\n' \
    "" \
    "=== RESULT ===" \
    "PROGRAM SEGUE SEPARATION INSPECTION: complete"
