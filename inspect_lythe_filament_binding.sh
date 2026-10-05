#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
LYTHE="${ROOT}/runtime/lythe"
FILAMENT="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/filament"

printf '%s\n' \
  '=== LYTHE IMPLEMENTATION ==='

find \
  "${LYTHE}" \
  -maxdepth 3 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== LYTHE PACKAGE ==='

for file in \
  "${LYTHE}/__init__.py" \
  "${LYTHE}/engine.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== LYTHE INSTANCES ==='

if [ -d "${LYTHE}/instances" ]; then
    for file in "${LYTHE}"/instances/*; do
        [ -f "${file}" ] || continue

        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    done
fi

printf '\n%s\n' \
  '=== FILAMENT IMPLEMENTATION ==='

find \
  "${FILAMENT}" \
  -maxdepth 4 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== FILAMENT CONTRACT SURFACE ==='

for file in \
  "${FILAMENT}/runtime/__init__.py" \
  "${FILAMENT}/entity.json" \
  "${FILAMENT}/interface/capabilities/capabilities.json" \
  "${FILAMENT}/interface/contracts/contracts.json" \
  "${FILAMENT}/composition/imports.json" \
  "${FILAMENT}/composition/exports.json" \
  "${FILAMENT}/registry/module.json" \
  "${FILAMENT}/introspection/dependencies.json" \
  "${FILAMENT}/introspection/health.json"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== LYTHE REFERENCES / DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'runtime\.lythe|from .*lythe|import .*lythe|Lythe|living:lythe' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== FILAMENT EXECUTION REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E \
  'filament|projection execution|projection runtime|projection worker|derive|derivation' \
  "${FILAMENT}" \
  "${LYTHE}" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== RESULT ===' \
  'LYTHE / FILAMENT INSPECTION: complete'
