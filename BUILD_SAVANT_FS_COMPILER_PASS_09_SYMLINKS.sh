#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
DB="$AUDIT/db/savant_fs_compiler.sqlite"

if [ ! -f "$DB" ]; then
  echo "[ERROR] Missing graph DB."
  exit 1
fi

python3 - <<'PY'
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("DELETE FROM symlinks")

rows = cur.execute(
    """
    SELECT id, path
    FROM files
    WHERE kind='symlink'
    ORDER BY path
    """
).fetchall()

for file_id, path_text in rows:

    path = Path(path_text)

    try:
        target_text = path.readlink().as_posix()
    except Exception as exc:
        target_text = f"[readlink_failed] {exc}"

    try:
        resolved = path.resolve(strict=False)
        target_exists = 1 if resolved.exists() else 0
        resolved_path = str(resolved)
    except Exception:
        resolved_path = ""
        target_exists = 0

    cur.execute(
        """
        INSERT INTO symlinks
        (
            file_id,
            link_path,
            target_text,
            resolved_path,
            target_exists
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            file_id,
            str(path),
            target_text,
            resolved_path,
            target_exists
        )
    )

con.commit()

print("[OK] pass 09 symlink graph built")
print("symlinks:", cur.execute("SELECT count(*) FROM symlinks").fetchone()[0])
print("broken:", cur.execute("SELECT count(*) FROM symlinks WHERE target_exists=0").fetchone()[0])

con.close()
PY
