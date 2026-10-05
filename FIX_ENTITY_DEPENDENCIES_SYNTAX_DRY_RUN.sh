#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

TARGET="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/runtime/services/ENTITY_DEPENDENCIES.py"

echo "=== TARGET ==="
echo "$TARGET"

echo
echo "=== CURRENT TAIL ==="
tail -n 20 "$TARGET" || true

echo
echo "=== PYTHON COMPILE ==="
python3 -m py_compile "$TARGET" || true

echo
echo "No changes made."
