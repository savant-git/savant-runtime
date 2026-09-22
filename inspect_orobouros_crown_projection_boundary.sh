#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"

PERSONA="${ENVOY}/runtime/persona_engine.py"
HISTORY="${ENVOY}/runtime/trait_history.py"
ADJUDICATION="${ENVOY}/runtime/trait_adjudication.py"
TRAITS="${ENVOY}/registry/traits/orobouros_traits.json"
OROBOUROS="${ENVOY}/registry/personas/orobouros.json"

printf '%s\n' \
  '=== OROBOUROS CROWN / ACCEPTED-PROJECTION BOUNDARY ==='

printf '\n%s\n' \
  '=== PERSONA ENGINE IMPORTS ==='

sed -n '1,120p' \
  "${PERSONA}"

printf '\n%s\n' \
  '=== TRAIT POOL LOAD ==='

sed -n '620,730p' \
  "${PERSONA}"

printf '\n%s\n' \
  '=== LIVING TRAIT SELECTION ==='

sed -n '840,1030p' \
  "${PERSONA}"

printf '\n%s\n' \
  '=== PERSONA COMPOSITION ==='

sed -n '1020,1190p' \
  "${PERSONA}"

printf '\n%s\n' \
  '=== CURRENT ACCEPTED-PROJECTION REFERENCES ==='

grep -nEi \
  'trait_history|accepted_trait|accepted_traits|champion|candidate_id|history_record|projection_only' \
  "${PERSONA}" \
  "${ENVOY}/runtime/"*.py \
  2>/dev/null \
  || true

printf '\n%s\n' \
  '=== HISTORY PUBLIC SURFACE ==='

grep -nE \
  '^def |^class |^SCHEMA|^PROJECTION_SCHEMA|^OWNER' \
  "${HISTORY}"

printf '\n%s\n' \
  '=== ADJUDICATION PUBLIC SURFACE ==='

grep -nE \
  '^def |^class |^SCHEMA|^OWNER|^VERIFICATION_OWNER' \
  "${ADJUDICATION}"

printf '\n%s\n' \
  '=== OROBOUROS CROWN CONFIGURATION ==='

cat \
  "${OROBOUROS}"

printf '\n%s\n' \
  '=== STATIC TRAIT POOL ==='

cat \
  "${TRAITS}"

printf '\n%s\n' \
  '=== POTENTIAL STATE / HISTORY LOCATIONS ==='

find "${ENVOY}" \
  -maxdepth 4 \
  -type d \
  \( \
    -iname '*state*' \
    -o -iname '*history*' \
    -o -iname '*decision*' \
    -o -iname '*projection*' \
  \) \
  -print \
  | sort

printf '\n%s\n' \
  '=== CODA MUTATION SURFACE REFERENCES ==='

grep -RInE \
  'replace_text|save_file|mutation|receipt|append' \
  "${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/coda/runtime" \
  --include='*.py' \
  2>/dev/null \
  | head -160 \
  || true

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS CROWN PROJECTION BOUNDARY: complete'
