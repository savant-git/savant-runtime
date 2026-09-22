#!/usr/bin/env bash

set -euo pipefail

ROOT="/root/savant-runtime"

PALAVER="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver"

RUNTIME="${PALAVER}/runtime"

FILES=(
    "${RUNTIME}/server.py"
    "${RUNTIME}/opus_bridge.py"
    "${RUNTIME}/envoy_bridge.py"
    "${RUNTIME}/coda_bridge.py"
    "${RUNTIME}/niche_bridge.py"
    "${RUNTIME}/patch_review_bridge.py"
    "${RUNTIME}/scrybe_bridge.py"
)

echo "=== PALAVER LIVE TOOL BINDING INSPECTION ==="

echo
echo "=== REQUIRED FILES ==="

for file in "${FILES[@]}"
do
    if [[ -f "${file}" ]]
    then
        echo "PASS  ${file}"
    else
        echo "MISS  ${file}"
    fi
done

echo
echo "=== SERVER HEALTH / CAPABILITY DISCOVERY ==="

grep -nE \
    'def health|file_tool|search_tool|retrieve_tool|patch_tool|graph_info|graph_file|term_available|core_available' \
    "${RUNTIME}/server.py" \
    || true

echo
echo "=== CHAT DISPATCH ==="

grep -nE \
    'api/chat|def .*chat|message|dispatch|command|files|graph|retrieve|search|patch|health' \
    "${RUNTIME}/server.py" \
    || true

echo
echo "=== FILE / TREE SURFACE ==="

grep -nE \
    'safe_rel_path|build_file_tree|list_directory|read_file|/api/tree|/api/file|file read|files' \
    "${RUNTIME}/server.py" \
    || true

echo
echo "=== GRAPH SURFACE ==="

grep -nE \
    '/api/graph|graph_info|graph_file|build_graph|graph' \
    "${RUNTIME}/server.py" \
    || true

echo
echo "=== RETRIEVAL / SCRYBE ==="

grep -nE \
    'scrybe|hydrate|retrieve|recall|context' \
    "${RUNTIME}/server.py" \
    "${RUNTIME}/scrybe_bridge.py" \
    2>/dev/null \
    || true

echo
echo "=== PATCH / CODA ==="

grep -nE \
    'patch|proposal|write|append|mutat|Coda|coda' \
    "${RUNTIME}/server.py" \
    "${RUNTIME}/patch_review_bridge.py" \
    "${RUNTIME}/coda_bridge.py" \
    2>/dev/null \
    || true

echo
echo "=== OPUS TOOL / RESPONSE SURFACE ==="

grep -nE \
    'execute_text_request|tool|tools|structured|response|provider|model' \
    "${RUNTIME}/opus_bridge.py" \
    "${RUNTIME}/server.py" \
    2>/dev/null \
    || true

echo
echo "=== NICHE TASK SURFACE ==="

grep -nE \
    'task|active|continue|ready|priority|Niche|niche' \
    "${RUNTIME}/niche_bridge.py" \
    "${RUNTIME}/server.py" \
    2>/dev/null \
    || true

echo
echo "=== DIRECT ROOT-LEVEL LEGACY TOOL CHECKS ==="

grep -RInE \
    'ROOT[[:space:]]*/[[:space:]]*"?(file|search|retrieve|patch|graph_info)"?|ROOT[[:space:]]*/[[:space:]]'\''(file|search|retrieve|patch|graph_info)'\''' \
    "${RUNTIME}" \
    --include='*.py' \
    || true

echo
echo "=== RESULT ==="
echo "PALAVER LIVE TOOL BINDING INSPECTION: complete"
