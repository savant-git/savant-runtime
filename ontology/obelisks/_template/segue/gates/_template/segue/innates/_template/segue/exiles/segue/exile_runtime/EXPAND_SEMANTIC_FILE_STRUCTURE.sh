#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

if [ ! -d "$EXILES_ROOT" ]; then
  echo "[ERROR] Missing exiles root:"
  echo "$EXILES_ROOT"
  exit 1
fi

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
    "$BASE/interface" \
    "$BASE/interface/runtime" \
    "$BASE/interface/api" \
    "$BASE/interface/events" \
    "$BASE/interface/capabilities" \
    "$BASE/interface/contracts" \
    "$BASE/evolution/migrations" \
    "$BASE/evolution/supersessions" \
    "$BASE/evolution/compatibility" \
    "$BASE/evolution/deprecations" \
    "$BASE/evolution/history" \
    "$BASE/composition" \
    "$BASE/lifecycle/create" \
    "$BASE/lifecycle/activate" \
    "$BASE/lifecycle/suspend" \
    "$BASE/lifecycle/migrate" \
    "$BASE/lifecycle/destroy" \
    "$BASE/lifecycle/recover" \
    "$BASE/state" \
    "$BASE/cache" \
    "$BASE/sessions" \
    "$BASE/metrics" \
    "$BASE/introspection" \
    "$BASE/bridges" \
    "$BASE/facets" \
    "$BASE/static" \
    "$BASE/dynamic"

  cat > "$BASE/entity.json" <<EOF
{
  "id": "$EXILE",
  "type": "exile",
  "status": "active",
  "owner": "$EXILE",
  "authority": "$BASE/authority",
  "lineage": "$BASE/lineage",
  "graph": "$BASE/graph",
  "interface": "$BASE/interface",
  "runtime": "$BASE/runtime",
  "registry": "$BASE/registry",
  "canon": "$BASE/canon",
  "composition": "$BASE/composition",
  "lifecycle": "$BASE/lifecycle",
  "introspection": "$BASE/introspection",
  "facets": "$BASE/facets"
}
EOF

  cat > "$BASE/interface/capabilities/capabilities.json" <<EOF
{
  "id": "$EXILE.capabilities",
  "owner": "$EXILE",
  "type": "capability_manifest",
  "status": "stub",
  "capabilities": []
}
EOF

  cat > "$BASE/interface/contracts/contracts.json" <<EOF
{
  "id": "$EXILE.contracts",
  "owner": "$EXILE",
  "type": "interface_contract_manifest",
  "status": "stub",
  "contracts": []
}
EOF

  cat > "$BASE/composition/imports.json" <<EOF
{
  "id": "$EXILE.imports",
  "owner": "$EXILE",
  "imports": []
}
EOF

  cat > "$BASE/composition/exports.json" <<EOF
{
  "id": "$EXILE.exports",
  "owner": "$EXILE",
  "exports": []
}
EOF

  cat > "$BASE/introspection/health.json" <<EOF
{
  "id": "$EXILE.health",
  "owner": "$EXILE",
  "status": "unknown",
  "checks": []
}
EOF

  cat > "$BASE/introspection/dependencies.json" <<EOF
{
  "id": "$EXILE.dependencies",
  "owner": "$EXILE",
  "dependencies": []
}
EOF

done

# Projection is owned by its exile, not duplicated as generic projection folders.
PROJECTION_EXILE="$EXILES_ROOT/projection"

if [ ! -d "$PROJECTION_EXILE" ]; then
  mkdir -p "$PROJECTION_EXILE"
fi

mkdir -p \
  "$PROJECTION_EXILE/runtime" \
  "$PROJECTION_EXILE/registry/views" \
  "$PROJECTION_EXILE/registry/projectors" \
  "$PROJECTION_EXILE/canon" \
  "$PROJECTION_EXILE/graph" \
  "$PROJECTION_EXILE/interface" \
  "$PROJECTION_EXILE/introspection"

cat > "$PROJECTION_EXILE/entity.json" <<'JSON'
{
  "id": "projection",
  "type": "exile",
  "status": "active",
  "owner": "projection",
  "purpose": "Projection owns deterministic derived views across graph, UI, API, runtime, docs, search, and observatory.",
  "rule": "Other exiles do not store projections locally. They expose primitives. Projection derives views."
}
JSON

