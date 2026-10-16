#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
SCRYBE="${ROOT}/runtime/scrybe"
LORE="${ROOT}/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/lore"
CANON="${ROOT}/canon-system"

printf '%s\n' \
  '=== SCRYBE PACKAGE ==='

for file in \
  "${SCRYBE}/__init__.py" \
  "${SCRYBE}/engine.py"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== SCRYBE PUBLIC API ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import inspect
import runtime.scrybe.engine as engine

for name in dir(engine):
    if name.startswith("_"):
        continue

    value = getattr(engine, name)

    if not (
        inspect.isclass(value)
        or inspect.isfunction(value)
    ):
        continue

    print(f"\n--- {name} ---")

    try:
        print(inspect.signature(value))
    except (TypeError, ValueError):
        pass

    if inspect.isclass(value):
        for method_name, method in inspect.getmembers(
            value,
            inspect.isfunction,
        ):
            if method_name.startswith("_"):
                continue

            try:
                signature = inspect.signature(method)
            except (TypeError, ValueError):
                signature = ""

            print(f"{method_name}{signature}")
'

printf '\n%s\n' \
  '=== SCRYBE INSTANCE ==='

find \
  "${SCRYBE}/instances" \
  -maxdepth 2 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print0 \
  2>/dev/null \
| while IFS= read -r -d '' file
do
    printf '\n--- %s ---\n' "${file}"
    cat "${file}"
done

printf '\n%s\n' \
  '=== LORE RUNTIME ==='

find \
  "${LORE}/runtime" \
  -maxdepth 3 \
  -type f \
  \( -name '*.py' -o -name '*.json' \) \
  ! -path '*/__pycache__/*' \
  -print0 \
  2>/dev/null \
| while IFS= read -r -d '' file
do
    printf '\n--- %s ---\n' "${file}"
    cat "${file}"
done

printf '\n%s\n' \
  '=== FLUID CANON RUNTIME ==='

for file in \
  "${CANON}/canon.yaml" \
  "${CANON}/runtime/canonctl.py" \
  "${CANON}/runtime/canon_proposals.py" \
  "${CANON}/schemas/canon-record.schema.json" \
  "${CANON}/authority/foundation/dynamic_canon.yaml" \
  "${CANON}/authority/exiles/lore.yaml"
do
    if [ -f "${file}" ]; then
        printf '\n--- %s ---\n' "${file}"
        cat "${file}"
    fi
done

printf '\n%s\n' \
  '=== LIVE CANON RECORDS / STORES ==='

find \
  "${CANON}" \
  -type f \
  \( \
    -name '*.jsonl' \
    -o -name '*.ndjson' \
    -o -name '*.db' \
    -o -name '*.sqlite' \
    -o -name '*.sqlite3' \
    -o -iname '*record*.json' \
    -o -iname '*ledger*.json' \
    -o -iname '*store*.json' \
  \) \
  ! -path '*/.venv/*' \
  ! -path '*/__pycache__/*' \
  ! -path '*/projections/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== LIVE CANON READ / RECALL API ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.venv' \
  --exclude-dir='projections' \
  --exclude-dir='vault' \
  --exclude-dir='node_modules' \
  --exclude-dir='dist' \
  -E \
  'def (get|read|query|search|recall|retrieve|resolve|current|history|list)|class .*Canon|canon_record|canon record|effective|supersed|valid_from|valid_to|authority|lineage|provenance' \
  "${CANON}/runtime" \
  "${LORE}" \
  "${SCRYBE}" \
  2>/dev/null \
  | head -n 500 \
  || true

printf '\n%s\n' \
  '=== SCRYBE LIVE DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='.venv' \
  --exclude-dir='node_modules' \
  --exclude-dir='dist' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  --exclude-dir='.git' \
  -E \
  'runtime\.scrybe|living:scrybe|Scrybe\(' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/canon-system" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 300 \
  || true

printf '\n%s\n' \
  '=== RESULT ===' \
  'LORE / SCRYBE / FLUID CANON FOCUSED INSPECTION: complete'
