#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
DRYVE="${ROOT}/runtime/dryve"

printf '%s\n' \
  '=== DRYVE __INIT__ ==='

cat \
  "${DRYVE}/__init__.py"

printf '\n%s\n' \
  '=== DRYVE ENGINE PUBLIC SYMBOLS ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import runtime.dryve.engine as engine

print([
    name
    for name in dir(engine)
    if not name.startswith("_")
])
'

printf '\n%s\n' \
  '=== OWNER BINDING PUBLIC SYMBOLS ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import runtime.dryve.owner_binding as binding

print([
    name
    for name in dir(binding)
    if not name.startswith("_")
])
'

printf '\n%s\n' \
  '=== RESULT ===' \
  'DRYVE EXPORT INSPECTION: complete'
