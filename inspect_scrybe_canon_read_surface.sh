#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
SCRYBE="${ROOT}/runtime/scrybe"
CANON="${ROOT}/canon-system"

printf '%s\n' \
  '=== SCRYBE CONSTRUCTOR / RETRIEVAL SURFACE ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import inspect
from runtime.scrybe import Scrybe

print("Scrybe", inspect.signature(Scrybe))

for name in (
    "recall",
    "authority_recall",
    "retrieve_authority",
    "retrieve_lineage",
    "retrieve_provenance",
    "health",
    "validate",
    "profile",
):
    value = getattr(Scrybe, name, None)

    if value is None:
        continue

    print(
        name,
        inspect.signature(value),
    )
'

printf '\n%s\n' \
  '=== SCRYBE RECALL IMPLEMENTATION ==='

sed -n '430,1120p' \
  "${SCRYBE}/engine.py"

printf '\n%s\n' \
  '=== CANONCTL IMPLEMENTATION ==='

cat \
  "${CANON}/runtime/canonctl.py"

printf '\n%s\n' \
  '=== CANON ROOT CONFIG ==='

cat \
  "${CANON}/canon.yaml"

printf '\n%s\n' \
  '=== CANON DATABASE / INDEX FILES ==='

find \
  "${CANON}" \
  -type f \
  \( \
    -name '*.sqlite' \
    -o -name '*.sqlite3' \
    -o -name '*.db' \
    -o -name 'index.json' \
    -o -name '*index*.json' \
  \) \
  ! -path '*/.venv/*' \
  ! -path '*/__pycache__/*' \
  ! -path '*/projections/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' \
  '=== CANON AUTHORITY RECORD SAMPLE ==='

find \
  "${CANON}/authority" \
  -type f \
  \( \
    -name '*.yaml' \
    -o -name '*.yml' \
    -o -name '*.json' \
  \) \
  ! -path '*/schemas/*' \
  -print \
  2>/dev/null \
  | sort \
  | head -n 5 \
  | while IFS= read -r file
    do
        printf '\n--- %s ---\n' \
          "${file}"

        sed -n '1,220p' \
          "${file}"
    done

printf '\n%s\n' \
  '=== RESULT ===' \
  'SCRYBE / CANON READ SURFACE INSPECTION: complete'
