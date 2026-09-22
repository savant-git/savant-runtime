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

runtime_ops = [
    "/root/savant-runtime/DIAGNOSE_FS_COMPILER_EMPTY_DB.sh",
    "/root/savant-runtime/EXECUTE_SAFE_SCOPE_MOVES_DRY_RUN.sh",
    "/root/savant-runtime/FORCE_REBUILD_FS_COMPILER_DB_FULL.sh",
    "/root/savant-runtime/REBUILD_FS_COMPILER_DB_DIRECT.sh",
    "/root/savant-runtime/REBUILD_FS_COMPILER_DB_FULL.sh",
    "/root/savant-runtime/REPORT_FS_COMPILER_GRAPH_DB.sh",
]

for path in runtime_ops:
    row = cur.execute(
        "SELECT id FROM files WHERE path=?",
        (path,)
    ).fetchone()

    if not row:
        print("[MISS]", path)
        continue

    file_id = row[0]

    cur.execute(
        """
        UPDATE classifications
        SET
            owner='runtime',
            scope='runtime_ops',
            containment='shell_script',
            edifice_level='runtime.ops',
            authority_class='operational_mote',
            move_policy='ELIGIBLE_FOR_PLANNING',
            confidence=95
        WHERE file_id=?
        """,
        (file_id,)
    )

    print("[PATCHED]", path)

con.commit()
con.close()
PY
