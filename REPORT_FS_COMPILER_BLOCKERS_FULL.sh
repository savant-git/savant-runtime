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

print("=== PYTHON PARSE FAILURES ===")
for row in cur.execute("""
    SELECT path, message
    FROM validation_results
    WHERE validation_id='pass06_python_ast'
      AND check_name='python_parse_failed'
    ORDER BY path
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== UNRESOLVED PYTHON IMPORTS ===")
for row in cur.execute("""
    SELECT f.relpath, p.import_type, p.module, p.symbol, p.resolution_status, p.line_number
    FROM python_imports p
    JOIN files f ON f.id=p.source_file_id
    WHERE p.resolution_status != 'resolved'
    ORDER BY f.relpath, p.line_number
    LIMIT 200
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== UNRESOLVED SHELL DEPENDENCIES ===")
for row in cur.execute("""
    SELECT f.relpath, s.dep_type, s.target_text, s.resolution_status, s.line_number
    FROM shell_dependencies s
    JOIN files f ON f.id=s.source_file_id
    WHERE s.resolution_status NOT IN ('resolved', 'dynamic')
    ORDER BY f.relpath, s.line_number
    LIMIT 200
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== UNRESOLVED TEXT/CONFIG REFERENCES ===")
for row in cur.execute("""
    SELECT f.relpath, t.reference_type, t.reference_value, t.resolution_status, t.line_number
    FROM text_config_references t
    JOIN files f ON f.id=t.source_file_id
    WHERE t.resolution_status NOT IN ('resolved', 'dynamic')
    ORDER BY f.relpath, t.line_number
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
