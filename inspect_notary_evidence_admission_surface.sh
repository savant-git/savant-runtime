#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

NOTARY="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/notary"

echo "=== NOTARY EVIDENCE ADMISSION SURFACE ==="

grep -RInE \
  'admit|admission|evidence|verify|verification|attest|decision|assure' \
  "${NOTARY}/runtime" \
  "${NOTARY}/registry" \
  --include='*.py' \
  --include='*.json' \
  2>/dev/null \
  || true

echo
echo "=== THRYCE ASSURANCE ==="

sed -n '1,360p' \
  "${NOTARY}/runtime/thryce_assurance.py"

echo
echo "=== NOTARY RUNTIME FILES ==="

find \
  "${NOTARY}/runtime" \
  -maxdepth 2 \
  -type f \
  -print \
  | sort

echo
echo "=== RESULT ==="
echo "NOTARY EVIDENCE ADMISSION SURFACE: complete"
