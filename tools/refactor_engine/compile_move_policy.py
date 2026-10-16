#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"

NEVER_MOVE_PARTS = {
    "audit",
    "imports",
    "exports",
    "_reports",
    "repair_backups",
    "tools",
    "context",
    "canon",
    "authority_graph",
}

ROOT_SCRIPT_ALLOWLIST = {
    "DIAGNOSE_FS_COMPILER_EMPTY_DB.sh",
    "EXECUTE_SAFE_SCOPE_MOVES_DRY_RUN.sh",
    "FORCE_REBUILD_FS_COMPILER_DB_FULL.sh",
    "REBUILD_FS_COMPILER_DB_DIRECT.sh",
    "REBUILD_FS_COMPILER_DB_FULL.sh",
    "REPORT_FS_COMPILER_GRAPH_DB.sh",
}

def classify(path: Path, rel: str, basename: str, ext: str):
    parts = set(Path(rel).parts)

    if parts & NEVER_MOVE_PARTS:
        return "KEEP", "", "authority_audit_tooling_or_generated_context", 100

    if basename.startswith("."):
        return "KEEP", "", "hidden_or_editor_artifact", 100

    if ext not in {"sh"}:
        return "KEEP", "", "non_shell_moves_disabled_in_phase_05", 100

    if "/" not in rel and basename in ROOT_SCRIPT_ALLOWLIST:
        dst = ROOT / "ops/runtime/scripts" / basename
        return "CANDIDATE", str(dst), "root_runtime_ops_script", 90

    if "/" not in rel and basename.endswith(".sh"):
        dst = ROOT / "ops/uncategorized/scripts" / basename
        return "CANDIDATE", str(dst), "root_uncategorized_shell_script", 70

    return "KEEP", "", "already_scoped_or_not_phase_05", 100

def main() -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS move_policy_phase05 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT NOT NULL,
        source_path TEXT NOT NULL,
        proposed_target TEXT NOT NULL DEFAULT '',
        decision TEXT NOT NULL,
        reason TEXT NOT NULL,
        confidence INTEGER NOT NULL DEFAULT 0
    );
    """)

    cur.execute("DELETE FROM move_policy_phase05")

    rows = cur.execute("""
        SELECT id, path, relpath, basename, extension
        FROM files
        WHERE ignored=0
          AND kind='file'
        ORDER BY path
    """).fetchall()

    for file_id, path_text, rel, basename, ext in rows:
        decision, target, reason, confidence = classify(
            Path(path_text),
            rel,
            basename,
            ext,
        )

        cur.execute("""
            INSERT INTO move_policy_phase05
            (file_id, source_path, proposed_target, decision, reason, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (file_id, path_text, target, decision, reason, confidence))

    con.commit()

    print("[OK] phase 05 move policy compiled")
    for row in cur.execute("""
        SELECT decision, reason, count(*)
        FROM move_policy_phase05
        GROUP BY decision, reason
        ORDER BY decision, reason
    """):
        print(" | ".join(str(x) for x in row))

    con.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
