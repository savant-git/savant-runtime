#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/root/savant-runtime"

cd "$ROOT"

python3 -m json.tool \
  authority_graph/policies/lineage_authority_projection.json \
  >/dev/null

python3 -m py_compile \
  runtime/palaver/authority/authority_engine.py \
  runtime/palaver/contracts/investigation_contract.py \
  runtime/palaver/investigation/investigation_packet_builder.py \
  runtime/palaver/registry/observatory_registry.py \
  runtime/palaver/health/health_snapshot.py \
  tests/lineage/test_runtime_lineage_services.py

find \
  runtime \
  tests/lineage \
  -type d \
  -name '__pycache__' \
  -prune \
  -exec rm -rf {} +

python3 -m unittest discover \
  -s "$ROOT/tests/lineage" \
  -p 'test_*.py' \
  -v

python3 \
  runtime/palaver/lineage/lineage_engine.py

python3 \
  runtime/palaver/graph/runtime_graph_engine.py \
  --no-refresh

python3 \
  runtime/palaver/fields/structural_fields.py

python3 \
  runtime/palaver/topology/topology_compiler.py

python3 \
  runtime/palaver/authority/authority_engine.py

python3 \
  runtime/palaver/investigation/investigation_packet_builder.py \
  --title "Functional lineage implementation" \
  --objective "trace the authority, dependencies, projections, and unresolved regions of the functional lineage implementation" \
  --start runtime \
  --direction both \
  --depth 4

python3 \
  runtime/palaver/registry/observatory_registry.py

python3 \
  runtime/palaver/health/health_snapshot.py

python3 \
  tools/verify_lineage_projection_chain.py

printf '%s\n' \
  "functional lineage integration validation: passed"
