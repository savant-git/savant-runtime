#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

ENVOY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/envoy"

echo "=== OROBOUROS ENTERPRISE BASELINE INSPECTION ==="

echo
echo "=== LIVE OROBOUROS FILES ==="

find "${ENVOY}" \
  -type f \
  \( \
    -iname '*orobouros*' \
    -o -iname '*trait*' \
    -o -iname '*persona*' \
    -o -iname '*crown*' \
  \) \
  -print \
  | sort

echo
echo "=== PERSONA RECORD ==="

cat \
  "${ENVOY}/registry/personas/orobouros.json"

echo
echo "=== TRAIT RECORD ==="

cat \
  "${ENVOY}/registry/traits/orobouros_traits.json"

echo
echo "=== PERSONA ENGINE ==="

cat \
  "${ENVOY}/runtime/persona_engine.py"

echo
echo "=== ENVOY RUNTIME EXPORTS ==="

cat \
  "${ENVOY}/runtime/__init__.py" \
  2>/dev/null \
  || true

echo
echo "=== TRAIT / CROWN SYMBOLS ==="

grep -RInE \
  'trait|crown|baseline|champion|challenger|candidate|evaluation|confidence|conflict|compatib|hysteresis|stickiness|composition' \
  "${ENVOY}" \
  --include='*.py' \
  --include='*.json' \
  2>/dev/null \
  || true

echo
echo "=== OPUS MODEL / CAPABILITY SURFACE ==="

OPUS="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus"

find "${OPUS}/registry" \
  -maxdepth 3 \
  -type f \
  -print \
  | sort

grep -RInE \
  'model|capabil|provider|latency|cost|health|lineage|version' \
  "${OPUS}/registry" \
  "${OPUS}/runtime" \
  --include='*.py' \
  --include='*.json' \
  2>/dev/null \
  || true

echo
echo "=== EXISTING EVALUATION PRIMITIVES ==="

grep -RInE \
  'benchmark|evaluation|evaluator|score|champion|challenger|pairwise|candidate' \
  "${ROOT}/ontology" \
  --include='*.py' \
  --include='*.json' \
  2>/dev/null \
  || true

echo
echo "=== RESULT ==="
echo "OROBOUROS ENTERPRISE BASELINE INSPECTION: complete"
