#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
DB="$AUDIT/db/savant_fs_compiler.sqlite"

PASS01="$(
  find "$AUDIT" -type f -name 'pass01_inventory_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

PASS02="$(
  find "$AUDIT" -type f -name 'pass02_semantic_classification_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

PASS03="$(
  find "$AUDIT" -type f -name 'pass03_reference_graph_*.tsv' 2>/dev/null |
  sort |
  tail -1
)"

if [ ! -f "$DB" ]; then
  echo "[ERROR] Missing graph DB. Run BUILD_SAVANT_FS_COMPILER_GRAPH_DB.sh first."
  exit 1
fi

if [ -z "$PASS01" ] || [ -z "$PASS02" ]; then
  echo "[ERROR] Missing pass01 or pass02 TSV."
  exit 1
fi

python3 - <<'PY'
import csv
import sqlite3
from pathlib import Path

root = Path("/root/savant-runtime")
audit = root / "audit/fs_compiler"
db = audit / "db/savant_fs_compiler.sqlite"

pass01 = sorted(audit.glob("pass01_inventory_*.tsv"))[-1]
pass02 = sorted(audit.glob("pass02_semantic_classification_*.tsv"))[-1]
pass03s = sorted(audit.glob("pass03_reference_graph_*.tsv"))
pass03 = pass03s[-1] if pass03s else None

con = sqlite3.connect(db)
cur = con.cursor()

cur.execute("DELETE FROM files")
cur.execute("DELETE FROM classifications")
cur.execute("DELETE FROM references_found")

with pass01.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        cur.execute(
            """
            INSERT OR REPLACE INTO files
            (id, path, relpath, basename, kind, extension, size_bytes, modified_utc, sha256, ignored)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["path"],
                row["relpath"],
                row["basename"],
                row["kind"],
                row["extension"],
                int(row["size_bytes"] or 0),
                row["modified_utc"],
                row["sha256"],
                1 if row["ignored"] == "yes" else 0,
            ),
        )

with pass02.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        cur.execute(
            """
            INSERT OR REPLACE INTO classifications
            (file_id, owner, scope, containment, edifice_level, authority_class, move_policy, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["owner"],
                row["scope"],
                row["containment"],
                row["edifice_level"],
                row["authority_class"],
                row["move_policy"],
                0,
            ),
        )

if pass03 and pass03.exists():
    with pass03.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        path_to_id = {
            path: file_id
            for file_id, path in cur.execute("SELECT id, path FROM files").fetchall()
        }

        for row in reader:
            sid = path_to_id.get(row["source_path"])
            if not sid:
                continue

            cur.execute(
                """
                INSERT INTO references_found
                (source_file_id, reference_type, reference_value, target_guess, line_number, line_text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    row["reference_type"],
                    row["reference_value"],
                    row.get("target_guess", ""),
                    int(row["line_number"] or 0),
                    row["line_text"],
                ),
            )

con.commit()

print("[OK] ingested compiler passes into graph DB")
print("files:", cur.execute("SELECT count(*) FROM files").fetchone()[0])
print("classifications:", cur.execute("SELECT count(*) FROM classifications").fetchone()[0])
print("references:", cur.execute("SELECT count(*) FROM references_found").fetchone()[0])

con.close()
PY
