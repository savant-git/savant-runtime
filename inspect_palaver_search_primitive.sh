#!/usr/bin/env bash

set -euo pipefail

SERVER="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/apps/webui_ultra/server.py"

echo "=== SEARCH SYMBOLS ==="

grep -nE \
    '^def .*search|search_payload|memory/search|repository/search|neural_search|search_fabric' \
    "${SERVER}" \
    || true

echo
echo "=== MEMORY SEARCH HANDLER ==="

grep -n -A70 -B20 \
    '"/api/memory/search"' \
    "${SERVER}" \
    || true

echo
echo "=== REPOSITORY SEARCH HANDLER ==="

grep -n -A70 -B20 \
    '"/api/repository/search"' \
    "${SERVER}" \
    || true

echo
echo "=== SEARCH FABRIC CALLS ==="

grep -n -A45 -B20 \
    'search_fabric.py' \
    "${SERVER}" \
    || true

echo
echo "=== RESULT ==="
echo "PALAVER SEARCH PRIMITIVE INSPECTION: complete"
