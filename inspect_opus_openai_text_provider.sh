#!/usr/bin/env bash

set -euo pipefail

PROVIDER="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus/runtime/providers/openai_text.py"

BASE="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/opus/runtime/providers/base.py"

echo "=== OPENAI TEXT PROVIDER ==="

cat "${PROVIDER}"

echo
echo "=== PROVIDER BASE ==="

cat "${BASE}"

echo
echo "=== RESULT ==="
echo "OPUS OPENAI TEXT PROVIDER INSPECTION: complete"
