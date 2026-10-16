#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"
SIM_ID="sim_$(date -u +%Y%m%dT%H%M%SZ)"

python3 - <<'PY'
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
SIM_ID = "sim_pending"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("DELETE FROM simulations WHERE simulation_id=?", (SIM_ID,))

rows = cur.execute(
    """
    SELECT
        m.file_id,
        f.path,
        f.relpath,
        m.proposed_target,
        m.decision,
        m.reason,
        m.confidence,
        m.reference_count
    FROM move_candidates m
    JOIN files f ON f.id=m.file_id
    WHERE m.decision='CANDIDATE'
    ORDER BY f.path
    """
).fetchall()

for (
    file_id,
    source_path,
    relpath,
    proposed_target,
    decision,
    reason,
    confidence,
    reference_count
) in rows:

    src = Path(source_path)
    dst = Path(proposed_target)

    status = "PASS"
    sim_reason = "simulation_passed"

    if not src.exists():
        status = "FAIL"
        sim_reason = "source_missing"

    elif dst.exists():
        status = "FAIL"
        sim_reason = "target_exists"

    elif not dst.parent.exists():
        status = "PASS_WITH_MKDIR"
        sim_reason = "target_parent_would_be_created"

    cur.execute(
        """
        INSERT INTO simulations
        (
            simulation_id,
            file_id,
            source_path,
            proposed_target,
            status,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            SIM_ID,
            file_id,
            str(src),
            str(dst),
            status,
            sim_reason
        )
    )

con.commit()

print("[OK] pass 13 move simulation complete")
print("simulation_id:", SIM_ID)

for status, count in cur.execute("""
    SELECT status, count(*)
    FROM simulations
    WHERE simulation_id=?
    GROUP BY status
    ORDER BY status
""", (SIM_ID,)):
    print(status, count)

con.close()
PY
