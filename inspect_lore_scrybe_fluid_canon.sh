#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
SCRYBE="${ROOT}/runtime/scrybe"
LORE="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/lore"
CANON="${ROOT}/canon-system"

printf '%s\n' \
  '=== SCRYBE IMPLEMENTATION ==='

find \
  "${SCRYBE}" \
  -maxdepth 3 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== SCRYBE PACKAGE ==='

for file in \
  "${SCRYBE}/__init__.py" \
  "${SCRYBE}/engine.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' \
          "${file}"

        cat \
          "${file}"
    fi
done

printf '\n%s\n' \
  '=== SCRYBE INSTANCES ==='

if [ -d "${SCRYBE}/instances" ]; then
    find \
      "${SCRYBE}/instances" \
      -maxdepth 2 \
      -type f \
      -print0 \
      2>/dev/null \
    | while IFS= read -r -d '' file
      do
          printf '\n--- %s ---\n' \
            "${file}"

          cat \
            "${file}"
      done
fi

printf '\n%s\n' \
  '=== LORE LIVE SURFACE ==='

find \
  "${LORE}" \
  -maxdepth 4 \
  -type f \
  \( \
    -name '*.py' \
    -o -name '*.json' \
    -o -name '*.yaml' \
    -o -name '*.yml' \
  \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/dist/*' \
  -print \
  2>/dev/null \
  | sort

for file in \
  "${LORE}/entity.json" \
  "${LORE}/runtime/__init__.py" \
  "${LORE}/interface/capabilities/capabilities.json" \
  "${LORE}/interface/contracts/contracts.json" \
  "${LORE}/composition/imports.json" \
  "${LORE}/composition/exports.json" \
  "${LORE}/registry/module.json" \
  "${LORE}/introspection/dependencies.json"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' \
          "${file}"

        cat \
          "${file}"
    fi
done

printf '\n%s\n' \
  '=== FLUID CANON LIVE SURFACE ==='

find \
  "${CANON}" \
  -maxdepth 4 \
  -type f \
  \( \
    -name '*.py' \
    -o -name '*.json' \
    -o -name '*.yaml' \
    -o -name '*.yml' \
  \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/projections/*' \
  -print \
  2>/dev/null \
  | sort \
  | head -n 500

printf '\n%s\n' \
  '=== CANON API / STORE REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='projections' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  -E \
  'fluid.?canon|canon.*store|canon.*record|append|supersed|valid_from|valid_to|effective|authority|provenance|lineage|confidence|recall|hydrate|memory' \
  "${CANON}" \
  "${LORE}" \
  "${SCRYBE}" \
  2>/dev/null \
  | head -n 700 \
  || true

printf '\n%s\n' \
  '=== SCRYBE LIVE DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='node_modules' \
  --exclude-dir='dist' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  --exclude-dir='.git' \
  -E \
  'runtime\.scrybe|living:scrybe|from .*scrybe|import .*scrybe|Scrybe\(' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/canon-system" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 400 \
  || true

printf '\n%s\n' \
  '=== MEMORY / RECALL PRIMITIVES ==='

find \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/canon-system" \
  -type f \
  \( \
    -iname '*memory*.py' \
    -o -iname '*memory*.json' \
    -o -iname '*recall*.py' \
    -o -iname '*recall*.json' \
    -o -iname '*context*.py' \
    -o -iname '*context*.json' \
    -o -iname '*canon*.py' \
  \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/node_modules/*' \
  ! -path '*/dist/*' \
  ! -path '*/vault/*' \
  ! -path '*/projections/*' \
  ! -path '*/structure-intelligence/*' \
  -print \
  2>/dev/null \
  | sort \
  | head -n 500

printf '\n%s\n' \
  '=== RESULT ===' \
  'LORE / FLUID CANON / SCRYBE INSPECTION: complete'
