#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/root/savant-runtime"

cd "$ROOT"

python3 -m json.tool \
  authority_graph/kinship/kinship_registry.json \
  >/dev/null

python3 -m py_compile \
  runtime/kinship/__init__.py \
  runtime/kinship/model.py \
  runtime/kinship/registry.py \
  runtime/kinship/graph.py \
  runtime/kinship/algebra.py \
  runtime/kinship/projection.py \
  runtime/kinship/cli.py \
  runtime/kinship/renderers/__init__.py \
  runtime/kinship/renderers/ascii_tree.py \
  runtime/kinship/renderers/dot.py \
  runtime/kinship/renderers/mermaid.py \
  tests/kinship/test_functional_kinship.py

find \
  runtime/kinship \
  tests/kinship \
  -type d \
  -name '__pycache__' \
  -prune \
  -exec rm -rf {} +

python3 -m unittest discover \
  -s "$ROOT/tests/kinship" \
  -p 'test_*.py' \
  -v

python3 -m runtime.kinship.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format ascii \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.txt"

python3 -m runtime.kinship.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format json \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.json"

python3 -m runtime.kinship.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format dot \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.dot"

python3 -m runtime.kinship.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format mermaid \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.mmd"

printf '%s\n' \
  "functional kinship substrate and renderers: passed"
