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

print("=== MOVE CANDIDATES ===")
for row in cur.execute("""
    SELECT decision, reason, count(*)
    FROM move_candidates
    GROUP BY decision, reason
    ORDER BY decision, reason
"""):
    print(" | ".join(str(x) for x in row))

print()
print("=== LATEST SIMULATION ===")
sim = cur.execute("""
    SELECT simulation_id
    FROM simulations
    ORDER BY id DESC
    LIMIT 1
""").fetchone()

if sim:
    sim_id = sim[0]
    print("simulation_id:", sim_id)

    for row in cur.execute("""
        SELECT status, reason, count(*)
        FROM simulations
        WHERE simulation_id=?
        GROUP BY status, reason
        ORDER BY status, reason
    """, (sim_id,)):
        print(" | ".join(str(x) for x in row))
else:
    print("none")

print()
print("=== LATEST VALIDATION ===")
val = cur.execute("""
    SELECT validation_id
    FROM validation_results
    WHERE validation_id LIKE 'validation_%'
    ORDER BY id DESC
    LIMIT 1
""").fetchone()

if val:
    val_id = val[0]
    print("validation_id:", val_id)

    for row in cur.execute("""
        SELECT severity, check_name, count(*)
        FROM validation_results
        WHERE validation_id=?
        GROUP BY severity, check_name
        ORDER BY severity, check_name
    """, (val_id,)):
        print(" | ".join(str(x) for x in row))
else:
    print("none")

print()
print("=== EXECUTION-ELIGIBLE FILES ===")
query = """
    SELECT
        s.source_path,
        s.proposed_target
    FROM simulations s
    LEFT JOIN validation_results v
      ON v.file_id=s.file_id
     AND v.validation_id=(
        SELECT validation_id
        FROM validation_results
        WHERE validation_id LIKE 'validation_%'
        ORDER BY id DESC
        LIMIT 1
     )
    WHERE s.simulation_id=(
        SELECT simulation_id
        FROM simulations
        ORDER BY id DESC
        LIMIT 1
    )
      AND s.status IN ('PASS', 'PASS_WITH_MKDIR')
      AND coalesce(v.severity, 'info')='info'
    ORDER BY s.source_path
"""

rows = list(cur.execute(query))

if not rows:
    print("none")
else:
    for src, dst in rows:
        print(f"{src} -> {dst}")

print()
print("=== BLOCKERS ===")
for row in cur.execute("""
    SELECT
        v.severity,
        v.check_name,
        v.path,
        v.message
    FROM validation_results v
    WHERE v.validation_id=(
        SELECT validation_id
        FROM validation_results
        WHERE validation_id LIKE 'validation_%'
        ORDER BY id DESC
        LIMIT 1
    )
      AND v.severity != 'info'
    ORDER BY v.severity, v.check_name, v.path
    LIMIT 160
"""):
    print(" | ".join(str(x) for x in row))

con.close()
PY
