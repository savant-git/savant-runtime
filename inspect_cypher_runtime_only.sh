#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
CYPHER="${ROOT}/runtime/cypher"

printf '%s\n' \
  '=== CYPHER __INIT__ ==='

cat \
  "${CYPHER}/__init__.py"

printf '\n%s\n' \
  '=== CYPHER ENGINE HEADER ==='

sed -n '1,260p' \
  "${CYPHER}/engine.py"

printf '\n%s\n' \
  '=== CYPHER PUBLIC API ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import inspect
import runtime.cypher.engine as engine

for name in dir(engine):
    if name.startswith("_"):
        continue

    value = getattr(
        engine,
        name,
    )

    if not (
        inspect.isclass(value)
        or inspect.isfunction(value)
    ):
        continue

    print(
        f"\n--- {name} ---"
    )

    try:
        print(
            inspect.signature(
                value
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        pass

    if inspect.isclass(value):
        for method_name, method in (
            inspect.getmembers(
                value,
                inspect.isfunction,
            )
        ):
            if method_name.startswith(
                "_"
            ):
                continue

            try:
                signature = (
                    inspect.signature(
                        method
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                signature = ""

            print(
                f"{method_name}{signature}"
            )
'

printf '\n%s\n' \
  '=== CYPHER CONSTANTS ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import runtime.cypher.engine as engine

for name in (
    "CYPHER_ABILITIES",
    "CYPHER_PIPELINE",
    "CYPHER_PROJECTIONS",
    "CYPHER_HEALTH_DIMENSIONS",
    "CYPHER_VALIDATION_DIMENSIONS",
):
    if hasattr(
        engine,
        name,
    ):
        print(
            name,
            "=",
            getattr(
                engine,
                name,
            ),
        )
'

printf '\n%s\n' \
  '=== CYPHER INSTANCE ==='

find \
  "${CYPHER}/instances" \
  -maxdepth 2 \
  -type f \
  -print0 \
  2>/dev/null \
| while IFS= read -r -d '' file
do
    printf '\n--- %s ---\n' \
      "${file}"

    cat \
      "${file}"
done

printf '\n%s\n' \
  '=== LIVE CYPHER DEPENDENTS ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='node_modules' \
  --exclude-dir='dist' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  --exclude-dir='.git' \
  -E \
  'runtime\.cypher|living:cypher|from .*cypher|import .*cypher|Cypher\(' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 300 \
  || true

printf '\n%s\n' \
  '=== LIVE COMPATIBILITY IMPLEMENTATIONS ==='

find \
  "${ROOT}/runtime" \
  "${ROOT}/
