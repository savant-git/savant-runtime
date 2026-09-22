#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import sqlite3
from pathlib import Path

DB = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")

con = sqlite3.connect(DB)
cur = con.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS hard_safety_gate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gate_name TEXT NOT NULL,
    status TEXT NOT NULL,
    blocker_count INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

cur.execute("DELETE FROM hard_safety_gate")

checks = []

checks.append((
    "python_compile",
    """
    SELECT count(*)
    FROM compile_audit
    WHERE language='python'
      AND status!='ok'
    """,
    "All Python files must compile."
))

checks.append((
    "shell_compile",
    """
    SELECT count(*)
    FROM compile_audit
    WHERE language='shell'
      AND status!='ok'
    """,
    "All shell scripts must pass bash -n."
))

checks.append((
    "json_parse",
    """
    SELECT count(*)
    FROM compile_audit
    WHERE language='json'
      AND status!='ok'
    """,
    "All JSON files must parse."
))

checks.append((
    "broken_symlinks",
    """
    SELECT count(*)
    FROM symlinks
    WHERE target_exists=0
    """,
    "No broken symlinks allowed."
))

checks.append((
    "unresolved_python_imports",
    """
    SELECT count(*)
    FROM python_imports
    WHERE resolution_status NOT IN ('resolved', 'unresolved_external_or_missing')
    """,
    "No internal Python imports may be unresolved."
))

checks.append((
    "unresolved_shell_dependencies",
    """
    SELECT count(*)
    FROM shell_dependencies
    WHERE resolution_status NOT IN ('resolved', 'dynamic')
      AND target_text NOT IN ('-', '-m', 'install')
      AND dep_type NOT IN ('systemctl')
    """,
    "No relevant shell dependency may be unresolved."
))

checks.append((
    "unresolved_text_config_references",
    """
    SELECT count(*)
    FROM text_config_references
    WHERE resolution_status NOT IN ('resolved', 'dynamic')
      AND reference_value NOT LIKE '%${%'
      AND reference_value NOT LIKE '%$%'
    """,
    "No relevant text/config path reference may be unresolved."
))

checks.append((
    "blocked_move_candidates",
    """
    SELECT count(*)
    FROM move_candidates
    WHERE decision='BLOCK'
    """,
    "No blocked move candidates may remain before execution."
))

for name, query, message in checks:
    try:
        count = cur.execute(query).fetchone()[0]
    except Exception as e:
        count = 999999
        message = f"{message} Query failed: {e}"

    status = "PASS" if count == 0 else "BLOCK"

    cur.execute(
        """
        INSERT INTO hard_safety_gate
        (gate_name, status, blocker_count, message)
        VALUES (?, ?, ?, ?)
        """,
        (name, status, count, message)
    )

con.commit()

print("[OK] pass 18 hard safety gate complete")
print()

for name, status, count, message in cur.execute("""
    SELECT gate_name, status, blocker_count, message
    FROM hard_safety_gate
    ORDER BY gate_name
"""):
    print(f"{status} | {name} | {count} | {message}")

total = cur.execute("""
    SELECT count(*)
    FROM hard_safety_gate
    WHERE status!='PASS'
""").fetchone()[0]

print()
if total == 0:
    print("[READY] Hard safety gate passed.")
else:
    print("[NOT READY] Hard safety gate blocked.")

con.close()
PY
