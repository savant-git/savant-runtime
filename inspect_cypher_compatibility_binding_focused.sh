#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
CYPHER="${ROOT}/runtime/cypher"

printf '%s\n' '=== CYPHER FILES ==='

find \
  "${CYPHER}" \
  -maxdepth 3 \
  -type f \
  ! -path '*/__pycache__/*' \
  -print \
  2>/dev/null \
  | sort

printf '\n%s\n' '=== CYPHER __INIT__ ==='

if [ -f "${CYPHER}/__init__.py" ]; then
    cat "${CYPHER}/__init__.py"
fi

printf '\n%s\n' '=== CYPHER ENGINE PUBLIC SYMBOLS ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import runtime.cypher.engine as engine

print([
    name
    for name in dir(engine)
    if not name.startswith("_")
])
'

printf '\n%s\n' '=== CYPHER ENGINE API ==='

PYTHONPATH="${ROOT}" \
python3 -c '
import inspect
import runtime.cypher.engine as engine

for name in (
    "Cypher",
    "TranslationSpec",
    "CompatibilitySpec",
    "AdapterSpec",
):
    value = getattr(
        engine,
        name,
        None,
    )

    if value is None:
        continue

    print(
        "\n---",
        name,
        "---",
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

    if inspect.isclass(
        value
    ):
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
                method_name,
                signature,
            )
'

printf '\n%s\n' '=== CYPHER INSTANCES ==='

if [ -d "${CYPHER}/instances" ]; then
    find \
      "${CYPHER}/instances" \
      -maxdepth 2 \
      -type f \
      -print0 \
      | sort -z \
      | while IFS= read -r -d "" file
        do
            printf '\n--- %s ---\n' "${file}"
            cat "${file}"
        done
fi

printf '\n%s\n' '=== LIVE COMPATIBILITY PRIMITIVES ==='

find \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  -type f \
  \( \
    -iname '*adapter*' \
    -o -iname '*compat*' \
    -o -iname '*bridge*' \
    -o -iname '*translat*' \
    -o -iname '*serializ*' \
    -o -iname '*normaliz*' \
  \) \
  ! -path '*/__pycache__/*' \
  ! -path '*/vault/*' \
  ! -path '*/assurance/structure-intelligence/*' \
  -print \
  2>/dev/null \
  | sort \
  | head -n 300

printf '\n%s\n' '=== CYPHER LIVE REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  --exclude-dir='.git' \
  -E \
  'runtime\.cypher|living:cypher|Cypher\(|Cypher\b|cypher\b' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  "${ROOT}/assurance" \
  "${ROOT}/bin" \
  2>/dev/null \
  | head -n 350 \
  || true

printf '\n%s\n' '=== TRANSPORT OWNERSHIP REFERENCES ==='

grep -RIn \
  --exclude='*.pyc' \
  --exclude-dir='__pycache__' \
  --exclude-dir='vault' \
  --exclude-dir='structure-intelligence' \
  --exclude-dir='.git' \
  -E \
  'transport_owner|transport owner|network transport|http transport|message transport|socket|routing owner|conversation_owner' \
  "${ROOT}/runtime" \
  "${ROOT}/ontology" \
  2>/dev/null \
  | head -n 250 \
  || true

printf '\n%s\n' '=== RESULT ==='
printf '%s\n' 'CYPHER FOCUSED COMPATIBILITY INSPECTION: complete'
