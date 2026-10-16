#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
DB="$AUDIT/db/savant_fs_compiler.sqlite"

echo "=== ROOT ==="
pwd
du -sh "$ROOT" 2>/dev/null || true

echo
echo "=== AUDIT DIR ==="
find "$AUDIT" -maxdepth 3 -type f 2>/dev/null | sort | tail -80 || true

echo
echo "=== LATEST PASS FILES ==="
for pattern in \
  'pass01_inventory_*.tsv' \
  'pass02_semantic_classification_*.tsv' \
  'pass03_reference_graph_*.tsv'
do
  latest="$(find "$AUDIT" -type f -name "$pattern" 2>/dev/null | sort | tail -1 || true)"
  echo "$pattern => ${latest:-MISSING}"
  if [ -n "$latest" ]; then
    echo "lines: $(wc -l < "$latest")"
    echo "head:"
    sed -n '1,5p' "$latest"
    echo
  fi
done

echo
echo "=== DB CHECK ==="
if [ ! -f "$DB" ]; then
  echo "[MISSING DB] $DB"
else
  ls -lh "$DB"
  python3 - <<'PY'
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")
con = sqlite3.connect(db)
cur = con.cursor()

for table in [
    "files",
    "classifications",
    "references_found",
    "python_imports",
    "shell_dependencies",
    "service_references",
    "symlinks",
    "duplicate_hashes",
]:
    try:
        count = cur.execute(f"select count(*) from {table}").fetchone()[0]
        print(f"{table}: {count}")
    except Exception as exc:
        print(f"{table}: ERROR {exc}")

con.close()
PY
fi

echo
echo "=== DIRECT FILE COUNTS ==="
echo "all objects:"
find "$ROOT" -mindepth 1 \( -type f -o -type d -o -type l \) 2>/dev/null | wc -l

echo "python files:"
find "$ROOT" -type f -name '*.py' 2>/dev/null | wc -l

echo "shell files:"
find "$ROOT" -type f -name '*.sh' 2>/dev/null | wc -l
