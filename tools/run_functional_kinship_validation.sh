#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/root/savant-runtime"

cd "$ROOT"

python3 -m json.tool \
  authority_graph/kindred/kindred_registry.json \
  >/dev/null

python3 -m py_compile \
  runtime/kindred/__init__.py \
  runtime/kindred/model.py \
  runtime/kindred/registry.py \
  runtime/kindred/graph.py \
  runtime/kindred/algebra.py \
  runtime/kindred/projection.py \
  runtime/kindred/cli.py \
  runtime/kindred/renderers/__init__.py \
  runtime/kindred/renderers/ascii_tree.py \
  runtime/kindred/renderers/dot.py \
  runtime/kindred/renderers/mermaid.py \
  tests/kindred/test_functional_kindred.py

find \
  runtime/kindred \
  tests/kindred \
  -type d \
  -name '__pycache__' \
  -prune \
  -exec rm -rf {} +

python3 -m unittest discover \
  -s "$ROOT/tests/kindred" \
  -p 'test_*.py' \
  -v

python3 -m runtime.kindred.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format ascii \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.txt"

python3 -m runtime.kindred.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format json \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.json"

python3 -m runtime.kindred.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format dot \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.dot"

python3 -m runtime.kindred.cli \
  savant-runtime \
  --graph \
  "$ROOT/vault/graphs/runtime_graph.json" \
  --format mermaid \
  --depth 3 \
  --output \
  "$ROOT/vault/graphs/family_tree_savant-runtime.mmd"

printf '%s\n' \
  "functional kindred substrate and renderers: passed"
