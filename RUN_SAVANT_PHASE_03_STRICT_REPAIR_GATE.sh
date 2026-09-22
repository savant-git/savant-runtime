#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$ROOT/repair_backups/$STAMP"
REPORT_DIR="$ROOT/audit/foundation_phase_03"
REPORT="$REPORT_DIR/phase_03_strict_repair_gate_$STAMP.md"

mkdir -p "$BACKUP" "$REPORT_DIR" "$ROOT/tools/foundation"

echo "======================================================="
echo "PHASE 03: STRICT REPAIR GATE"
echo "======================================================="

cat > "$ROOT/tools/foundation/strict_repair_gate.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
OUT = ROOT / "context/STRICT_REPAIR_GATE.json"

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

def ignored(path: Path) -> bool:
    return any(part in IGNORE for part in path.parts)

def compile_checks() -> list[dict]:
    failures = []

    for path in sorted(ROOT.rglob("*.py")):
        if ignored(path):
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append({
                "kind": "python",
                "path": str(path.relative_to(ROOT)),
                "error": str(exc),
            })

    for path in sorted(ROOT.rglob("*.sh")):
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
                "path": str(path.relative_to(ROOT)),
                "error": proc.stderr.strip(),
            })

    for path in sorted(ROOT.rglob("*.json")):
        if ignored(path):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            failures.append({
                "kind": "json",
                "path": str(path.relative_to(ROOT)),
                "error": str(exc),
            })

    return failures

def db_blockers() -> dict:
    result = {
        "available": DB.exists(),
        "actionable_errors": None,
        "broken_symlinks": None,
        "internal_unresolved_imports": None,
    }

    if not DB.exists():
        return result

    con = sqlite3.connect(DB)
    cur = con.cursor()

    try:
        result["actionable_errors"] = cur.execute("""
            SELECT count(*)
            FROM blocker_classification
            WHERE severity='error'
        """).fetchone()[0]
    except Exception:
        result["actionable_errors"] = None

    try:
        result["broken_symlinks"] = cur.execute("""
            SELECT count(*)
            FROM symlinks
            WHERE target_exists=0
        """).fetchone()[0]
    except Exception:
        result["broken_symlinks"] = None

    try:
        result["internal_unresolved_imports"] = cur.execute("""
            SELECT count(*)
            FROM blocker_classification
            WHERE severity='error'
              AND class='internal_unresolved'
        """).fetchone()[0]
    except Exception:
        result["internal_unresolved_imports"] = None

    con.close()
    return result

def foundation_checks() -> list[dict]:
    required = [
        "canon/foundation/000_META_REALITY_CANON.md",
        "canon/foundation/001_META_ARCHETYPE_CANON.md",
        "canon/foundation/002_ARCHETYPE_CANON.md",
        "canon/foundation/003_TEMPLATE_CANON.md",
        "canon/foundation/004_INSTANCE_CANON.md",
        "canon/foundation/005_SEGUE_CANON.md",
        "canon/foundation/006_AUTHORITY_GRAPH_CANON.md",
        "canon/foundation/007_PROJECTION_CANON.md",
        "authority_graph/meta_archetypes/universal_object.json",
        "authority_graph/archetypes/universal_instance.json",
        "authority_graph/templates/base_instance.json",
        "authority_graph/policies/emergence.json",
        "authority_graph/policies/projection.json",
        "context/FOUNDATION_STATUS.json",
    ]

    rows = []
    for rel in required:
        path = ROOT / rel
        rows.append({
            "path": rel,
            "exists": path.exists(),
        })
    return rows

def main() -> int:
    compile_failures = compile_checks()
    db = db_blockers()
    foundation = foundation_checks()

    missing_foundation = [x for x in foundation if not x["exists"]]

    blockers = []
    blockers.extend(compile_failures)

    if db["actionable_errors"] not in (0, None):
        blockers.append({
            "kind": "db",
            "path": "blocker_classification",
            "error": f"actionable_errors={db['actionable_errors']}",
        })

    if db["broken_symlinks"] not in (0, None):
        blockers.append({
            "kind": "db",
            "path": "symlinks",
            "error": f"broken_symlinks={db['broken_symlinks']}",
        })

    for item in missing_foundation:
        blockers.append({
            "kind": "foundation",
            "path": item["path"],
            "error": "missing required foundation path",
        })

    report = {
        "id": "strict_repair_gate",
        "status": "PASS" if not blockers else "BLOCK",
        "compile_failures": compile_failures,
        "db": db,
        "foundation": foundation,
        "blockers": blockers,
        "move_safe": False,
        "move_safe_reason": "Filesystem moves remain blocked until strict repair gate and full rewrite simulation both pass.",
    }

    if not blockers:
        report["next_phase"] = "build_full_reference_rewrite_simulator"

    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not blockers else 1

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/tools/foundation/strict_repair_gate.py"

echo
echo "=== REFRESH FAST AUDIT ==="
./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh

echo
echo "=== RUN STRICT GATE ==="
set +e
python3 "$ROOT/tools/foundation/strict_repair_gate.py" | tee "$REPORT"
STATUS="${PIPESTATUS[0]}"
set -e

echo
echo "[OK] strict gate report:"
echo "$REPORT"

if [ "$STATUS" -ne 0 ]; then
  echo
  echo "[BLOCKED] Still not move-safe."
  exit 0
fi

echo
echo "[PASS] Strict repair gate passed. Still no files moved."
