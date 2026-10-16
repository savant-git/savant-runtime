#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

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

REQUIRED_DIRS=(
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
  segue
)

make_required() {
  local base="$1"
  for d in "${REQUIRED_DIRS[@]}"; do
    mkdir -p "$base/$d"
  done
  touch "$base/README.md"
  touch "$base/runtime/__init__.py"
}

mkdir -p "$EXILES"

# Remove false/root-level non-exiles.
for bad in runtime projection _audit _bridges _index _reports _retired; do
  if [ -e "$EXILES/$bad" ]; then
    mkdir -p "$EXILES/segue/exile_runtime/retired"
    mv "$EXILES/$bad" "$EXILES/segue/exile_runtime/retired/${bad}_retired_$(date -u +%Y%m%dT%H%M%SZ)"
  fi
done

# Create actual 18 exiles directly in exiles/.
for exile in "${EXILES_LIST[@]}"; do
  make_required "$EXILES/$exile"

  cat > "$EXILES/$exile/entity.json" <<JSON
{
  "id": "$exile",
  "type": "exile",
  "status": "active",
  "template_policy": "actual element overwrites temporary template",
  "segue": "$EXILES/$exile/segue"
}
JSON

  mkdir -p "$EXILES/$exile/segue/prodigals"
done

# If a temporary _template exists, migrate its useful segue contents into exiles/segue, then remove it.
if [ -d "$EXILES/_template/segue" ]; then
  mkdir -p "$EXILES/segue"
  cp -a "$EXILES/_template/segue"/. "$EXILES/segue"/ 2>/dev/null || true
fi

rm -rf "$EXILES/_template"

# Required shared transition infrastructure lives in exiles/segue.
mkdir -p \
  "$EXILES/segue/prodigals" \
  "$EXILES/segue/exile_runtime"

make_required "$EXILES/segue/prodigals"
make_required "$EXILES/segue/exile_runtime"

cat > "$EXILES/segue/entity.json" <<'JSON'
{
  "id": "exiles.segue",
  "type": "segue",
  "status": "active",
  "rule": "Exiles segue into prodigals. Temporary _template folders are overwritten by actual ontology element names."
}
JSON

cat > "$EXILES/segue/exile_runtime/entity.json" <<'JSON'
{
  "id": "exile_runtime",
  "type": "runtime_layer",
  "status": "active",
  "owner": "exiles",
  "rule": "Runtime infrastructure for the Exiles level. Not an exile."
}
JSON

cat > "$EXILES/segue/prodigals/entity.json" <<'JSON'
{
  "id": "prodigals",
  "type": "ontology_level",
  "status": "active",
  "parent": "exiles",
  "rule": "Prodigals are the next ontology level beneath Exiles."
}
JSON

echo "=== EXILES ROOT ==="
find "$EXILES" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort

echo
echo "=== COUNT SHOULD BE 19: 18 EXILES + segue ==="
find "$EXILES" -maxdepth 1 -mindepth 1 -type d | wc -l

echo
echo "=== BAD ROOT FOLDERS CHECK ==="
find "$EXILES" -maxdepth 1 -mindepth 1 -type d \
  \( -name '_template' -o -name 'runtime' -o -name 'projection' -o -name '_audit' -o -name '_bridges' -o -name '_index' -o -name '_reports' -o -name '_retired' \) \
  -print

echo
echo "=== EXILES SEGUE ==="
find "$EXILES/segue" -maxdepth 2 -type d | sort
