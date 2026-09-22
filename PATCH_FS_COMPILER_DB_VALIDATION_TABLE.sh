#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")

if not db.exists():
    raise SystemExit(f"[ERROR] Missing DB: {db}")

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

CREATE INDEX IF NOT EXISTS idx_validation_id
ON validation_results(validation_id);

CREATE INDEX IF NOT EXISTS idx_validation_severity
ON validation_results(severity);
""")

con.commit()

print("[OK] validation_results table ensured")
print("validation rows:", cur.execute("SELECT count(*) FROM validation_results").fetchone()[0])

con.close()
PY
