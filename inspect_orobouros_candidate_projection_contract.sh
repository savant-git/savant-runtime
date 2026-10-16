#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"

EVIDENCE="${ENVOY}/runtime/trait_evidence.py"
EVALUATION="${ENVOY}/runtime/trait_evaluation.py"
EXPERIMENT="${ENVOY}/runtime/trait_experiment.py"
ADJUDICATION="${ENVOY}/runtime/trait_adjudication.py"

printf '%s\n' \
  '=== OROBOUROS CANDIDATE PROJECTION CONTRACT ==='

printf '\n%s\n' \
  '=== TRAIT EVIDENCE CANDIDATE TYPES ==='

grep -nE \
  '^class |^def |candidate_id|trait_id|projection|domains|signals|priority|conflicts|description' \
  "${EVIDENCE}" \
  | head -260

printf '\n%s\n' \
  '=== TRAIT EVIDENCE CANDIDATE IMPLEMENTATION ==='

sed -n '560,900p' \
  "${EVIDENCE}"

printf '\n%s\n' \
  '=== TRAIT EVALUATION CANDIDATE / RESULT SURFACE ==='

grep -nE \
  '^class |^def |candidate_id|trait_id|projection|measurements|champion|variant' \
  "${EVALUATION}" \
  | head -280

printf '\n%s\n' \
  '=== TRAIT EXPERIMENT CANDIDATE / VARIANT SURFACE ==='

grep -nE \
  '^class |^def |candidate_id|trait_id|projection|variant|trait|parameters' \
  "${EXPERIMENT}" \
  | head -320

printf '\n%s\n' \
  '=== ADJUDICATION CANDIDATE CONSTRUCTION ==='

sed -n '160,340p' \
  "${ADJUDICATION}"

sed -n '560,830p' \
  "${ADJUDICATION}"

printf '\n%s\n' \
  '=== TESTS USING CANDIDATE CATALOGS ==='

grep -RInE \
  'accepted_trait_projection|candidate.*catalog|candidate_id.*trait_id|AdjudicationCandidate' \
  "${ROOT}" \
  --include='test_*.py' \
  --include='*.sh' \
  2>/dev/null \
  | head -260 \
  || true

printf '\n%s\n' \
  '=== CODA IMPORT PATTERN ==='

sed -n '1,130p' \
  "${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/runtime/coda_bridge.py"

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS CANDIDATE PROJECTION CONTRACT: complete'
