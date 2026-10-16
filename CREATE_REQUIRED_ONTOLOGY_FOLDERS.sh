#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
ONTOLOGY="$ROOT/ontology"

EXILES="$ONTOLOGY/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
EXILE_RUNTIME="$EXILES/_template/segue/exile_runtime"
PRODIGALS="$EXILES/_template/segue/prodigals"
PRODIGAL_RUNTIME="$PRODIGALS/_template/segue/prodigal_runtime"
QUIRKS="$PRODIGALS/_template/segue/quirks"
QUIRK_RUNTIME="$QUIRKS/_template/segue/quirk_runtime"

EXILES_LIST=(
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

OBJECT_DIRS=(
  apps
  authority
  cache
  canon
  composition
  dynamic
  evolution
  evolution/migrations
  evolution/supersessions
  evolution/compatibility
  evolution/deprecations
  evolution/history
  facets
  graph
  graph/edges
  graph/nodes
  graph/projections
  graph/relationships
  interface
  interface/api
  interface/capabilities
  interface/contracts
  interface/events
  interface/runtime
  introspection
  lifecycle
  lifecycle/activate
  lifecycle/create
  lifecycle/destroy
  lifecycle/migrate
  lifecycle/recover
  lifecycle/suspend
  lineage
  metrics
  observatory
  observatory/diagnostics
  observatory/events
  observatory/logs
  observatory/metrics
  observatory/traces
  registry
  registry/capabilities
  registry/contracts
  registry/defaults
  registry/interfaces
  registry/manifests
  registry/schemas
  registry/templates
  registry/versions
  runtime
  runtime/api
  runtime/bootstrap
  runtime/bridge
  runtime/contracts
  runtime/events
  runtime/orchestration
  runtime/pipeline
  runtime/protocol
  runtime/providers
  runtime/services
  runtime/workers
  sessions
  state
  static
  tests
  validation
  _template
  _template/segue
)

SEGUE_DIRS=(
  authority
  canon
  composition
  evolution
  graph
  interface
  introspection
  lifecycle
  lineage
  observatory
  registry
  runtime
  validation
)

create_object_layout() {
  local base="$1"
  local id="$2"
  local type="$3"

  mkdir -p "$base"

  for d in "${OBJECT_DIRS[@]}"; do
    mkdir -p "$base/$d"
  done

  touch "$base/README.md"
  touch "$base/runtime/__init__.py"

  if [ ! -f "$base/entity.json" ]; then
    cat > "$base/entity.json" <<JSON
{
  "id": "$id",
  "type": "$type",
  "status": "active",
  "authority": "$base/authority",
  "canon": "$base/canon",
  "lineage": "$base/lineage",
  "graph": "$base/graph",
  "registry": "$base/registry",
  "runtime": "$base/runtime",
  "interface": "$base/interface",
  "introspection": "$base/introspection",
  "facets": "$base/facets",
  "template": "$base/_template"
}
JSON
  fi
}

create_segue_layout() {
  local base="$1"
  local id="$2"

  mkdir -p "$base"

  for d in "${SEGUE_DIRS[@]}"; do
    mkdir -p "$base/$d"
  done

  touch "$base/README.md"

  if [ ! -f "$base/entity.json" ]; then
    cat > "$base/entity.json" <<JSON
{
  "id": "$id",
  "type": "segue",
  "status": "active",
  "purpose": "Transition layer governing inheritance, validation, graph edges, lineage, authority, runtime activation, and child ontology creation."
}
JSON
  fi
}

mkdir -p "$EXILES"

for exile in "${EXILES_LIST[@]}"; do
  create_object_layout "$EXILES/$exile" "$exile" "exile"
done

create_segue_layout "$EXILES/_template/segue" "exiles.template.segue"
create_object_layout "$EXILE_RUNTIME" "exile_runtime" "runtime_layer"
create_object_layout "$PRODIGALS" "prodigals" "ontology_level"

create_segue_layout "$PRODIGALS/_template/segue" "prodigals.template.segue"
create_object_layout "$PRODIGAL_RUNTIME" "prodigal_runtime" "runtime_layer"
create_object_layout "$QUIRKS" "quirks" "ontology_level"

create_segue_layout "$QUIRKS/_template/segue" "quirks.template.segue"
create_object_layout "$QUIRK_RUNTIME" "quirk_runtime" "runtime_layer"

mkdir -p \
  "$EXILES/_bridges" \
  "$EXILES/_retired" \
  "$EXILES/_reports" \
  "$EXILES/_index" \
  "$EXILES/_audit"

cat > "$EXILE_RUNTIME/canon/required_ontology_layout.md" <<'MD'
# REQUIRED ONTOLOGY LAYOUT
# STATUS: CANON
# OWNER: EXILE RUNTIME

Every ontology object must expose the same required folders from birth.

Empty folders are valid.
Missing folders are invalid.

Required object folders:

- apps
- authority
- cache
- canon
- composition
- dynamic
- evolution
- facets
- graph
- interface
- introspection
- lifecycle
- lineage
- metrics
- observatory
- registry
- runtime
- sessions
- state
- static
- tests
- validation
- _template/segue

Exiles segue into Prodigals.
Prodigals segue into Quirks.
Quirks segue into later ontology levels.

Runtime layers are transition infrastructure, not ontology children.
MD

cat > "$EXILE_RUNTIME/registry/exiles.json" <<'JSON'
{
  "count": 18,
  "exiles": [
    "carbon",
    "cataxis",
    "coda",
    "envoy",
    "filament",
    "graffiti",
    "lore",
    "mobius",
    "modus",
    "niche",
    "notary",
    "opus",
    "pact",
    "palaver",
    "shatter",
    "underscore",
    "urge",
    "zero"
  ]
}
JSON

cat > "$EXILE_RUNTIME/registry/required_directories.json" <<'JSON'
{
  "object_required": [
    "apps",
    "authority",
    "cache",
    "canon",
    "composition",
    "dynamic",
    "evolution",
    "evolution/migrations",
    "evolution/supersessions",
    "evolution/compatibility",
    "evolution/deprecations",
    "evolution/history",
    "facets",
    "graph",
    "graph/edges",
    "graph/nodes",
    "graph/projections",
    "graph/relationships",
    "interface",
    "interface/api",
    "interface/capabilities",
    "interface/contracts",
    "interface/events",
    "interface/runtime",
    "introspection",
    "lifecycle",
    "lifecycle/activate",
    "lifecycle/create",
    "lifecycle/destroy",
    "lifecycle/migrate",
    "lifecycle/recover",
    "lifecycle/suspend",
    "lineage",
    "metrics",
    "observatory",
    "observatory/diagnostics",
    "observatory/events",
    "observatory/logs",
    "observatory/metrics",
    "observatory/traces",
    "registry",
    "registry/capabilities",
    "registry/contracts",
    "registry/defaults",
    "registry/interfaces",
    "registry/manifests",
    "registry/schemas",
    "registry/templates",
    "registry/versions",
    "runtime",
    "runtime/api",
    "runtime/bootstrap",
    "runtime/bridge",
    "runtime/contracts",
    "runtime/events",
    "runtime/orchestration",
    "runtime/pipeline",
    "runtime/protocol",
    "runtime/providers",
    "runtime/services",
    "runtime/workers",
    "sessions",
    "state",
    "static",
    "tests",
    "validation",
    "_template",
    "_template/segue"
  ],
  "segue_required": [
    "authority",
    "canon",
    "composition",
    "evolution",
    "graph",
    "interface",
    "introspection",
    "lifecycle",
    "lineage",
    "observatory",
    "registry",
    "runtime",
    "validation"
  ]
}
JSON

echo "[OK] Required ontology folders created."
echo
echo "EXILES ROOT:"
find "$EXILES" -maxdepth 1 -mindepth 1 -type d | sort
echo
echo "EXILE TEMPLATE SEGUE:"
find "$EXILES/_template/segue" -maxdepth 2 -type d | sort
echo
echo "PRODIGALS:"
find "$PRODIGALS" -maxdepth 2 -type d | sort
echo
echo "QUIRKS:"
find "$QUIRKS" -maxdepth 2 -type d | sort
