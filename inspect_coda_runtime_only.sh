#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
CODA="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/coda"

printf '%s\n' \
  '=== CODA ENTITY ==='

cat \
  "${CODA}/entity.json" \
  2>/dev/null \
  || true

printf '\n%s\n' \
  '=== CODA RUNTIME FILES ==='

find \
  "${CODA}/runtime" \
  -maxdepth 4 \
  -type f \
  \( \
    -name '*.py' \
    -o -name '*.json' \
  \) \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== CODA RUNTIME PYTHON ==='

find \
  "${CODA}/runtime" \
  -maxdepth 4 \
  -type f \
  -name '*.py' \
  ! -path '*/__pycache__/*' \
  -print0 \
  2>/dev/null \
| while IFS= read -r -d '' file
do
    printf '\n--- %s ---\n' \
      "${file}"

    cat \
      "${file}"
done

printf '\n%s\n' \
  '=== CODA CONTRACTS ==='

for file in \
  "${CODA}/interface/capabilities/capabilities.json" \
  "${CODA}/interface/contracts/contracts.json" \
  "${CODA}/composition/imports.json" \
  "${CODA}/composition/exports.json" \
  "${CODA}/registry/module.json" \
  "${CODA}/introspection/dependencies.json" \
  "${CODA}/introspection/health.json"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' \
          "${file}"

        cat \
          "${file}"
    fi
done

printf '\n%s\n' \
  '=== CODA MUTATION API SYMBOLS ==='

find \
  "${CODA}" \
  -type f \
  \( \
    -name '*.py' \
    -o -name '*.json' \
  \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/dist/*' \
  -print0 \
  2>/dev/null \
| xargs -0 grep -InE \
    'authority_witness|authority witness|commit|mutation|authorize|authorized|apply|rollback|migration|transition|durable|supersession' \
    2>/dev/null \
| head -n 500 \
|| true

printf '\n%s\n' \
  '=== EXISTING SPYRAL REFERENCES IN CODA ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='node_modules' \
  --exclude-dir='dist' \
  -E \
  'spyral|living:spyral|transition_id|migration_manifest' \
  "${CODA}" \
  2>/dev/null \
  | head -n 300 \
  || true

printf '\n%s\n' \
  '=== RESULT ===' \
  'CODA RUNTIME-ONLY INSPECTION: complete'
