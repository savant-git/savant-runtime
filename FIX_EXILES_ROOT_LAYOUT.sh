#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
SEGUE="$EXILES/_template/segue"

mkdir -p "$SEGUE/exile_runtime"

# Move accidental runtime folder into correct place.
if [ -d "$EXILES/runtime" ]; then
  cp -a "$EXILES/runtime"/. "$SEGUE/exile_runtime"/ 2>/dev/null || true
  rm -rf "$EXILES/runtime"
fi

# Retire incorrect projection exile. Filament owns projection.
if [ -d "$EXILES/projection" ]; then
  mkdir -p "$SEGUE/exile_runtime/retired"
  mv "$EXILES/projection" "$SEGUE/exile_runtime/retired/projection_retired_$(date -u +%Y%m%dT%H%M%SZ)"
fi

# Move global support folders out of exiles root.
for d in _audit _bridges _index _reports _retired; do
  if [ -d "$EXILES/$d" ]; then
    mkdir -p "$SEGUE/exile_runtime/$d"
    cp -a "$EXILES/$d"/. "$SEGUE/exile_runtime/$d"/ 2>/dev/null || true
    rm -rf "$EXILES/$d"
  fi
done

echo "=== EXILES ROOT SHOULD NOW BE 18 EXILES + _template ONLY ==="
find "$EXILES" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort

echo
echo "COUNT ACTUAL EXILES:"
find "$EXILES" -maxdepth 1 -mindepth 1 -type d \
  ! -name '_template' \
  -printf '%f\n' | sort | wc -l

echo
echo "=== EXILE RUNTIME ==="
find "$SEGUE/exile_runtime" -maxdepth 2 -type d | sort
