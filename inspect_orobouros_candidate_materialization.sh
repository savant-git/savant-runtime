#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"

EVIDENCE="${ENVOY}/runtime/trait_evidence.py"
HISTORY_TEST="${ROOT}/test_orobouros_trait_history_deterministic.py"
ADMISSION_TEST="${ROOT}/test_orobouros_notary_admission_integration.py"

printf '%s\n' \
  '=== TRAIT OBSERVATION COMPLETE CONTRACT ==='

sed -n '270,555p' \
  "${EVIDENCE}"

printf '\n%s\n' \
  '=== HISTORY TEST CANDIDATE CATALOG ==='

sed -n '1,340p' \
  "${HISTORY_TEST}"

printf '\n%s\n' \
  '=== NOTARY INTEGRATION CANDIDATE FLOW ==='

sed -n '180,330p' \
  "${ADMISSION_TEST}"

printf '\n%s\n' \
  '=== PRIORITY OWNERSHIP SEARCH ==='

grep -RInE \
  '"priority"|priority=' \
  "${ENVOY}/runtime" \
  "${ENVOY}/registry/traits" \
  --include='*.py' \
  --include='*.json' \
  2>/dev/null \
  | head -180 \
  || true

printf '\n%s\n' \
  '=== CANDIDATE MATERIALIZATION REFERENCES ==='

grep -RInE \
  'TraitCandidate|candidate_from_observations|accepted_trait_projection' \
  "${ROOT}" \
  --include='*.py' \
  2>/dev/null \
  | head -220 \
  || true

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS CANDIDATE MATERIALIZATION INSPECTION: complete'
