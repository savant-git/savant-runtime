#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

printf '%s\n' \
  '=== THRYCE IMPLEMENTATION ==='

find \
  "${ROOT}/runtime/thryce" \
  -maxdepth 3 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== THRYCE PACKAGE ==='

for file in \
  "${ROOT}/runtime/thryce/__init__.py" \
  "${ROOT}/runtime/thryce/engine.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== THRYCE INSTANCES ==='

if [ -d "${ROOT}/runtime/thryce/instances" ]; then
    for file in "${ROOT}"/runtime/thryce/instances/*; do
        [ -f "${file}" ] || continue
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    done
fi

printf '\n%s\n' \
  '=== NOTARY IMPLEMENTATION REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'class .*Notary|notary|attest|evidence|verification|verify|assurance' \
  "${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/notary" \
  "${ROOT}/runtime/thryce" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== THRYCE DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'runtime\.thryce|from .*thryce|import .*thryce|Thryce' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== RESULT ===' \
  'THRYCE / NOTARY INSPECTION: complete'
