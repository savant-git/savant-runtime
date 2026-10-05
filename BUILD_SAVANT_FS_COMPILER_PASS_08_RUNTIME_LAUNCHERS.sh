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

cur.execute("DELETE FROM service_references")

files = cur.execute(
    """
    SELECT id, path, relpath, basename, extension
    FROM files
    WHERE ignored=0
      AND kind='file'
    ORDER BY path
    """
).fetchall()


def resolve_exec(text: str):
    for match in re.findall(r"/root/savant-runtime/[A-Za-z0-9_./-]+", text):
        p = Path(match)
        if p.exists():
            return str(p), "resolved"

    return "", "unresolved"


for file_id, path_text, relpath, basename, ext in files:
    path = Path(path_text)

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    service_type = ""

    if basename.endswith(".service"):
        service_type = "systemd_service"
    elif basename.endswith(".timer"):
        service_type = "systemd_timer"
    elif "systemctl" in text:
        service_type = "systemctl_script"
    elif "crontab" in text or "cron" in text:
        service_type = "cron_reference"

    if not service_type:
        continue

    exec_lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if (
            stripped.startswith("ExecStart=")
            or stripped.startswith("ExecReload=")
            or stripped.startswith("ExecStop=")
            or "systemctl" in stripped
            or "crontab" in stripped
            or "cron" in stripped
        ):
            exec_lines.append(stripped)

    if not exec_lines:
        exec_lines = [""]

    for exec_text in exec_lines:
        resolved, status = resolve_exec(exec_text)

        cur.execute(
            """
            INSERT INTO service_references
            (
                source_file_id,
                service_type,
                name,
                exec_text,
                resolved_path,
                resolution_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                service_type,
                basename,
                exec_text,
                resolved,
                status,
            ),
        )

con.commit()

print("[OK] pass 08 runtime launcher graph built")
print("service refs:", cur.execute("SELECT count(*) FROM service_references").fetchone()[0])
print("resolved:", cur.execute("SELECT count(*) FROM service_references WHERE resolution_status='resolved'").fetchone()[0])
print("unresolved:", cur.execute("SELECT count(*) FROM service_references WHERE resolution_status!='resolved'").fetchone()[0])

con.close()
PY
