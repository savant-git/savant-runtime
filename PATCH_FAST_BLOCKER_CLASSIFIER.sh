#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

DB="/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite"

python3 - <<'PY'
import sqlite3
from pathlib import Path

db = Path("/root/savant-runtime/audit/fs_compiler/db/savant_fs_compiler.sqlite")
con = sqlite3.connect(db)
cur = con.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS blocker_classification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_table TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    severity TEXT NOT NULL,
    class TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

cur.execute("DELETE FROM blocker_classification")

SYSTEM_PREFIXES = (
    "/root/savant-runtime/imports/source-dumps/analysis_",
    "/root/savant-runtime/imports/source-dumps/parsed_any_",
    "/root/savant-runtime/imports/source-dumps/parsed_",
    "/root/savant-runtime/imports/source-dumps/parsed_clean_",
    "/root/savant-runtime/current_runtime_source_dump_",
    "/root/savant-runtime/audit/fs_compiler/execution_plan_",
    "/root/savant-runtime/audit/scope_tree/moveable_files_clear_list_",
)

SHELL_NOISE = {"-", "-m", "install", "./-", "../-", "./g", "./Filament"}

for row in cur.execute("""
    SELECT id, module, symbol, resolution_status
    FROM python_imports
    WHERE resolution_status != 'resolved'
""").fetchall():
    pid, module, symbol, status = row

    severity = "warning"
    cls = "external_or_optional"
    reason = "Likely external package, stdlib, optional provider, or dynamically resolved import."

    if module.startswith(("app.", "runtime.", "ontology.", "authority_graph.", "tools.")):
        severity = "error"
        cls = "internal_unresolved"
        reason = "Internal import failed to resolve."

    cur.execute(
        """
        INSERT INTO blocker_classification
        (source_table, source_id, severity, class, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("python_imports", pid, severity, cls, reason)
    )

for row in cur.execute("""
    SELECT id, dep_type, command, target_text, resolution_status
    FROM shell_dependencies
    WHERE resolution_status NOT IN ('resolved','dynamic')
""").fetchall():
    sid, dep_type, command, target, status = row

    severity = "warning"
    cls = "shell_noise_or_service_reference"
    reason = "Shell reference appears to be command syntax, service command, generated path prefix, or non-file shell argument."

    if dep_type == "systemctl":
        severity = "info"
        cls = "systemctl_command"
        reason = "Systemd command reference, not direct file dependency."

    elif target in SHELL_NOISE:
        severity = "info"
        cls = "non_file_argument"
        reason = "Not a file dependency."

    elif any(target.startswith(prefix) for prefix in SYSTEM_PREFIXES):
        severity = "info"
        cls = "generated_prefix"
        reason = "Generated prefix path. Directory prefix is intentionally dynamic."

    elif target.startswith("/root/savant-runtime/"):
        severity = "error"
        cls = "missing_runtime_path"
        reason = "Absolute runtime path does not exist."

    elif target.startswith("./") or target.startswith("../"):
        severity = "error"
        cls = "missing_relative_path"
        reason = "Relative path does not resolve."

    cur.execute(
        """
        INSERT INTO blocker_classification
        (source_table, source_id, severity, class, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("shell_dependencies", sid, severity, cls, reason)
    )

con.commit()

print("[OK] blocker classifications built")

for row in cur.execute("""
    SELECT severity, class, count(*)
    FROM blocker_classification
    GROUP BY severity, class
    ORDER BY severity, class
"""):
    print(" | ".join(str(x) for x in row))

con.close()
PY
