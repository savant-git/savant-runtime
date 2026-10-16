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

cur.executescript("""
CREATE TABLE IF NOT EXISTS validation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    validation_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    check_name TEXT NOT NULL,
    file_id TEXT,
    path TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

con.commit()
con.close()

print("[OK] validation_results ready")
PY

./BUILD_SAVANT_FS_COMPILER_PASS_06_PY_IMPORTS.sh
