#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

EVIDENCE="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/runtime/trait_evidence.py"

TEST="${ROOT}/test_orobouros_trait_evidence_deterministic.py"

printf '%s\n' \
  '=== TRAIT CANDIDATE EXACT IMPLEMENTATION ==='

sed -n '540,835p' \
  "${EVIDENCE}"

printf '\n%s\n' \
  '=== TRAIT EVIDENCE DETERMINISTIC TEST ==='

sed -n '1,390p' \
  "${TEST}"

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS TRAIT CANDIDATE EXACT INSPECTION: complete'
