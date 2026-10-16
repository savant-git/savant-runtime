#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
LYTHE="${ROOT}/runtime/lythe"
FILAMENT="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/filament"

printf '%s\n' '=== LYTHE ENGINE ==='
cat "${LYTHE}/engine.py"

printf '\n%s\n' '=== FILAMENT RUNTIME PYTHON ==='
find \
  "${FILAMENT}/runtime" \
  -maxdepth 4 \
  -type f \
  -name '*.py' \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

for file in \
  $(find \
    "${FILAMENT}/runtime" \
    -maxdepth 4 \
    -type f \
    -name '*.py' \
    ! -path '*/__pycache__/*' \
    -print \
    2>/dev/null \
    | sort)
do
    printf '\n--- %s ---\n' "${file}"
    cat "${file}"
done

printf '\n%s\n' '=== FILAMENT PROJECTION CONTRACTS ==='

find \
  "${FILAMENT}" \
  -type f \
  \( -name '*.json' -o -name '*.py' \) \
  ! -path '*/__pycache__/*' \
  -print0 \
  2>/dev/null \
| xargs -0 grep -InE \
    'projection_engine|runtime_path|execute|worker|emit|projection|derive' \
    2>/dev/null \
| head -n 500 \
|| true

printf '\n%s\n' '=== RESULT ==='
printf '%s\n' 'LYTHE / FILAMENT RUNTIME SURFACE INSPECTION: complete'
