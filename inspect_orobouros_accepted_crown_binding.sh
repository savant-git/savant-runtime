#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY_RUNTIME="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/runtime"
ENVOY_REGISTRY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/registry"
ENVOY_STATE="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/state"
ENVOY_HISTORY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy/evolution/history"

PERSONA_ENGINE="${ENVOY_RUNTIME}/persona_engine.py"
TRAIT_HISTORY="${ENVOY_RUNTIME}/trait_history.py"
TRAIT_EVIDENCE="${ENVOY_RUNTIME}/trait_evidence.py"
TRAIT_ADJUDICATION="${ENVOY_RUNTIME}/trait_adjudication.py"
OROBOUROS_PERSONA="${ENVOY_REGISTRY}/personas/orobouros.json"
STATIC_POOL="${ENVOY_REGISTRY}/traits/orobouros_traits.json"

printf '%s\n' \
  '=== OROBOUROS ACCEPTED-CROWN BINDING INSPECTION ==='

printf '\n%s\n' \
  '=== PERSONA ENGINE IMPORTS ==='

sed -n '1,120p' \
  "${PERSONA_ENGINE}"

printf '\n%s\n' \
  '=== PERSONA ENGINE TRAIT POOL / SELECTION REFERENCES ==='

grep -nE \
  'TRAIT_REGISTRY|DEFAULT_TRAIT_POOL_ID|load_trait_pool|select_living_traits|compose_persona|living_trait_crown|traits|priority|conflicts' \
  "${PERSONA_ENGINE}" \
  || true

printf '\n%s\n' \
  '=== PERSONA ENGINE TRAIT LOAD + SELECTION ==='

sed -n '630,1030p' \
  "${PERSONA_ENGINE}"

printf '\n%s\n' \
  '=== PERSONA ENGINE COMPOSITION ==='

sed -n '1020,1185p' \
  "${PERSONA_ENGINE}"

printf '\n%s\n' \
  '=== ACCEPTED TRAIT PROJECTION IMPLEMENTATION ==='

grep -n \
  -A 125 \
  '^def accepted_trait_projection' \
  "${TRAIT_HISTORY}" \
  || true

printf '\n%s\n' \
  '=== TRAIT HISTORY STATUS / PERSISTENCE CONTRACT ==='

grep -nE \
  'persistent_state|persistence_owner_required|accepted_traits_derived|projection_only|authoritative|authority_effect|rebuildable' \
  "${TRAIT_HISTORY}" \
  || true

printf '\n%s\n' \
  '=== CANDIDATE SEMANTIC PROJECTION ==='

grep -n \
  -A 190 \
  '^class TraitCandidate' \
  "${TRAIT_EVIDENCE}" \
  || true

printf '\n%s\n' \
  '=== ADJUDICATION DECISION CONTRACT ==='

grep -n \
  -A 125 \
  '^class AdjudicationDecision' \
  "${TRAIT_ADJUDICATION}" \
  || true

printf '\n%s\n' \
  '=== CURRENT OROBOUROS PERSONA ==='

cat \
  "${OROBOUROS_PERSONA}"

printf '\n%s\n' \
  '=== CURRENT STATIC TRAIT POOL ==='

cat \
  "${STATIC_POOL}"

printf '\n%s\n' \
  '=== CURRENT ENVOY STATE TREE ==='

if [ -d "${ENVOY_STATE}" ]; then
  find \
    "${ENVOY_STATE}" \
    -maxdepth 4 \
    -type f \
    -print \
    | sort
else
  printf '%s\n' \
    'STATE DIRECTORY ABSENT'
fi

printf '\n%s\n' \
  '=== CURRENT ENVOY EVOLUTION HISTORY TREE ==='

if [ -d "${ENVOY_HISTORY}" ]; then
  find \
    "${ENVOY_HISTORY}" \
    -maxdepth 4 \
    -type f \
    -print \
    | sort
else
  printf '%s\n' \
    'EVOLUTION HISTORY DIRECTORY ABSENT'
fi

printf '\n%s\n' \
  '=== ACCEPTED / CHAMPION / HISTORY REFERENCES ACROSS ENVOY ==='

grep -RInE \
  'accepted_trait_projection|accepted_traits|current_champions|winner_candidate_id|candidate_catalog|trait_history|champion' \
  "${ENVOY_RUNTIME}" \
  "${ENVOY_STATE}" \
  "${ENVOY_HISTORY}" \
  2>/dev/null \
  | head -500 \
  || true

printf '\n%s\n' \
  '=== CODA PERSISTENCE REFERENCES FOR OROBOUROS TRAIT STATE ==='

grep -RInE \
  'trait_history|accepted_traits|orobouros.*trait|coda.*history|history.*coda' \
  "${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/coda" \
  "${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver" \
  2>/dev/null \
  | head -500 \
  || true

printf '\n%s\n' \
  '=== EXISTING TESTS / CHECKS ==='

find \
  "${ROOT}" \
  -maxdepth 2 \
  -type f \
  \( \
    -name '*orobouros*trait*' \
    -o \
    -name '*orobouros*crown*' \
    -o \
    -name '*orobouros*candidate*' \
    -o \
    -name '*orobouros*history*' \
  \) \
  -print \
  | sort

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS ACCEPTED-CROWN BINDING INSPECTION: complete'
