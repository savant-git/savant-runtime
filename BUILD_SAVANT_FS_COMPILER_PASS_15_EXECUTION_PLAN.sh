#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"
OUT="/root/savant-runtime/audit/fs_compiler/execution_plan_$(date -u +%Y%m%dT%H%M%SZ).tsv"

python3 - <<'PY' > "$OUT"
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")
con = sqlite3.connect(db)
cur = con.cursor()

validation_id = cur.execute("""
    SELECT validation_id
    FROM validation_results
    WHERE validation_id LIKE 'validation_%'
    ORDER BY id DESC
    LIMIT 1
""").fetchone()

simulation_id = cur.execute("""
    SELECT simulation_id
    FROM simulations
    ORDER BY id DESC
    LIMIT 1
""").fetchone()

print("action\tsource\tproposed_target\twrapper_path\tmkdir_parent\tsha256_before")

if not validation_id or not simulation_id:
    raise SystemExit(0)

validation_id = validation_id[0]
simulation_id = simulation_id[0]

rows = cur.execute("""
    SELECT
        s.source_path,
        s.proposed_target,
        f.sha256
    FROM simulations s
    JOIN files f ON f.id=s.file_id
    LEFT JOIN validation_results v
      ON v.file_id=s.file_id
     AND v.validation_id=?
    WHERE s.simulation_id=?
      AND s.status IN ('PASS', 'PASS_WITH_MKDIR')
      AND coalesce(v.severity, 'info')='info'
    ORDER BY s.source_path
""", (validation_id, simulation_id)).fetchall()

for src, dst, sha in rows:
    parent = str(Path(dst).parent)
    wrapper = src if src.endswith(".sh") else ""
    print(f"MOVE\t{src}\t{dst}\t{wrapper}\t{parent}\t{sha}")

con.close()
PY

echo
echo "[OK] execution plan:"
echo "$OUT"

echo
column -t -s $'\t' "$OUT"
