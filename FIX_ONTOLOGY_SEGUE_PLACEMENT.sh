#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
ONTOLOGY="$ROOT/ontology"
SEGUE="$ONTOLOGY/segue"

mkdir -p "$SEGUE"

move_if_exists() {
  local name="$1"
  local src="$ONTOLOGY/$name"
  local dst="$SEGUE/$name"

  if [ -e "$src" ]; then
    if [ -e "$dst" ]; then
      mkdir -p "$SEGUE/_merge_conflicts"
      mv "$src" "$SEGUE/_merge_conflicts/${name}_$(date -u +%Y%m%dT%H%M%SZ)"
    else
      mv "$src" "$dst"
    fi
  fi
}

move_if_exists "authority_graph"
move_if_exists "authority_db"
move_if_exists "runtime_reports"
move_if_exists "entity_index.json"
move_if_exists "entity_audit.json"

mkdir -p \
  "$SEGUE/authority_graph" \
  "$SEGUE/authority_db" \
  "$SEGUE/projections" \
  "$SEGUE/runtime" \
  "$SEGUE/scripts" \
  "$SEGUE/snippets" \
  "$SEGUE/lines" \
  "$SEGUE/characters"

cat > "$SEGUE/entity.json" <<'JSON'
{
  "id": "ontology.segue",
  "kind": "segue",
  "status": "active",
  "authority": "USER_DIRECTIVE",
  "rule": "Only edifice folders belong directly inside ontology/. Non-edifice infrastructure belongs inside ontology/segue/."
}
JSON

echo "[OK] ontology segue placement repaired"
echo
echo "Ontology root:"
find "$ONTOLOGY" -maxdepth 1 -mindepth 1 -printf '%f\n' | sort
echo
echo "Ontology segue:"
find "$SEGUE" -maxdepth 1 -mindepth 1 -printf '%f\n' | sort
