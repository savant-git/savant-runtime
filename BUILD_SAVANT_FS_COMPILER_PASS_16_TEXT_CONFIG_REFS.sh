#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import re
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS text_config_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id TEXT NOT NULL,
    reference_type TEXT NOT NULL,
    reference_value TEXT NOT NULL,
    resolved_path TEXT NOT NULL DEFAULT '',
    resolution_status TEXT NOT NULL DEFAULT 'unresolved',
    line_number INTEGER NOT NULL DEFAULT 0,
    line_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_text_config_source
ON text_config_references(source_file_id);

CREATE INDEX IF NOT EXISTS idx_text_config_status
ON text_config_references(resolution_status);
""")

cur.execute("DELETE FROM text_config_references")

TEXT_EXTS = {
    "json",
    "md",
    "txt",
    "yaml",
    "yml",
    "toml",
    "env",
    "service",
    "timer",
    "jsx",
    "js",
    "ts",
    "tsx",
    "css",
    "html",
    "sql",
}

patterns = [
    ("absolute_runtime_path", re.compile(r"/root/savant-runtime/[A-Za-z0-9_./:@{}$()\-]+")),
    ("ontology_relpath", re.compile(r"ontology/obelisks/[A-Za-z0-9_./:@{}$()\-]+")),
    ("relative_path", re.compile(r"(?:\./|\../)[A-Za-z0-9_./:@{}$()\-]+")),
]

rows = cur.execute(
    """
    SELECT id, path, extension
    FROM files
    WHERE ignored=0
      AND kind='file'
    ORDER BY path
    """
).fetchall()

def resolve(source: Path, ref: str):
    ref = ref.rstrip('",;)]}>\'')
    ref = ref.lstrip('(<"\'')

    if not ref:
        return "", "empty"

    if "$" in ref or "{" in ref or "(" in ref:
        return "", "dynamic"

    if ref.startswith("/root/savant-runtime/"):
        p = Path(ref)
        return (str(p), "resolved") if p.exists() else ("", "absolute_missing")

    if ref.startswith("ontology/"):
        p = ROOT / ref
        return (str(p), "resolved") if p.exists() else ("", "relative_missing")

    if ref.startswith("./") or ref.startswith("../"):
        p = (source.parent / ref).resolve()
        return (str(p), "resolved") if p.exists() else ("", "relative_missing")

    return "", "unresolved"

for file_id, path_text, extension in rows:
    path = Path(path_text)

    if extension not in TEXT_EXTS and "." in path.name:
        continue

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines()
    except Exception:
        continue

    for line_number, line in enumerate(lines, start=1):
        for ref_type, pattern in patterns:
            for match in pattern.findall(line):
                resolved, status = resolve(path, match)

                cur.execute(
                    """
                    INSERT INTO text_config_references
                    (
                        source_file_id,
                        reference_type,
                        reference_value,
                        resolved_path,
                        resolution_status,
                        line_number,
                        line_text
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        ref_type,
                        match,
                        resolved,
                        status,
                        line_number,
                        line[:500]
                    )
                )

con.commit()

print("[OK] pass 16 text/config reference graph built")
print("references:", cur.execute("SELECT count(*) FROM text_config_references").fetchone()[0])
print("resolved:", cur.execute("SELECT count(*) FROM text_config_references WHERE resolution_status='resolved'").fetchone()[0])
print("unresolved:", cur.execute("SELECT count(*) FROM text_config_references WHERE resolution_status!='resolved'").fetchone()[0])

con.close()
PY
