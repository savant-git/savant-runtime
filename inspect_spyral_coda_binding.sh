#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
SPYRAL="${ROOT}/runtime/spyral"
CODA="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/coda"

printf '%s\n' \
  '=== SPYRAL IMPLEMENTATION ==='

find \
  "${SPYRAL}" \
  -maxdepth 3 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== SPYRAL PACKAGE ==='

for file in \
  "${SPYRAL}/__init__.py" \
  "${SPYRAL}/engine.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== SPYRAL INSTANCES ==='

if [ -d "${SPYRAL}/instances" ]; then
    find \
      "${SPYRAL}/instances" \
      -maxdepth 2 \
      -type f \
      -print0 \
      2>/dev/null \
    | while IFS= read -r -d '' file
      do
          printf '\n--- %s ---\n' "${file}"
          cat "${file}"
      done
fi

printf '\n%s\n' \
  '=== CODA LIVE SURFACE ==='

find \
  "${CODA}" \
  -maxdepth 4 \
  -type f \
  \( -name '*.py' -o -name '*.json' \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/dist/*' \
  -print \
  2>/dev/null \
  | sort

for file in \
  "${CODA}/runtime/__init__.py" \
  "${CODA}/entity.json" \
  "${CODA}/interface/capabilities/capabilities.json" \
  "${CODA}/interface/contracts/contracts.json" \
  "${CODA}/composition/imports.json" \
  "${CODA}/composition/exports.json" \
  "${CODA}/registry/module.json" \
  "${CODA}/introspection/dependencies.json"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== SPYRAL LIVE DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='node_modules' \
  --exclude-dir='dist' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  --exclude-dir='.git' \
  -E \
  'runtime\.spyral|living:spyral|from .*spyral|import .*spyral|Spyral\(' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 350 \
  || true

printf '\n%s\n' \
  '=== CODA MUTATION / MIGRATION REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='node_modules' \
  --exclude-dir='dist' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  --exclude-dir='.git' \
  -E \
  'mutation|mutate|migration|migrate|version transition|supersed|rollback|commit|apply|authorize|authorization' \
  "${CODA}" \
  "${SPYRAL}" \
  2>/dev/null \
  | head -n 450 \
  || true

printf '\n%s\n' \
  '=== EXISTING SPYRAL / CODA BINDINGS ==='

find \
  "${ROOT}/runtime/spyral" \
  "${CODA}" \
  -type f \
  \( \
    -iname '*spyral*' \
    -o -iname '*coda*' \
    -o -iname '*evolution*' \
    -o -iname '*migration*' \
    -o -iname '*transition*' \
    -o -iname '*binding*' \
    -o -iname '*adapter*' \
  \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/dist/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== RESULT ===' \
  'SPYRAL / CODA INSPECTION: complete'
