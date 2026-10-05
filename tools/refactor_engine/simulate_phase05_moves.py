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
