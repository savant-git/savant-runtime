#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")
con = sqlite3.connect(db)
cur = con.cursor()

print("=== ACTIONABLE PYTHON IMPORT BLOCKERS ===")
for row in cur.execute("""
    SELECT f.relpath, p.module, p.symbol, p.line_number, b.class, b.reason
    FROM blocker_classification b
    JOIN python_imports p ON p.id=b.source_id
    JOIN files f ON f.id=p.source_file_id
    WHERE b.source_table='python_imports'
      AND b.severity='error'
    ORDER BY f.relpath, p.line_number
    LIMIT 200
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== ACTIONABLE SHELL BLOCKERS ===")
for row in cur.execute("""
    SELECT f.relpath, s.dep_type, s.command, s.target_text, s.resolution_status, s.line_number, b.class, b.reason
    FROM blocker_classification b
    JOIN shell_dependencies s ON s.id=b.source_id
    JOIN files f ON f.id=s.source_file_id
    WHERE b.source_table='shell_dependencies'
      AND b.severity='error'
    ORDER BY f.relpath, s.line_number
    LIMIT 200
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== BROKEN SYMLINKS ===")
for row in cur.execute("""
    SELECT link_path, target_text, resolved_path
    FROM symlinks
    WHERE target_exists=0
    ORDER BY link_path
"""):
    print(" | ".join(str(x) for x in row))

con.close()
PY
