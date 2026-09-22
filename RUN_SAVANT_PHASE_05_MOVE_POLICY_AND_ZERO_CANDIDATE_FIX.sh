#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT/audit/foundation_phase_05"
REPORT="$REPORT_DIR/phase_05_move_policy_$STAMP.md"
BACKUP="$ROOT/repair_backups/$STAMP"

mkdir -p "$REPORT_DIR" "$BACKUP"

echo "======================================================="
echo "PHASE 05: MOVE POLICY + ZERO-CANDIDATE FIX"
echo "======================================================="

echo
echo "=== 1. INSTALL CONSERVATIVE MOVE POLICY COMPILER ==="

cat > "$ROOT/tools/refactor_engine/compile_move_policy.py" <<'PY'
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
PY

chmod +x "$ROOT/tools/refactor_engine/compile_move_policy.py"

echo
echo "=== 2. INSTALL PHASE 05 SIMULATOR ==="

cat > "$ROOT/tools/refactor_engine/simulate_phase05_moves.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
OUT = ROOT / "context/PHASE05_MOVE_SIMULATION.json"

IGNORE = {
    ".git",
    ".venv",
    ".venv_voice",
    "node_modules",
    "__pycache__",
    "site-packages",
    "exports",
    "repair_backups",
}

def ignore_copy(dirpath, names):
    return [n for n in names if n in IGNORE]

def ignored(path: Path) -> bool:
    return any(part in IGNORE for part in path.parts)

def moves():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    rows = cur.execute("""
        SELECT file_id, source_path, proposed_target, reason, confidence
        FROM move_policy_phase05
        WHERE decision='CANDIDATE'
        ORDER BY source_path
    """).fetchall()
    con.close()
    return [
        {
            "file_id": r[0],
            "source": r[1],
            "target": r[2],
            "reason": r[3],
            "confidence": r[4],
        }
        for r in rows
    ]

def references_to_path(source: str) -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    count = 0

    for table, col in [
        ("shell_dependencies", "resolved_path"),
        ("canonical_path_claims", "claimed_path"),
        ("text_config_references", "resolved_path"),
    ]:
        try:
            count += cur.execute(
                f"SELECT count(*) FROM {table} WHERE {col}=?",
                (source,),
            ).fetchone()[0]
        except Exception:
            pass

    con.close()
    return count

def validate(work: Path) -> list[dict]:
    failures = []

    for path in sorted(work.rglob("*.sh")):
        if ignored(path):
            continue
        proc = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
        if proc.returncode != 0:
            failures.append({
                "kind": "shell",
                "path": str(path.relative_to(work)),
                "error": proc.stderr.strip(),
            })

    for path in sorted(work.rglob("*.py")):
        if ignored(path):
            continue
        proc = subprocess.run(["python3", "-m", "py_compile", str(path)], text=True, capture_output=True)
        if proc.returncode != 0:
            failures.append({
                "kind": "python",
                "path": str(path.relative_to(work)),
                "error": proc.stderr.strip(),
            })

    return failures

def main() -> int:
    candidate_moves = moves()

    blocked = []
    executable = []

    for move in candidate_moves:
        refs = references_to_path(move["source"])
        move["reference_count"] = refs
        if refs > 0:
            move["blocked_reason"] = "source_has_known_references"
            blocked.append(move)
        elif Path(move["target"]).exists():
            move["blocked_reason"] = "target_exists"
            blocked.append(move)
        else:
            executable.append(move)

    with tempfile.TemporaryDirectory(prefix="savant_phase05_sim_") as td:
        work = Path(td) / "savant-runtime"
        shutil.copytree(ROOT, work, ignore=ignore_copy, symlinks=True)

        move_results = []

        for move in executable:
            src = work / Path(move["source"]).relative_to(ROOT)
            dst = work / Path(move["target"]).relative_to(ROOT)

            row = {
                "source": str(src.relative_to(work)),
                "target": str(dst.relative_to(work)),
                "status": "pending",
            }

            if not src.exists():
                row["status"] = "fail"
                row["reason"] = "source_missing"
            elif dst.exists():
                row["status"] = "fail"
                row["reason"] = "target_exists"
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                row["status"] = "moved"

            move_results.append(row)

        failures = validate(work)

    failed_moves = [x for x in move_results if x["status"] != "moved"]

    status = "PASS" if not blocked and not failed_moves and not failures else "BLOCK"

    report = {
        "id": "phase05_move_simulation",
        "status": status,
        "candidate_count": len(candidate_moves),
        "executable_count": len(executable),
        "blocked_count": len(blocked),
        "failed_move_count": len(failed_moves),
        "validation_failure_count": len(failures),
        "candidates": candidate_moves,
        "executable": executable,
        "blocked": blocked,
        "move_results": move_results,
        "failed_moves": failed_moves,
        "validation_failures": failures,
        "live_files_changed": False,
        "move_safe": False,
    }

    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/tools/refactor_engine/simulate_phase05_moves.py"

echo
echo "=== 3. REFRESH AUDIT + COMPILE POLICY + SIMULATE ==="

./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh
python3 "$ROOT/tools/refactor_engine/compile_move_policy.py"

set +e
python3 "$ROOT/tools/refactor_engine/simulate_phase05_moves.py" | tee "$REPORT"
STATUS="${PIPESTATUS[0]}"
set -e

echo
echo "[OK] report:"
echo "$REPORT"
echo "/root/savant-runtime/context/PHASE05_MOVE_SIMULATION.json"

if [ "$STATUS" -ne 0 ]; then
  echo
  echo "[BLOCKED] Phase 05 did not prove move safety."
  exit 0
fi

echo
echo "[PASS] Phase 05 simulation passed. No live files moved."
