#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"

BASE="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
FILAMENT="$BASE/filament"
FILAMENT_RUNTIME="$FILAMENT/runtime/projection_engine"

OBELISKS_SEGUE="$ROOT/ontology/obelisks/segue"
OLD_ENGINE="$OBELISKS_SEGUE/authority_graph/projection_engine"

mkdir -p \
  "$FILAMENT_RUNTIME" \
  "$FILAMENT/authority" \
  "$FILAMENT/canon" \
  "$FILAMENT/interface/contracts" \
  "$FILAMENT/registry/manifests" \
  "$FILAMENT/graph/relationships"

if [ -d "$OLD_ENGINE" ]; then
  rsync -a "$OLD_ENGINE"/ "$FILAMENT_RUNTIME"/
  mkdir -p "$OBELISKS_SEGUE/authority_graph/_retired"
  mv "$OLD_ENGINE" "$OBELISKS_SEGUE/authority_graph/_retired/projection_engine_moved_to_filament_$(date -u +%Y%m%dT%H%M%SZ)"
fi

cat > "$FILAMENT/canon/projection_engine_ownership.md" <<'MD'
# PROJECTION ENGINE OWNERSHIP

STATUS: CANON
AUTHORITY: USER DIRECTIVE

Filament owns projection.

Projection engines, projection runners, projection workers, and projection runtime code belong in Filament.

Authority graph may define projection rules.

Authority graph must not own projection runtime implementation.

Rule:

authority_graph = projection canon / contracts / references
filament = projection execution / runtime / implementation
MD

cat > "$FILAMENT/interface/contracts/projection_engine_contract.json" <<'JSON'
{
  "id": "contract.filament.projection_engine",
  "kind": "contract",
  "status": "active",
  "authority": "USER_DIRECTIVE",
  "owner": "filament",
  "function": "projection",
  "rule": "Filament owns runtime projection from authoritative primitives into generated files.",
  "inputs": [
    "authority_db",
    "instances",
    "templates",
    "segues",
    "policies"
  ],
  "outputs": [
    "json_projections",
    "markdown_projections",
    "script_projections",
    "audit_projections"
  ]
}
JSON

cat > "$FILAMENT/registry/manifests/projection_engine.json" <<'JSON'
{
  "id": "manifest.filament.projection_engine",
  "kind": "manifest",
  "status": "active",
  "owner": "filament",
  "runtime_path": "runtime/projection_engine/project.py",
  "authority": "USER_DIRECTIVE",
  "dependencies": [
    "ontology/obelisks/segue/authority_db/savant_authority.sqlite",
    "ontology/obelisks/segue/authority_graph/canon",
    "ontology/obelisks/segue/authority_graph/templates"
  ]
}
JSON

echo "[OK] Projection engine realigned to Filament:"
echo "$FILAMENT_RUNTIME"

echo
echo "Filament projection files:"
find "$FILAMENT" \( -path '*/projection_engine*' -o -name 'projection_engine_ownership.md' -o -name 'projection_engine_contract.json' -o -name 'projection_engine.json' \) -print | sort
