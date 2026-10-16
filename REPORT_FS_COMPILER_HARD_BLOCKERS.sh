#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import sqlite3
from pathlib import Path

DB = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")
con = sqlite3.connect(DB)
cur = con.cursor()

print("=== HARD SAFETY GATE ===")
for row in cur.execute("""
    SELECT status, gate_name, blocker_count, message
    FROM hard_safety_gate
    ORDER BY status, gate_name
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== COMPILE FAILURES ===")
for row in cur.execute("""
    SELECT language, path, message
    FROM compile_audit
    WHERE status!='ok'
    ORDER BY language, path
    LIMIT 300
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

print()
print("=== BLOCKED MOVE CANDIDATES ===")
for row in cur.execute("""
    SELECT f.path, m.proposed_target, m.reason, m.reference_count
    FROM move_candidates m
    JOIN files f ON f.id=m.file_id
    WHERE m.decision='BLOCK'
    ORDER BY m.reason, f.path
    LIMIT 300
"""):
    print(" | ".join(str(x) for x in row))

con.close()
PY
