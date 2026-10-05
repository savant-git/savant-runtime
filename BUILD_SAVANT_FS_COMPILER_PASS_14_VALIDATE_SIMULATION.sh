#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"
VALIDATION_ID="validation_$(date -u +%Y%m%dT%H%M%SZ)"

python3 - <<'PY'
import sqlite3
from pathlib import Path

DB = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")
VALIDATION_ID = "validation_pending"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("DELETE FROM validation_results WHERE validation_id=?", (VALIDATION_ID,))

sim_id = cur.execute(
    """
    SELECT simulation_id
    FROM simulations
    ORDER BY id DESC
    LIMIT 1
    """
).fetchone()

if not sim_id:
    raise SystemExit("[ERROR] No simulation found. Run pass 13 first.")

sim_id = sim_id[0]

rows = cur.execute(
    """
    SELECT
        s.file_id,
        s.source_path,
        s.proposed_target,
        s.status,
        s.reason,
        f.basename,
        c.scope,
        c.owner,
        c.containment,
        c.move_policy
    FROM simulations s
    JOIN files f ON f.id=s.file_id
    JOIN classifications c ON c.file_id=s.file_id
    WHERE s.simulation_id=?
    ORDER BY s.source_path
    """,
    (sim_id,)
).fetchall()

for (
    file_id,
    source_path,
    proposed_target,
    status,
    reason,
    basename,
    scope,
    owner,
    containment,
    move_policy
) in rows:

    severity = "info"
    check = "simulation_ok"
    message = "Simulation passed."

    if status.startswith("FAIL"):
        severity = "error"
        check = "simulation_failed"
        message = reason

    elif containment in {
        "application_package",
        "runtime_protocol_package",
        "runtime_provider_package",
        "runtime_event_bus_package",
        "projection_engine_package",
    }:
        severity = "error"
        check = "package_boundary_violation"
        message = "Move would cross or flatten a package boundary."

    elif basename in {"__init__.py", "package.json", "pyproject.toml", "requirements.txt"}:
        severity = "warning"
        check = "package_anchor_sensitive"
        message = "Package or environment anchor file requires manual review."

    elif scope == "unknown" or owner == "unknown":
        severity = "warning"
        check = "unknown_scope_or_owner"
        message = "Unknown scope or owner requires manual review."

    cur.execute(
        """
        INSERT INTO validation_results
        (
            validation_id,
            severity,
            check_name,
            file_id,
            path,
            message
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            VALIDATION_ID,
            severity,
            check,
            file_id,
            source_path,
            message
        )
    )

con.commit()

print("[OK] pass 14 simulation validation complete")
print("simulation_id:", sim_id)
print("validation_id:", VALIDATION_ID)

for severity, count in cur.execute("""
    SELECT severity, count(*)
    FROM validation_results
    WHERE validation_id=?
    GROUP BY severity
    ORDER BY severity
""", (VALIDATION_ID,)):
    print(severity, count)

con.close()
PY
