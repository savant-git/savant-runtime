#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
CYPHER="${ROOT}/runtime/cypher"

printf '%s\n' \
  '=== CYPHER IMPLEMENTATION ==='

find \
  "${CYPHER}" \
  -maxdepth 3 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== CYPHER PACKAGE ==='

for file in \
  "${CYPHER}/__init__.py" \
  "${CYPHER}/engine.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== CYPHER INSTANCES ==='

if [ -d "${CYPHER}/instances" ]; then
    for file in "${CYPHER}"/instances/*; do
        [ -f "${file}" ] || continue

        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    done
fi

printf '\n%s\n' \
  '=== COMPATIBILITY / TRANSLATION REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'runtime\.cypher|living:cypher|Cypher|compatibil|translate|translation|adapter|serialize|serialization|normalize|normalization|schema.*version|protocol.*version' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 700 \
  || true

printf '\n%s\n' \
  '=== EXISTING ADAPTER / BRIDGE PRIMITIVES ==='

find \
  "${ROOT}" \
  \( \
    -iname '*adapter*' \
    -o -iname '*compat*' \
    -o -iname '*bridge*' \
    -o -iname '*translator*' \
    -o -iname '*serializer*' \
  \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/.git/*' \
  -print \
  2>/dev/null \
  | sort \
  | head -n 500

printf '\n%s\n' \
  '=== CYPHER DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'from runtime\.cypher|import runtime\.cypher|Cypher\(' \
  "${ROOT}" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== RESULT ===' \
  'CYPHER COMPATIBILITY INSPECTION: complete'
