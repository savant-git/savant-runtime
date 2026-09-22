#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/runtime"

STORE="${RUNTIME}/program_store.py"
REGISTRY="${RUNTIME}/program_registry.py"

printf '%s\n' \
    "=== PROGRAM STORE / REGISTRY AUTHORITY INSPECTION ==="

for file in \
    "${STORE}" \
    "${REGISTRY}"
do
    printf '\n=== FILE: %s ===\n' "${file}"

    printf '%s\n' \
        "--- edifice references ---"

    grep -nE \
        'PROGRAM_edifice_SEGUES|PROGRAM_edifice_LINEAGE|PROGRAM_LEVELS|PROGRAM_LEVEL_INDEX|PROGRAM_CHILD_LEVEL|PROGRAM_PARENT_LEVEL|Programedifice' \
        "${file}" \
        || true

    printf '%s\n' \
        "--- possible topology definitions ---"

    grep -nE \
        '^[[:space:]]*(PROGRAM_edifice_SEGUES|PROGRAM_edifice_LINEAGE|PROGRAM_LEVELS|PROGRAM_LEVEL_INDEX|PROGRAM_CHILD_LEVEL|PROGRAM_PARENT_LEVEL)[[:space:]]*=' \
        "${file}" \
        || true

    printf '%s\n' \
        "--- authority semantics ---"

    grep -nEi \
        'authoritative|authority_state|authority_effect|authority|accepted|canonical|canon|source_of_truth' \
        "${file}" \
        || true

    printf '%s\n' \
        "--- persistence operations ---"

    grep -nEi \
        'write_text|write_bytes|json\.dump|json\.dumps|mkdir|replace|rename|sqlite|insert|update|save|store|persist|registry' \
        "${file}" \
        || true

    printf '%s\n' \
        "--- edifice material persisted ---"

    grep -nEi \
        'levels|segues|lineage|parent|child|projection|manifest|digest' \
        "${file}" \
        || true
done

printf '%s\n' \
    "" \
    "=== RESULT ===" \
    "PROGRAM STORE / REGISTRY AUTHORITY INSPECTION: complete"
