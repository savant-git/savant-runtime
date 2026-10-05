#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
NOTARY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/notary"

for file in \
  "${NOTARY}/runtime/__init__.py" \
  "${NOTARY}/entity.json" \
  "${NOTARY}/interface/capabilities/capabilities.json" \
  "${NOTARY}/interface/contracts/contracts.json" \
  "${NOTARY}/composition/imports.json" \
  "${NOTARY}/composition/exports.json" \
  "${NOTARY}/registry/module.json" \
  "${NOTARY}/introspection/dependencies.json" \
  "${NOTARY}/introspection/health.json"
do
    if [ -f "${file}" ]; then
        printf '\n=== %s ===\n' "${file}"
        cat "${file}"
    fi
done

printf '\n=== RESULT ===\n'
printf '%s\n' 'NOTARY CONTRACT SURFACE INSPECTION: complete'
