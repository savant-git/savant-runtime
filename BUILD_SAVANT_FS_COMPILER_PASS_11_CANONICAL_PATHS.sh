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
import re
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS canonical_path_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    claimed_path TEXT NOT NULL,
    claimed_relpath TEXT NOT NULL DEFAULT '',
    target_exists INTEGER NOT NULL DEFAULT 0,
    line_number INTEGER NOT NULL DEFAULT 0,
    line_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_claimed_path
ON canonical_path_claims(claimed_path);
""")

cur.execute("DELETE FROM canonical_path_claims")

rows = cur.execute(
    """
    SELECT id, path
    FROM files
    WHERE ignored=0
      AND kind='file'
    ORDER BY path
    """
).fetchall()

patterns = [
    re.compile(r"/root/savant-runtime/[A-Za-z0-9_./{}$():-]+"),
    re.compile(r"ontology/obelisks/[A-Za-z0-9_./{}$():-]+"),
]

for file_id, path_text in rows:
    path = Path(path_text)

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines()
    except Exception:
        continue

    for line_number, line in enumerate(lines, start=1):
        for pattern in patterns:
            for match in pattern.findall(line):
                claimed = match.rstrip('",;)]}')

                if "$" in claimed or "{" in claimed or "(" in claimed:
                    continue

                if claimed.startswith("/root/savant-runtime/"):
                    full = Path(claimed)
                    rel = str(full.relative_to(ROOT)) if str(full).startswith(str(ROOT)) else ""
                else:
                    rel = claimed
                    full = ROOT / claimed

                cur.execute(
                    """
                    INSERT INTO canonical_path_claims
                    (
                        source_file_id,
                        claimed_path,
                        claimed_relpath,
                        target_exists,
                        line_number,
                        line_text
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        str(full),
                        rel,
                        1 if full.exists() else 0,
                        line_number,
                        line[:500]
                    )
                )

con.commit()

print("[OK] pass 11 canonical path claims built")
print("claims:", cur.execute("SELECT count(*) FROM canonical_path_claims").fetchone()[0])
print("existing:", cur.execute("SELECT count(*) FROM canonical_path_claims WHERE target_exists=1").fetchone()[0])
print("missing:", cur.execute("SELECT count(*) FROM canonical_path_claims WHERE target_exists=0").fetchone()[0])

con.close()
PY
