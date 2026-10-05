#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import json
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")

if not db.exists():
    raise SystemExit(f"[ERROR] Missing DB: {db}")

con = sqlite3.connect(db)
cur = con.cursor()

def section(title):
    print()
    print(f"=== {title} ===")

section("FILES")
for row in cur.execute("""
    select kind, count(*)
    from files
    where ignored=0
    group by kind
    order by kind
"""):
    print(" | ".join(str(x) for x in row))

section("PYTHON IMPORTS")
for row in cur.execute("""
    select resolution_status, count(*)
    from python_imports
    group by resolution_status
    order by resolution_status
"""):
    print(" | ".join(str(x) for x in row))

section("SHELL DEPENDENCIES")
for row in cur.execute("""
    select resolution_status, count(*)
    from shell_dependencies
    group by resolution_status
    order by resolution_status
"""):
    print(" | ".join(str(x) for x in row))

section("SERVICE REFERENCES")
for row in cur.execute("""
    select service_type, resolution_status, count(*)
    from service_references
    group by service_type, resolution_status
    order by service_type, resolution_status
"""):
    print(" | ".join(str(x) for x in row))

section("SYMLINKS")
for row in cur.execute("""
    select target_exists, count(*)
    from symlinks
    group by target_exists
    order by target_exists
"""):
    label = "exists" if row[0] else "broken"
    print(label, "|", row[1])

section("DUPLICATES")
for row in cur.execute("""
    select count(*), coalesce(sum(file_count), 0)
    from duplicate_hashes
"""):
    print("duplicate_groups | duplicate_files")
    print(f"{row[0]} | {row[1]}")

section("BROKEN SYMLINKS")
for row in cur.execute("""
    select link_path, target_text, resolved_path
    from symlinks
    where target_exists=0
    order by link_path
    limit 80
"""):
    print(" | ".join(str(x) for x in row))

section("UNRESOLVED SHELL DEPENDENCIES")
for row in cur.execute("""
    select f.relpath, s.dep_type, s.target_text, s.resolution_status, s.line_number
    from shell_dependencies s
    join files f on f.id=s.source_file_id
    where s.resolution_status != 'resolved'
    order by f.relpath, s.line_number
    limit 120
"""):
    print(" | ".join(str(x) for x in row))

section("DUPLICATE GROUPS")
for sha, count, paths_json in cur.execute("""
    select sha256, file_count, paths_json
    from duplicate_hashes
    order by file_count desc, sha256
    limit 30
"""):
    paths = json.loads(paths_json)
    print()
    print(f"{sha} ({count})")
    for path in paths[:12]:
        print(f"  {path}")

con.close()
PY
