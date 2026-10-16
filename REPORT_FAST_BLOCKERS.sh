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

print("=== UNRESOLVED PYTHON IMPORTS TOP 120 ===")
for row in cur.execute("""
select f.relpath, p.import_type, p.module, p.symbol, p.level, p.resolution_status, p.line_number
from python_imports p
join files f on f.id=p.source_file_id
where p.resolution_status != 'resolved'
order by f.relpath, p.line_number
limit 120
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== BROKEN SYMLINKS ===")
for row in cur.execute("""
select link_path, target_text, resolved_path
from symlinks
where target_exists=0
order by link_path
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== UNRESOLVED SHELL DEPS TOP 120 ===")
for row in cur.execute("""
select f.relpath, s.dep_type, s.command, s.target_text, s.resolution_status, s.line_number
from shell_dependencies s
join files f on f.id=s.source_file_id
where s.resolution_status not in ('resolved','dynamic')
order by f.relpath, s.line_number
limit 120
"""):
    print(" | ".join(str(x) for x in row))

con.close()
PY
