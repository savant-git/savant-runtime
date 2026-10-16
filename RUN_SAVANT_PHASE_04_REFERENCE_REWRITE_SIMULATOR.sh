#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT/audit/foundation_phase_04"
REPORT="$REPORT_DIR/phase_04_reference_rewrite_simulation_$STAMP.md"

mkdir -p "$REPORT_DIR" "$ROOT/tools/refactor_engine"

cat > "$ROOT/tools/refactor_engine/full_reference_rewrite_simulator.py" <<'PY'
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
OUT = ROOT / "context/FULL_REFERENCE_REWRITE_SIMULATION.json"

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

TEXT_SUFFIXES = {
    ".py", ".sh", ".json", ".md", ".txt", ".yaml", ".yml",
    ".toml", ".service", ".timer", ".js", ".jsx", ".ts", ".tsx",
    ".css", ".html"
}


def ignore_copy(dirpath, names):
    return [n for n in names if n in IGNORE]


def ignored(path: Path) -> bool:
    return any(part in IGNORE for part in path.parts)


def load_candidate_moves() -> list[dict]:
    if not DB.exists():
        return []

    con = sqlite3.connect(DB)
    cur = con.cursor()

    rows = []

    try:
        rows = cur.execute("""
            SELECT
                f.path,
                f.relpath,
                m.proposed_target,
                m.decision,
                m.reason,
                m.reference_count
            FROM move_candidates m
            JOIN files f ON f.id=m.file_id
            WHERE m.decision='CANDIDATE'
            ORDER BY f.path
        """).fetchall()
    except Exception:
        rows = []

    con.close()

    return [
        {
            "source": r[0],
            "source_rel": r[1],
            "target": r[2],
            "decision": r[3],
            "reason": r[4],
            "reference_count": r[5],
        }
        for r in rows
    ]


def text_files(root: Path) -> list[Path]:
    rows = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ignored(path):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name.endswith((".service", ".timer")):
            rows.append(path)
    return sorted(rows)


def build_replacements(moves: list[dict]) -> list[tuple[str, str]]:
    reps = []

    for move in moves:
        src = Path(move["source"])
        dst = Path(move["target"])

        reps.append((str(src), str(dst)))
        reps.append((str(src.relative_to(ROOT)), str(dst.relative_to(ROOT))))

    dedup = []
    seen = set()

    for old, new in reps:
        if old == new:
            continue
        key = (old, new)
        if key in seen:
            continue
        seen.add(key)
        dedup.append((old, new))

    return dedup


def apply_rewrites(work: Path, replacements: list[tuple[str, str]]) -> list[dict]:
    affected = []

    for path in text_files(work):
        text = path.read_text(encoding="utf-8", errors="replace")
        original = text
        changes = []

        for old, new in replacements:
            if old in text:
                count = text.count(old)
                text = text.replace(old, new)
                changes.append({"old": old, "new": new, "count": count})

        if text != original:
            path.write_text(text, encoding="utf-8")
            affected.append({
                "path": str(path.relative_to(work)),
                "changes": changes,
            })

    return affected


def apply_moves(work: Path, moves: list[dict]) -> list[dict]:
    results = []

    for move in moves:
        src = work / move["source_rel"]
        dst = work / Path(move["target"]).relative_to(ROOT)

        row = {
            "source": str(src.relative_to(work)),
            "target": str(dst.relative_to(work)),
            "status": "pending",
            "reason": "",
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

        results.append(row)

    return results


def validate(work: Path) -> list[dict]:
    failures = []

    for path in sorted(work.rglob("*.py")):
        if ignored(path):
            continue
        proc = subprocess.run(
            ["python3", "-m", "py_compile", str(path)],
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            failures.append({
                "kind": "python",
                "path": str(path.relative_to(work)),
                "error": proc.stderr.strip(),
            })

    for path in sorted(work.rglob("*.sh")):
        if ignored(path):
            continue
        proc = subprocess.run(
            ["bash", "-n", str(path)],
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            failures.append({
                "kind": "shell",
                "path": str(path.relative_to(work)),
                "error": proc.stderr.strip(),
            })

    for path in sorted(work.rglob("*.json")):
        if ignored(path):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            failures.append({
                "kind": "json",
                "path": str(path.relative_to(work)),
                "error": str(exc),
            })

    return failures


def main() -> int:
    moves = load_candidate_moves()
    replacements = build_replacements(moves)

    with tempfile.TemporaryDirectory(prefix="savant_full_rewrite_sim_") as td:
        work = Path(td) / "savant-runtime"
        shutil.copytree(ROOT, work, ignore=ignore_copy, symlinks=True)

        affected = apply_rewrites(work, replacements)
        move_results = apply_moves(work, moves)
        failures = validate(work)

    failed_moves = [m for m in move_results if m["status"] != "moved"]

    status = "PASS" if not failures and not failed_moves else "BLOCK"

    report = {
        "id": "full_reference_rewrite_simulation",
        "status": status,
        "move_count": len(moves),
        "rewrite_count": len(affected),
        "failed_move_count": len(failed_moves),
        "validation_failure_count": len(failures),
        "moves": moves,
        "affected_files": affected,
        "move_results": move_results,
        "failed_moves": failed_moves,
        "validation_failures": failures,
        "live_files_changed": False,
        "move_safe": False,
        "move_safe_reason": "Even when this passes, live execution requires explicit separate executor and current report review.",
    }

    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/tools/refactor_engine/full_reference_rewrite_simulator.py"

echo "=== FAST REFRESH ==="
./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh

echo "=== MOVE CANDIDATES ==="
if [ -x ./BUILD_SAVANT_FS_COMPILER_PASS_12_MOVE_CANDIDATES.sh ]; then
  ./BUILD_SAVANT_FS_COMPILER_PASS_12_MOVE_CANDIDATES.sh
fi

echo "=== FULL REFERENCE REWRITE SIMULATION ==="
set +e
python3 "$ROOT/tools/refactor_engine/full_reference_rewrite_simulator.py" | tee "$REPORT"
STATUS="${PIPESTATUS[0]}"
set -e

echo
echo "[OK] phase 04 report:"
echo "$REPORT"
echo "/root/savant-runtime/context/FULL_REFERENCE_REWRITE_SIMULATION.json"

if [ "$STATUS" -ne 0 ]; then
  echo
  echo "[BLOCKED] Not move-safe."
  exit 0
fi

echo
echo "[PASS] Simulation passed. No live files moved."
