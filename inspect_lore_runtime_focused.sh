#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
LORE="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/lore"

printf '%s\n' '=== LORE RUNTIME FILES ==='
find "$LORE/runtime" \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' '=== LORE RUNTIME CONTENT ==='
while IFS= read -r file; do
  printf '\n--- %s ---\n' "$file"
  sed -n '1,260p' "$file"
done < <(
  find "$LORE/runtime" \
    -type f \
    \( -name '*.py' -o -name '*.json' -o -name '*.yaml' -o -name '*.yml' \) \
    ! -path '*/__pycache__/*' \
    -print \
    2>/dev/null \
    | sort
)

printf '\n%s\n' '=== LORE CONTRACTS ==='
cat "$LORE/interface/contracts/contracts.json"

printf '\n%s\n' '=== LORE CAPABILITIES ==='
cat "$LORE/interface/capabilities/capabilities.json"

printf '\n%s\n' '=== LORE IMPORTS / EXPORTS ==='
for file in \
  "$LORE/composition/imports.json" \
  "$LORE/composition/exports.json"
do
  printf '\n--- %s ---\n' "$file"
  cat "$file"
done

printf '\n%s\n' '=== RESULT ==='
printf '%s\n' 'LORE RUNTIME FOCUSED INSPECTION: complete'
