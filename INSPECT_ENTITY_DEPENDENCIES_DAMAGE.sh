#!/usr/bin/env bash
set -euo pipefail

TARGET="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/runtime/services/ENTITY_DEPENDENCIES.py"

echo
echo "===== FILE ====="
echo "$TARGET"

echo
echo "===== LINE COUNT ====="
wc -l "$TARGET"

echo
echo "===== LAST 40 LINES ====="
tail -40 "$TARGET"

echo
echo "===== LAST 10 NUMBERED ====="
nl -ba "$TARGET" | tail -10

echo
echo "===== BACKUPS ====="
find "$(dirname "$TARGET")" \
    -maxdepth 1 \
    -type f \
    -name 'ENTITY_DEPENDENCIES.py*' \
    | sort

echo
echo "===== GIT ====="
git status --short 2>/dev/null || true
git log --oneline -- "$TARGET" 2>/dev/null || true
