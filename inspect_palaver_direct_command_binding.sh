#!/usr/bin/env bash

set -euo pipefail

SERVER="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/runtime/server.py"

LEGACY="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/apps/webui_ultra/server.py"

echo "=== CANONICAL BOOTSTRAP ==="

grep -n -A70 -B10 \
    '^def bootstrap' \
    "${SERVER}"

echo
echo "=== CANONICAL INSTALL FUNCTIONS ==="

grep -nE \
    '^def install_' \
    "${SERVER}"

echo
echo "=== CURRENT LEGACY DIRECT COMMAND ==="

grep -n -A95 \
    '^def direct_command' \
    "${LEGACY}"

echo
echo "=== CURRENT LEGACY TOOL PRIMITIVES ==="

grep -nE \
    '^def (list_directory_payload|read_file_payload|graph_snapshot|repository_files_payload|memory_files_payload|patch_review_pending_payload|read_text_payload|latest_matching_payload)' \
    "${LEGACY}"

echo
echo "=== SCRYBE BRIDGE PUBLIC FUNCTIONS ==="

grep -nE \
    '^def ' \
    "/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/runtime/scrybe_bridge.py"

echo
echo "=== RESULT ==="
echo "PALAVER DIRECT COMMAND BINDING INSPECTION: complete"