cat > "$PROJECTION_EXILE/canon/projection_ownership.md" <<'MD'
# PROJECTION EXILE OWNERSHIP
# STATUS: CANON
# AUTHORITY: USER DIRECTIVE

Projection is an exile.

No ontology object should duplicate projection logic locally.

Every entity exposes authoritative primitives.

Projection derives:

- graph views
- UI views
- API views
- runtime views
- documentation views
- search views
- observatory views

Projection owns deterministic projection behavior.
MD

cat > "$PROJECTION_EXILE/registry/views/views.json" <<'JSON'
{
  "id": "projection.views",
  "owner": "projection",
  "views": [
    "graph",
    "ui",
    "api",
    "runtime",
    "docs",
    "search",
    "observatory"
  ]
}
JSON

# Segue structures: every segue owns transition semantics.
find "$ROOT/ontology" -type d -name segue | while read -r SEGUE; do
  mkdir -p \
    "$SEGUE/authority" \
    "$SEGUE/canon" \
    "$SEGUE/graph" \
    "$SEGUE/lineage" \
    "$SEGUE/observatory" \
    "$SEGUE/registry" \
    "$SEGUE/runtime" \
    "$SEGUE/transform" \
    "$SEGUE/validation" \
    "$SEGUE/interface" \
    "$SEGUE/introspection" \
    "$SEGUE/evolution" \
    "$SEGUE/lifecycle"

  cat > "$SEGUE/entity.json" <<EOF
{
  "id": "$(echo "$SEGUE" | sed 's#^/root/savant-runtime/##')",
  "type": "segue",
  "status": "active",
  "purpose": "Nested transition object between parent ontology level and child ontology level.",
  "rule": "A segue is both contained by the parent and parent to the child beneath it."
}
EOF

  cat > "$SEGUE/canon/transition.md" <<'MD'
# SEGUE TRANSITION
# STATUS: CANON

A segue owns the rules for crossing from one ontology level into the next.

It defines:

- inherited authority
- transformed lineage
- created graph edges
- runtime activation
- validation requirements
- projection eligibility
- child interface requirements
MD

  cat > "$SEGUE/registry/contracts.json" <<'JSON'
{
  "id": "segue.contracts",
  "type": "transition_contract_manifest",
  "status": "stub",
  "contracts": []
}
JSON

  cat > "$SEGUE/lineage/inheritance.json" <<'JSON'
{
  "id": "segue.inheritance",
  "type": "lineage_inheritance_rules",
  "status": "stub",
  "inherits": [],
  "transforms": [],
  "blocks": []
}
JSON

  cat > "$SEGUE/graph/edges.json" <<'JSON'
{
  "id": "segue.edges",
  "type": "graph_edge_projection_rules",
  "status": "stub",
  "edges": []
}
JSON
done

# Cross-exile bridge root.
BRIDGES="$EXILES_ROOT/_bridges"
mkdir -p "$BRIDGES"

cat > "$BRIDGES/README.md" <<'MD'
# CROSS-EXILE BRIDGES

Segues govern parent-child ontology transitions.

Bridges govern peer-to-peer exile interactions.

Each bridge should own:

- contracts
- runtime
- events
- authority
- lineage
- graph
- tests
- docs
MD

for PAIR in envoy-opus envoy-palaver opus-vault opus-registry observatory-all; do
  mkdir -p \
    "$BRIDGES/$PAIR/contracts" \
    "$BRIDGES/$PAIR/runtime" \
    "$BRIDGES/$PAIR/events" \
    "$BRIDGES/$PAIR/authority" \
    "$BRIDGES/$PAIR/lineage" \
    "$BRIDGES/$PAIR/graph" \
    "$BRIDGES/$PAIR/tests" \
    "$BRIDGES/$PAIR/docs"

  cat > "$BRIDGES/$PAIR/entity.json" <<EOF
{
  "id": "$PAIR",
  "type": "bridge",
  "status": "stub",
  "owner": "opus",
  "purpose": "Peer interaction bridge."
}
EOF
done

echo "[OK] Semantic file structure expanded."
echo
echo "EXILES:"
find "$EXILES_ROOT" -maxdepth 2 -name entity.json | sort | head -80
echo
echo "SEGUES:"
find "$ROOT/ontology" -type d -name segue | sort
echo
echo "PROJECTION EXILE:"
find "$PROJECTION_EXILE" -maxdepth 3 -type f | sort
