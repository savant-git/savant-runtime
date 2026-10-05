#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
ONTOLOGY="$ROOT/ontology"
OBELISKS="$ONTOLOGY/obelisks"
TARGET="$OBELISKS/segue"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$TARGET"

move_into_obelisks_segue() {
  local name="$1"
  local src="$ONTOLOGY/$name"
  local dst="$TARGET/$name"

  if [ -e "$src" ]; then
    if [ -e "$dst" ]; then
      mkdir -p "$TARGET/_merge_conflicts/$STAMP"
      mv "$src" "$TARGET/_merge_conflicts/$STAMP/$name"
    else
      mv "$src" "$dst"
    fi
  fi
}

move_into_obelisks_segue "segue"
move_into_obelisks_segue "authority_graph"
move_into_obelisks_segue "authority_db"
move_into_obelisks_segue "indexes"
move_into_obelisks_segue "projections"
move_into_obelisks_segue "runtime"
move_into_obelisks_segue "scripts"
move_into_obelisks_segue "snippets"
move_into_obelisks_segue "lines"
move_into_obelisks_segue "characters"

if [ -d "$TARGET/segue" ]; then
  shopt -s dotglob nullglob
  for item in "$TARGET/segue"/*; do
    base="$(basename "$item")"
    if [ -e "$TARGET/$base" ]; then
      mkdir -p "$TARGET/_merge_conflicts/$STAMP"
      mv "$item" "$TARGET/_merge_conflicts/$STAMP/${base}_from_nested_segue"
    else
      mv "$item" "$TARGET/$base"
    fi
  done
  rmdir "$TARGET/segue" 2>/dev/null || true
fi

cat > "$TARGET/entity.json" <<'JSON'
{
  "id": "ontology.obelisks.segue",
  "kind": "segue",
  "status": "active",
  "authority": "USER_DIRECTIVE",
  "rule": "ontology contains obelisks. Shared ontology infrastructure belongs under ontology/obelisks/segue, not ontology/segue."
}
JSON

echo
echo "Ontology root:"
find "$ONTOLOGY" -maxdepth 1 -mindepth 1 -printf '%f\n' | sort

echo
echo "Obelisks segue:"
find "$TARGET" -maxdepth 1 -mindepth 1 -printf '%f\n' | sort

echo
echo "[OK] realigned"
