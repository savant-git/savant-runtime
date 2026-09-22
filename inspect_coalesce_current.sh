#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

printf '%s\n' '=== COALESCE AUTHORITY ==='
for path in \
  "$ROOT/COALESCE_COMPOSITION_CONTRACT.md" \
  "$ROOT/COALESCE_SLIVER_MIGRATION_PLAN.md" \
  "$ROOT/COALESCE_ARCHITECTURE_CANON.md" \
  "$ROOT/COALESCE_27_PRIMITIVE_TARGET.md"
do
  if [ -f "$path" ]; then
    printf '\n--- %s ---\n' "$path"
    cat "$path"
  fi
done

printf '\n%s\n' '=== MODUS AUTHORITY ==='
cat "$ROOT/canon-system/authority/exiles/modus.yaml"

printf '\n%s\n' '=== COALESCE IMPLEMENTATION CANDIDATES ==='
find "$ROOT" \
  -type f \
  \( \
    -iname '*coalesce*' -o \
    -iname '*sliver*' -o \
    -iname '*alloy*' \
  \) \
  -not -path '*/__pycache__/*' \
  -not -path '*/vault/*' \
  -not -path '*/projections/*' \
  -print \
  | sort

printf '\n%s\n' '=== MODUS IMPLEMENTATION ==='
find "$ROOT/ontology" \
  -type f \
  -path '*exiles/modus/*' \
  -not -path '*/__pycache__/*' \
  -print \
  | sort

printf '\n%s\n' '=== COALESCE REFERENCES ==='
grep -RInE \
  --exclude='*.log' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  --exclude-dir='vault' \
  --exclude-dir='projections' \
  '\bCoalesce\b|\bcoalesce\b|\bSliver\b|\bsliver\b|\bAlloy\b|\balloy\b|prodigal:modus:coalesce' \
  "$ROOT/canon-system" \
  "$ROOT/ontology" \
  "$ROOT/runtime" \
  "$ROOT/assurance" \
  "$ROOT/bin" \
  2>/dev/null \
  | head -n 500 || true

printf '\n%s\n' '=== MODUS DEPENDENTS ==='
grep -RIn \
  --exclude='*.log' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  'exile:modus' \
  "$ROOT/canon-system" \
  "$ROOT/ontology" \
  "$ROOT/runtime" \
  "$ROOT/assurance" \
  "$ROOT/bin" \
  2>/dev/null \
  | head -n 300 || true
