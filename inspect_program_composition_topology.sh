#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/runtime"

COMPOSITION="${RUNTIME}/program_composition.py"
edifice="${RUNTIME}/program_edifice.py"

printf '%s\n' \
    "=== PROGRAM COMPOSITION TOPOLOGY INSPECTION ==="

printf '%s\n' \
    "" \
    "=== IMPORT SURFACE ==="

sed -n '1,80p' \
    "${COMPOSITION}"

printf '%s\n' \
    "" \
    "=== edifice SYMBOL REFERENCES ==="

grep -nE \
    'PROGRAM_edifice_SEGUES|PROGRAM_edifice_LINEAGE|PROGRAM_LEVELS|PROGRAM_LEVEL_INDEX|PROGRAM_CHILD_LEVEL|PROGRAM_PARENT_LEVEL|Programedifice' \
    "${COMPOSITION}" \
    || true

printf '%s\n' \
    "" \
    "=== POSSIBLE LOCAL TOPOLOGY AUTHORITY ==="

grep -nE \
    '^[[:space:]]*(PROGRAM_edifice_SEGUES|PROGRAM_edifice_LINEAGE|PROGRAM_LEVELS|PROGRAM_LEVEL_INDEX|PROGRAM_CHILD_LEVEL|PROGRAM_PARENT_LEVEL)[[:space:]]*=' \
    "${COMPOSITION}" \
    || true

printf '%s\n' \
    "" \
    "=== LEVEL LITERALS ==="

grep -nE \
    '"character"|"line"|"segment"|"snippet"|"script"|"engine"|"subsystem"|"system"|"application"' \
    "${COMPOSITION}" \
    || true

printf '%s\n' \
    "" \
    "=== CHILD/PARENT CALCULATION ==="

grep -nE \
    'child_level|parent_level|ordinal|PROGRAM_LEVEL_INDEX|PROGRAM_LEVELS' \
    "${COMPOSITION}" \
    || true

printf '%s\n' \
    "" \
    "=== DECOMPOSITION OPERATIONS ==="

grep -nE \
    '_intern_character|_intern_line|_intern_composition|decompose_text|decompose_file|level=' \
    "${COMPOSITION}" \
    || true

printf '%s\n' \
    "" \
    "=== edifice AUTHORITY SOURCE ==="

grep -nE \
    'PROGRAM_edifice_SEGUES|PROGRAM_edifice_LINEAGE|PROGRAM_LEVELS|PROGRAM_LEVEL_INDEX|PROGRAM_CHILD_LEVEL|PROGRAM_PARENT_LEVEL' \
    "${edifice}"

printf '%s\n' \
    "" \
    "=== RESULT ===" \
    "PROGRAM COMPOSITION TOPOLOGY INSPECTION: complete"
