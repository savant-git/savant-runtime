#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus/segue/prodigals/coalesce"

printf '\n=== ENTRYPOINT FILES ===\n'

find "$ROOT" \
  -maxdepth 3 \
  -type f \
  \( \
    -path '*/commands/*' \
    -o -path '*/runtime/coalesce.py' \
    -o -path '*/runtime/server.py' \
    -o -path '*/runtime/__init__.py' \
  \) \
  -print \
  | sort

printf '\n=== CURRENT COALESCE RUNTIME ===\n'

if [ -f "$ROOT/runtime/coalesce.py" ]; then
  cat "$ROOT/runtime/coalesce.py"
fi

printf '\n=== COMMANDS ===\n'

if [ -d "$ROOT/commands" ]; then
  for file in "$ROOT"/commands/*; do
    [ -f "$file" ] || continue
    printf '\n--- %s ---\n' "$file"
    cat "$file"
  done
fi

printf '\n=== TEST ENTRYPOINT EXPECTATIONS ===\n'

grep -RInE \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  'runtime/coalesce.py|commands/|compile\(|project\(|status\(|/api/coalesce' \
  "$ROOT/tests" \
  "$ROOT/interface" \
  "$ROOT/static/public" \
  2>/dev/null \
  | head -n 300 \
  || true
