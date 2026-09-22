#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"

NOTARY="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/notary"

printf '%s\n' \
  '=== ENVOY ADJUDICATION/HISTORY/PROJECTION CANDIDATES ==='

find "$ENVOY" \
  -type f \
  \( \
    -name '*.py' \
    -o -name '*.json' \
  \) \
  -print0 \
| sort -z \
| xargs -0 grep -nEi \
  'adjudicat|decision|history|histor|accepted|acceptance|projection|supersed|winner|challenge|immutable|trait.*state|state.*trait' \
  || true

printf '\n%s\n' \
  '=== NOTARY ADJUDICATION/HISTORY/PROJECTION CANDIDATES ==='

find "$NOTARY" \
  -type f \
  \( \
    -name '*.py' \
    -o -name '*.json' \
  \) \
  -print0 \
| sort -z \
| xargs -0 grep -nEi \
  'adjudicat|decision|history|histor|accepted|acceptance|projection|supersed|winner|challenge|immutable|trait.*state|state.*trait' \
  || true

printf '\n%s\n' \
  '=== ENVOY RUNTIME FILES ==='

find "$ENVOY/runtime" \
  -maxdepth 1 \
  -type f \
  -print \
| sort

printf '\n%s\n' \
  '=== ENVOY REGISTRY FILES ==='

find "$ENVOY/registry" \
  -type f \
  -name '*.json' \
  -print \
| sort

printf '\n%s\n' \
  '=== TRAIT ADJUDICATION IMPLEMENTATION ==='

if [[ -f "$ENVOY/runtime/trait_adjudication.py" ]]; then
    sed -n '1,520p' \
      "$ENVOY/runtime/trait_adjudication.py"
fi

printf '\n%s\n' \
  '=== PERSONA ENGINE RELEVANT SURFACE ==='

grep -nEi \
  'living_trait|trait_pool|select_living_traits|compose_persona|accepted|adjudicat|history|supersed|projection' \
  "$ENVOY/runtime/persona_engine.py" \
  || true

printf '\n%s\n' \
  '=== OROBOUROS PERSONA ==='

cat \
  "$ENVOY/registry/personas/orobouros.json"

printf '\n%s\n' \
  '=== OROBOUROS TRAIT POOL ==='

cat \
  "$ENVOY/registry/traits/orobouros_traits.json"

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS ADJUDICATION HISTORY SURFACE: complete'
