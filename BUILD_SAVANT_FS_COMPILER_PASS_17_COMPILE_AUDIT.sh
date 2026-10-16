#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import json
import py_compile
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS compile_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,
    path TEXT NOT NULL,
    language TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_compile_audit_status
ON compile_audit(status);
""")

cur.execute("DELETE FROM compile_audit")

rows = cur.execute("""
    SELECT id, path, extension, basename
    FROM files
    WHERE ignored=0
      AND kind='file'
    ORDER BY path
""").fetchall()

for file_id, path_text, extension, basename in rows:
    path = Path(path_text)

    if extension == "py":
        try:
            py_compile.compile(str(path), doraise=True)
            status = "ok"
            message = ""
        except Exception as e:
            status = "fail"
            message = str(e)

        cur.execute(
            """
            INSERT INTO compile_audit
            (file_id, path, language, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_id, str(path), "python", status, message)
        )

    elif extension == "sh":
        try:
            proc = subprocess.run(
                ["bash", "-n", str(path)],
                text=True,
                capture_output=True,
                timeout=20
            )
            status = "ok" if proc.returncode == 0 else "fail"
            message = (proc.stderr or proc.stdout or "").strip()
        except Exception as e:
            status = "fail"
            message = str(e)

        cur.execute(
            """
            INSERT INTO compile_audit
            (file_id, path, language, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_id, str(path), "shell", status, message)
        )

    elif extension == "json":
        try:
            json.loads(path.read_text(encoding="utf-8", errors="replace"))
            status = "ok"
            message = ""
        except Exception as e:
            status = "fail"
            message = str(e)

        cur.execute(
            """
            INSERT INTO compile_audit
            (file_id, path, language, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_id, str(path), "json", status, message)
        )

con.commit()

print("[OK] pass 17 compile audit complete")

for language, status, count in cur.execute("""
    SELECT language, status, count(*)
    FROM compile_audit
    GROUP BY language, status
    ORDER BY language, status
"""):
    print(language, status, count)

con.close()
PY
