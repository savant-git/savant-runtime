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
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("DELETE FROM duplicate_hashes")

rows = cur.execute(
    """
    SELECT sha256, path
    FROM files
    WHERE ignored=0
      AND kind='file'
      AND sha256 != ''
    ORDER BY sha256, path
    """
).fetchall()

groups = defaultdict(list)

for sha, path in rows:
    groups[sha].append(path)

for sha, paths in groups.items():
    if len(paths) < 2:
        continue

    cur.execute(
        """
        INSERT INTO duplicate_hashes
        (
            sha256,
            file_count,
            paths_json
        )
        VALUES (?, ?, ?)
        """,
        (
            sha,
            len(paths),
            json.dumps(paths, indent=2, sort_keys=True)
        )
    )

con.commit()

print("[OK] pass 10 duplicate hash graph built")
print("duplicate groups:", cur.execute("SELECT count(*) FROM duplicate_hashes").fetchone()[0])
print("duplicate files:", cur.execute("SELECT coalesce(sum(file_count),0) FROM duplicate_hashes").fetchone()[0])

con.close()
PY
