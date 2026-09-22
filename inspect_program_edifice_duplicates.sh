#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/runtime"

printf '%s\n' \
    "=== PROGRAM edifice DUPLICATION INSPECTION ==="

printf '%s\n' \
    "" \
    "=== TOPOLOGY DEFINITIONS ==="

grep -RInE \
    '^[[:space:]]*(PROGRAM_edifice_SEGUES|PROGRAM_edifice_LINEAGE|PROGRAM_LEVELS|PROGRAM_LEVEL_INDEX|PROGRAM_CHILD_LEVEL|PROGRAM_PARENT_LEVEL|PARENT_LEVELS)[[:space:]]*=' \
    "${RUNTIME}" \
    --include='*.py' \
    || true

printf '%s\n' \
    "" \
    "=== FULL NINE-LEVEL SEQUENCES ==="

grep -RInE \
    'character.*line.*segment.*snippet.*script.*engine.*subsystem.*system.*application' \
    "${RUNTIME}" \
    --include='*.py' \
    || true

printf '%s\n' \
    "" \
    "=== UPPER-LEVEL PAIR LITERALS ==="

grep -RInE \
    '"script".*"engine"|"engine".*"subsystem"|"subsystem".*"system"|"system".*"application"' \
    "${RUNTIME}" \
    --include='*.py' \
    || true

printf '%s\n' \
    "" \
    "=== LOWER-LEVEL PAIR LITERALS ==="

grep -RInE \
    '"character".*"line"|"line".*"segment"|"segment".*"snippet"|"snippet".*"script"' \
    "${RUNTIME}" \
    --include='*.py' \
    || true

printf '%s\n' \
    "" \
    "=== edifice SOURCE MARKERS ==="

grep -RIn \
    'PROGRAM_edifice_SEGUES' \
    "${RUNTIME}" \
    --include='*.py' \
    || true

printf '%s\n' \
    "" \
    "=== RESULT ===" \
    "PROGRAM edifice DUPLICATION INSPECTION: complete"
