#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"
CODA="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/coda"

MUTATION="${CODA}/runtime/mutation.py"

printf '%s\n' \
  '=== CODA MUTATION CONTRACT ==='

sed -n '1,380p' \
  "${MUTATION}"

printf '\n%s\n' \
  '=== CODA PUBLIC MUTATION FUNCTIONS ==='

grep -nE \
  '^def |^class |^OWNER|^ROOT|^RECEIPT' \
  "${MUTATION}" \
  || true

printf '\n%s\n' \
  '=== EXISTING ENVOY STATE ==='

find "${ENVOY}/state" \
  -maxdepth 4 \
  -type f \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== EXISTING ENVOY EVOLUTION HISTORY ==='

find "${ENVOY}/evolution/history" \
  -maxdepth 4 \
  -type f \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== EXISTING HISTORY / DECISION CONTENT ==='

find \
  "${ENVOY}/state" \
  "${ENVOY}/evolution/history" \
  -type f \
  \( \
    -name '*.json' \
    -o -name '*.jsonl' \
    -o -name '*.py' \
    -o -name '*.md' \
  \) \
  -print0 \
  2>/dev/null \
| sort -z \
| xargs -0 -r grep -nEi \
  'trait|champion|candidate|decision|adjudicat|history|accepted|supersed|coda|mutation' \
  || true

printf '\n%s\n' \
  '=== CODA CALLERS ==='

grep -RInE \
  'replace_text\(|resolve_target\(|digest_file\(' \
  "${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles" \
  --include='*.py' \
  2>/dev/null \
  | head -220 \
  || true

printf '\n%s\n' \
  '=== TRAIT HISTORY CURRENT PERSISTENCE CLAIMS ==='

grep -nE \
  'persistent|persistence|Coda|coda|state|history|mutation' \
  "${ENVOY}/runtime/trait_history.py" \
  || true

printf '\n%s\n' \
  '=== RESULT ==='

printf '%s\n' \
  'OROBOUROS CODA HISTORY BINDING INSPECTION: complete'
