#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

EXILES=(
  carbon
  cataxis
  coda
  envoy
  filament
  graffiti
  lore
  mobius
  modus
  niche
  notary
  opus
  pact
  palaver
  shatter
  underscore
  urge
  zero
)

for EXILE in "${EXILES[@]}"; do
  BASE="$EXILES_ROOT/$EXILE"

  mkdir -p \
    "$BASE/apps" \
    "$BASE/runtime" \
    "$BASE/registry" \
    "$BASE/canon" \
    "$BASE/authority" \
    "$BASE/lineage" \
    "$BASE/graph" \
    "$BASE/api" \
    "$BASE/tests" \
    "$BASE/docs" \
    "$BASE/observatory" \
    "$BASE/segue"

  cat > "$BASE/README.md" <<EOF
# ${EXILE^^} EXILE

Status: canonical exile module shell.

This exile is self-contained and recursively extensible.

Standard internal structure:

- apps/
- runtime/
- registry/
- canon/
- authority/
- lineage/
- graph/
- api/
- tests/
- docs/
- observatory/
- segue/

No exile should depend on hidden external structure for its own identity,
authority, lineage, registry, or graph projection.
EOF

  cat > "$BASE/registry/module.json" <<EOF
{
  "id": "$EXILE",
  "type": "exile",
  "status": "active",
  "path": "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/$EXILE",
  "composition_level": "exile",
  "contains": [
    "apps",
    "runtime",
    "registry",
    "canon",
    "authority",
    "lineage",
    "graph",
    "api",
    "tests",
    "docs",
    "observatory",
    "segue"
  ]
}
EOF

  cat > "$BASE/graph/node.json" <<EOF
{
  "id": "exile:$EXILE",
  "label": "$EXILE",
  "type": "exile",
  "parent_type": "innate",
  "child_type": "prodigal",
  "graph_address": "ontology.exiles.$EXILE"
}
EOF

done

echo "[OK] Expanded canonical exile module layout."
find "$EXILES_ROOT" -maxdepth 2 -type d | sort
