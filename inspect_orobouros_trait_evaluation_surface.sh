#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"
OPUS="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus"
NOTARY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/notary"

PERSONA_ENGINE="${ENVOY}/runtime/persona_engine.py"
TRAITS="${ENVOY}/registry/traits/orobouros_traits.json"
PERSONA="${ENVOY}/registry/personas/orobouros.json"
THRYCE="${NOTARY}/runtime/thryce_assurance.py"

echo "=== OROBOUROS TRAIT EVALUATION SURFACE ==="

echo
echo "=== 1. CURRENT PERSONA ==="
cat "${PERSONA}"

echo
echo "=== 2. CURRENT TRAITS ==="
cat "${TRAITS}"

echo
echo "=== 3. PERSONA ENGINE TRAIT FUNCTIONS ==="

grep -nE \
  '^def (_trait_score|select_living_traits|assert_no_trait_conflicts|compose_persona|_conflicts|load_traits|load_persona)' \
  "${PERSONA_ENGINE}"

echo
echo "=== 4. TRAIT SCORING IMPLEMENTATION ==="

sed -n '700,1040p' \
  "${PERSONA_ENGINE}"

echo
echo "=== 5. TRAIT LOAD / VALIDATION IMPLEMENTATION ==="

sed -n '1,700p' \
  "${PERSONA_ENGINE}" \
  | grep -nE -B12 -A45 \
  'trait|baseline|crown|conflict|compatib|confidence|provenance|lineage|version'

echo
echo "=== 6. CURRENT OPUS TEXT PROVIDERS ==="

find \
  "${OPUS}/registry/providers" \
  -maxdepth 1 \
  -type f \
  -print \
  | sort

for file in "${OPUS}"/registry/providers/*.json
do
    [ -f "${file}" ] || continue

    echo
    echo "--- ${file} ---"
    cat "${file}"
done

echo
echo "=== 7. TEXT ROUTE ==="

cat \
  "${OPUS}/registry/routes/text_inference_route.json" \
  2>/dev/null \
  || true

echo
echo "=== 8. NOTARY CANDIDATE / ASSURANCE SURFACE ==="

grep -nE \
  '^class VerificationCandidate|^class NotaryThryceAssurance|^    def (candidate|projection|assure|status)' \
  "${THRYCE}"

sed -n '1,230p' \
  "${THRYCE}"

echo
echo "=== 9. EXISTING ENVOY EVALUATION FILES ==="

find "${ENVOY}" \
  -type f \
  \( \
    -iname '*evaluat*' \
    -o -iname '*candidate*' \
    -o -iname '*champion*' \
    -o -iname '*challenger*' \
    -o -iname '*evidence*' \
  \) \
  -print \
  | sort

echo
echo "=== RESULT ==="
echo "OROBOUROS TRAIT EVALUATION SURFACE: complete"
