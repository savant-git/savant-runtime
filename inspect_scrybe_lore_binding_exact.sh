#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
ENGINE="${ROOT}/runtime/scrybe/engine.py"
INSTANCE="${ROOT}/runtime/scrybe/instances/lore.json"
CANONCTL="${ROOT}/canon-system/runtime/canonctl.py"
DB="${ROOT}/canon-system/runtime/canon.sqlite3"

printf '%s\n' '=== SCRYBE EXACT PUBLIC SIGNATURES ==='

PYTHONPATH="${ROOT}" python3 -c '
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
    if value is not None:
        print(name, inspect.signature(value))
'

printf '\n%s\n' '=== SCRYBE RECALL METHODS ==='

python3 -c '
from pathlib import Path
import ast

path = Path("/root/savant-runtime/runtime/scrybe/engine.py")
tree = ast.parse(path.read_text(encoding="utf-8"))

wanted = {
    "__init__",
    "recall",
    "authority_recall",
    "retrieve_authority",
    "retrieve_lineage",
    "retrieve_provenance",
}

source = path.read_text(encoding="utf-8").splitlines()

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
        print(f"\n--- {node.name} ---")
        end = getattr(node, "end_lineno", node.lineno)
        print("\n".join(source[node.lineno - 1:end]))
'

printf '\n%s\n' '=== SCRYBE LORE INSTANCE ==='

cat "${INSTANCE}"

printf '\n%s\n' '=== CANON SQLITE SCHEMA ==='

python3 -c '
import sqlite3

db = sqlite3.connect(
    "/root/savant-runtime/canon-system/runtime/canon.sqlite3"
)

try:
    rows = db.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type IN ("table", "view", "index")
        ORDER BY type, name
        """
    ).fetchall()

    for name, sql in rows:
        print(f"\n--- {name} ---")
        print(sql or "")
finally:
    db.close()
'

printf '\n%s\n' '=== CANONCTL DATABASE BUILD / READ LOGIC ==='

python3 -c '
from pathlib import Path
import ast

path = Path("/root/savant-runtime/canon-system/runtime/canonctl.py")
tree = ast.parse(path.read_text(encoding="utf-8"))
source = path.read_text(encoding="utf-8").splitlines()

wanted = {
    "build_db",
    "validate",
    "project",
    "supersede",
}

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
        print(f"\n--- {node.name} ---")
        end = getattr(node, "end_lineno", node.lineno)
        print("\n".join(source[node.lineno - 1:end]))
'

printf '\n%s\n' '=== DATABASE ROW SAMPLE ==='

python3 -c '
import sqlite3

db = sqlite3.connect(
    "/root/savant-runtime/canon-system/runtime/canon.sqlite3"
)
db.row_factory = sqlite3.Row

try:
    tables = [
        row[0]
        for row in db.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = "table"
              AND name NOT LIKE "sqlite_%"
            ORDER BY name
            """
        )
    ]

    for table in tables:
        print(f"\n--- {table} ---")

        try:
            rows = db.execute(
                f"SELECT * FROM [{table}] LIMIT 2"
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            print(type(exc).__name__, str(exc))
            continue

        for row in rows:
            print(dict(row))
finally:
    db.close()
'

printf '\n%s\n' '=== RESULT ==='
printf '%s\n' 'SCRYBE / LORE BINDING EXACT INSPECTION: complete'
