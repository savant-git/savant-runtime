#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

printf '\n=== PRYME FILES ===\n'

find "$ROOT" \
  -type f \
  \( \
    -iname '*pryme*' \
    -o -path '*/runtime/pryme/*' \
  \) \
  -not -path '*/__pycache__/*' \
  -not -path '*/.git/*' \
  | sort

printf '\n=== PRYME REFERENCES ===\n'

grep -RIn \
  --exclude='*.log' \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.git' \
  -E '\bPryme\b|\bpryme\b' \
  "$ROOT/runtime" \
  "$ROOT/ontology" \
  "$ROOT/canon-system" \
  "$ROOT/assurance" \
  2>/dev/null \
  | head -300 \
  || true

printf '\n=== AUTHORITY RUNTIME ===\n'

find "$ROOT/runtime/constitution" \
  -maxdepth 3 \
  -type f \
  -print \
  2>/dev/null \
  | sort

printf '\n=== AUTHORITY GRAPH IMPLEMENTATION ===\n'

for file in \
  "$ROOT/runtime/constitution/registry.py" \
  "$ROOT/runtime/constitution/graph.py" \
  "$ROOT/runtime/constitution/bootstrap.py"
do
  if [ -f "$file" ]; then
    printf '\n--- %s ---\n' "$file"
    sed -n '1,320p' "$file"
  fi
done

printf '\n=== PRYME IMPLEMENTATION CONTENT ===\n'

while IFS= read -r file; do
  case "$file" in
    *.py|*.json|*.yaml|*.yml)
      printf '\n--- %s ---\n' "$file"
      sed -n '1,360p' "$file"
      ;;
  esac
done < <(
  find "$ROOT" \
    -type f \
    \( \
      -iname '*pryme*.py' \
      -o -iname '*pryme*.json' \
      -o -iname '*pryme*.yaml' \
      -o -iname '*pryme*.yml' \
      -o -path '*/runtime/pryme/*.py' \
      -o -path '*/runtime/pryme/*.json' \
    \) \
    -not -path '*/__pycache__/*' \
    -not -path '*/.git/*' \
    | sort
)

printf '\n=== RELATIONSHIP REGISTRY ===\n'

if [ -f "$ROOT/canon-system/authority/constitution/relationships.json" ]; then
  python3 -m json.tool \
    "$ROOT/canon-system/authority/constitution/relationships.json"
fi

printf '\n=== AUTHORITY GRAPH LOAD CHECK ===\n'

PYTHONPATH="$ROOT" \
python3 -c '
from runtime.constitution import ConstitutionalRegistry

root = "/root/savant-runtime"

registry = ConstitutionalRegistry.load(root)

print({
    "object_count": len(registry.values()),
    "registry_type": type(registry).__name__,
    "graph_type": type(registry.graph).__name__ if hasattr(registry, "graph") else None,
    "passed": True,
})
'

printf '\n=== RESULT ===\n'
echo "PRYME AUTHORITY INSPECTION: complete"
