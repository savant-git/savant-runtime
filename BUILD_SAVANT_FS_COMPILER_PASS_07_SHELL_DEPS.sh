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
import shlex
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("DELETE FROM shell_dependencies")

rows = cur.execute(
    """
    SELECT id, path, relpath, extension
    FROM files
    WHERE ignored = 0
      AND kind = 'file'
      AND (
        extension = 'sh'
        OR basename = 'run.sh'
        OR basename LIKE '%.service'
        OR basename LIKE '%.timer'
      )
    ORDER BY path
    """
).fetchall()


def resolve_path(source: Path, target: str) -> tuple[str, str]:
    target = target.strip().strip('"').strip("'")

    if not target:
        return "", "empty"

    if target.startswith("$") or "${" in target or "$(" in target:
        return "", "dynamic"

    candidate = Path(target)

    if candidate.is_absolute():
        if candidate.exists():
            return str(candidate), "resolved"
        return "", "absolute_missing"

    local = source.parent / candidate

    if local.exists():
        return str(local.resolve()), "resolved"

    root_relative = ROOT / candidate

    if root_relative.exists():
        return str(root_relative.resolve()), "resolved"

    return "", "unresolved"


def extract_shell_deps(path: Path):
    deps = []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return deps

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        try:
            parts = shlex.split(stripped, comments=True, posix=True)
        except Exception:
            parts = stripped.split()

        if not parts:
            continue

        cmd = parts[0]

        if cmd in {"source", "."} and len(parts) >= 2:
            deps.append(("source", cmd, parts[1], idx))

        elif cmd in {"bash", "sh", "python", "python3", "node", "npm"} and len(parts) >= 2:
            deps.append(("exec", cmd, parts[1], idx))

        elif cmd == "exec" and len(parts) >= 2:
            deps.append(("exec", cmd, parts[1], idx))

        elif cmd == "systemctl":
            deps.append(("systemctl", cmd, " ".join(parts[1:]), idx))

        for match in re.findall(r"/root/savant-runtime/[A-Za-z0-9_./-]+", stripped):
            deps.append(("absolute_path", "path", match, idx))

        for match in re.findall(r"(?:\./|\../)[A-Za-z0-9_./-]+", stripped):
            deps.append(("relative_path", "path", match, idx))

    return deps


for file_id, path_text, relpath, ext in rows:
    path = Path(path_text)

    for dep_type, command, target_text, line_number in extract_shell_deps(path):
        resolved, status = resolve_path(path, target_text)

        cur.execute(
            """
            INSERT INTO shell_dependencies
            (
                source_file_id,
                dep_type,
                command,
                target_text,
                resolved_path,
                resolution_status,
                line_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                dep_type,
                command,
                target_text,
                resolved,
                status,
                line_number,
            ),
        )

con.commit()

print("[OK] pass 07 shell dependency graph built")
print("shell/service files:", len(rows))
print("dependencies:", cur.execute("SELECT count(*) FROM shell_dependencies").fetchone()[0])
print("resolved:", cur.execute("SELECT count(*) FROM shell_dependencies WHERE resolution_status='resolved'").fetchone()[0])
print("unresolved:", cur.execute("SELECT count(*) FROM shell_dependencies WHERE resolution_status!='resolved'").fetchone()[0])

con.close()
PY
