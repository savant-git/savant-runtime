#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
AUDIT="$ROOT/audit/fs_compiler"
DB="$AUDIT/db/savant_fs_compiler.sqlite"

if [ ! -f "$DB" ]; then
  echo "[ERROR] Missing graph DB."
  echo "Run BUILD_SAVANT_FS_COMPILER_GRAPH_DB.sh first."
  exit 1
fi

python3 - <<'PY'
import ast
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("DELETE FROM python_imports")

rows = cur.execute(
    """
    SELECT id, path, relpath
    FROM files
    WHERE ignored = 0
      AND kind = 'file'
      AND extension = 'py'
    ORDER BY path
    """
).fetchall()


def resolve_module(source: Path, module: str, level: int) -> tuple[str, str]:
    if level > 0:
        base = source.parent
        for _ in range(level - 1):
            base = base.parent

        if module:
            candidate = base / Path(module.replace(".", "/"))
        else:
            candidate = base

        for target in [
            candidate.with_suffix(".py"),
            candidate / "__init__.py",
        ]:
            if target.exists():
                return str(target), "resolved"

        return "", "unresolved_relative"

    if not module:
        return "", "unresolved_empty"

    parts = Path(module.replace(".", "/"))

    search_roots = [
        ROOT,
        source.parent,
        source.parent.parent,
        source.parent.parent.parent,
    ]

    for root in search_roots:
        candidate = root / parts

        for target in [
            candidate.with_suffix(".py"),
            candidate / "__init__.py",
        ]:
            if target.exists():
                return str(target), "resolved"

    return "", "unresolved_external_or_missing"


for file_id, path_text, relpath in rows:
    path = Path(path_text)

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:
        cur.execute(
            """
            INSERT INTO validation_results
            (validation_id, severity, check_name, file_id, path, message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "pass06_python_ast",
                "warning",
                "python_parse_failed",
                file_id,
                str(path),
                str(exc),
            ),
        )
        continue

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved, status = resolve_module(path, alias.name, 0)

                cur.execute(
                    """
                    INSERT INTO python_imports
                    (source_file_id, import_type, module, symbol, level, resolved_path, resolution_status, line_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        "import",
                        alias.name,
                        alias.asname or "",
                        0,
                        resolved,
                        status,
                        getattr(node, "lineno", 0),
                    ),
                )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            resolved, status = resolve_module(path, module, level)

            for alias in node.names:
                cur.execute(
                    """
                    INSERT INTO python_imports
                    (source_file_id, import_type, module, symbol, level, resolved_path, resolution_status, line_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        "from",
                        module,
                        alias.name,
                        level,
                        resolved,
                        status,
                        getattr(node, "lineno", 0),
                    ),
                )

con.commit()

print("[OK] pass 06 Python import graph built")
print("python files:", len(rows))
print("imports:", cur.execute("SELECT count(*) FROM python_imports").fetchone()[0])
print("unresolved:", cur.execute("SELECT count(*) FROM python_imports WHERE resolution_status != 'resolved'").fetchone()[0])

con.close()
PY
