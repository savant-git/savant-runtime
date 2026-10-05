#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"

HISTORY="${ENVOY}/runtime/trait_history.py"
PERSONA="${ENVOY}/runtime/persona_engine.py"

printf '%s\n' \
  '=== TRAIT HISTORY ACCEPTED PROJECTION ==='

sed -n '620,875p' \
  "${HISTORY}"

printf '\n%s\n' \
  '=== PERSONA ENGINE FULL SELECTION / COMPOSITION TAIL ==='

sed -n '820,1460p' \
  "${PERSONA}"

printf '\n%s\n' \
  '=== PERSONA ENGINE IMPORT / MAIN SURFACE ==='

grep -nE \
  '^def |^class |^if __name__|^DEFAULT_|^PROJECTION_SCHEMA|^PERSONA_SCHEMA' \
  "${PERSONA}"

printf '\n%s\n' \
  '=== HISTORY RECORD SERIALIZATION SURFACE ==='

sed -n '120,620p' \
  "${HISTORY}"

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS FINAL INTEGRATION SURFACE: complete'
