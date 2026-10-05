#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
DRYVE="${ROOT}/runtime/dryve"
NICHE="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/niche"
OPUS="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus"

printf '%s\n' \
  '=== DRYVE IMPLEMENTATION ==='

find \
  "${DRYVE}" \
  -maxdepth 3 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== DRYVE PACKAGE ==='

for file in \
  "${DRYVE}/__init__.py" \
  "${DRYVE}/engine.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== DRYVE INSTANCES ==='

if [ -d "${DRYVE}/instances" ]; then
    for file in "${DRYVE}"/instances/*; do
        [ -f "${file}" ] || continue

        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    done
fi

printf '\n%s\n' \
  '=== NICHE RUNTIME / CONTRACT SURFACE ==='

find \
  "${NICHE}" \
  -maxdepth 4 \
  -type f \
  \( -name '*.py' -o -name '*.json' \) \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

for file in \
  "${NICHE}/runtime/__init__.py" \
  "${NICHE}/entity.json" \
  "${NICHE}/interface/capabilities/capabilities.json" \
  "${NICHE}/interface/contracts/contracts.json" \
  "${NICHE}/composition/imports.json" \
  "${NICHE}/composition/exports.json" \
  "${NICHE}/registry/module.json"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== OPUS RUNTIME / CONTRACT SURFACE ==='

find \
  "${OPUS}" \
  -maxdepth 4 \
  -type f \
  \( -name '*.py' -o -name '*.json' \) \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

for file in \
  "${OPUS}/runtime/__init__.py" \
  "${OPUS}/entity.json" \
  "${OPUS}/interface/capabilities/capabilities.json" \
  "${OPUS}/interface/contracts/contracts.json" \
  "${OPUS}/composition/imports.json" \
  "${OPUS}/composition/exports.json" \
  "${OPUS}/registry/module.json"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== DRYVE REFERENCES / DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'runtime\.dryve|from .*dryve|import .*dryve|Dryve|living:dryve' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== NICHE TASK AUTHORITY REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'task.*authority|task.*state|task.*transition|queue|lease|schedule|masterplan' \
  "${NICHE}" \
  "${DRYVE}" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== OPUS EXECUTION REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'provider|model|inference|execution|retry|fallback|route|orchestrat' \
  "${OPUS}" \
  "${DRYVE}" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== RESULT ===' \
  'DRYVE / NICHE / OPUS INSPECTION: complete'
