#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$ROOT/repair_backups/$STAMP"
REPORT_DIR="$ROOT/audit/foundation_phase_02"
REPORT="$REPORT_DIR/foundation_phase_02_report_$STAMP.md"

mkdir -p "$BACKUP" "$REPORT_DIR"

echo "======================================================="
echo "PHASE 02: BLOCKER REDUCTION + RECURSIVE FOUNDATION"
echo "======================================================="

echo
echo "=== 1. PATCH BLOCKER CLASSIFIER TO IGNORE GENERATED PREFIX DIRECTORIES ==="

if [ -f "$ROOT/PATCH_FAST_BLOCKER_CLASSIFIER.sh" ]; then
  cp "$ROOT/PATCH_FAST_BLOCKER_CLASSIFIER.sh" "$BACKUP/PATCH_FAST_BLOCKER_CLASSIFIER.sh.before"
fi

cat > "$ROOT/PATCH_FAST_BLOCKER_CLASSIFIER.sh" <<'SH'
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
SH

chmod +x "$ROOT/PATCH_FAST_BLOCKER_CLASSIFIER.sh"

echo
echo "=== 2. CREATE RUNTIME COMPATIBILITY PACKAGE FOR PALAVER SERVER IMPORTS ==="

PALAVER_APP="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/apps/webui_ultra"
PALAVER_RUNTIME="$PALAVER_APP/runtime"

mkdir -p "$PALAVER_RUNTIME"

cat > "$PALAVER_RUNTIME/__init__.py" <<'PY'
"""Compatibility runtime package for Palaver WebUI Ultra."""
PY

cat > "$PALAVER_RUNTIME/patch_review_workflow.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/root/savant-runtime")
STORE = ROOT / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/state/patch_review"
PENDING = STORE / "pending"
APPLIED = STORE / "applied"
REJECTED = STORE / "rejected"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    for p in [STORE, PENDING, APPLIED, REJECTED]:
        p.mkdir(parents=True, exist_ok=True)


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"id": path.stem, "error": "invalid_json", "detail": str(exc)}


def list_pending() -> list[dict[str, Any]]:
    _ensure()
    return [_read(p) for p in sorted(PENDING.glob("*.json"))]


def create(payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    _ensure()
    data: dict[str, Any] = {}
    if payload:
        data.update(payload)
    data.update(kwargs)
    data.setdefault("id", f"patch_{uuid.uuid4().hex}")
    data.setdefault("status", "pending")
    data.setdefault("created_at", _now())
    path = PENDING / f"{data['id']}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def apply_patch(patch_id: str, **kwargs: Any) -> dict[str, Any]:
    _ensure()
    src = PENDING / f"{patch_id}.json"
    if not src.exists():
        return {"id": patch_id, "status": "missing", "applied": False}
    data = _read(src)
    data.update(kwargs)
    data["status"] = "applied"
    data["applied"] = True
    data["applied_at"] = _now()
    dst = APPLIED / src.name
    dst.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    src.unlink()
    return data


def reject_patch(patch_id: str, reason: str = "", **kwargs: Any) -> dict[str, Any]:
    _ensure()
    src = PENDING / f"{patch_id}.json"
    if not src.exists():
        return {"id": patch_id, "status": "missing", "rejected": False}
    data = _read(src)
    data.update(kwargs)
    data["status"] = "rejected"
    data["rejected"] = True
    data["rejected_at"] = _now()
    data["reason"] = reason
    dst = REJECTED / src.name
    dst.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    src.unlink()
    return data
PY

python3 -m py_compile "$PALAVER_RUNTIME/patch_review_workflow.py"

echo
echo "=== 3. PATCH PYTHON IMPORT RESOLVER TO CONSIDER SOURCE FILE PARENT PACKAGE ROOT ==="

if [ -f "$ROOT/BUILD_SAVANT_FS_COMPILER_PASS_06_PY_IMPORTS.sh" ]; then
  cp "$ROOT/BUILD_SAVANT_FS_COMPILER_PASS_06_PY_IMPORTS.sh" "$BACKUP/BUILD_SAVANT_FS_COMPILER_PASS_06_PY_IMPORTS.sh.before"
fi

python3 - <<'PY'
from pathlib import Path

p = Path("/root/savant-runtime/BUILD_SAVANT_FS_COMPILER_PASS_06_PY_IMPORTS.sh")
text = p.read_text(encoding="utf-8", errors="replace")

old = """search_roots = [
        ROOT,
        source.parent,
    ]"""

new = """search_roots = [
        ROOT,
        source.parent,
        source.parent.parent,
        source.parent.parent.parent,
    ]"""

if old in text:
    text = text.replace(old, new)

p.write_text(text, encoding="utf-8")
PY

echo
echo "=== 4. PATCH DIRECT DB REBUILD IGNORE LIST ==="

if [ -f "$ROOT/REBUILD_FS_COMPILER_DB_DIRECT.sh" ]; then
  cp "$ROOT/REBUILD_FS_COMPILER_DB_DIRECT.sh" "$BACKUP/REBUILD_FS_COMPILER_DB_DIRECT.sh.before"
fi

python3 - <<'PY'
from pathlib import Path

p = Path("/root/savant-runtime/REBUILD_FS_COMPILER_DB_DIRECT.sh")
text = p.read_text(encoding="utf-8", errors="replace")

for name in ["repair_backups", "exports"]:
    marker = f'"{name}",'
    if marker not in text:
        text = text.replace(
            '"site-packages",',
            f'"site-packages",\n    "{name}",'
        )

p.write_text(text, encoding="utf-8")
PY

echo
echo "=== 5. INSTALL RECURSIVE FOUNDATION STATUS PROJECTOR ==="

mkdir -p "$ROOT/tools/foundation" "$ROOT/context"

cat > "$ROOT/tools/foundation/project_foundation_status.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/root/savant-runtime")
OUT = ROOT / "context/FOUNDATION_STATUS.json"

REQUIRED = {
    "canon_foundation": ROOT / "canon/foundation",
    "authority_graph": ROOT / "authority_graph",
    "meta_archetypes": ROOT / "authority_graph/meta_archetypes",
    "archetypes": ROOT / "authority_graph/archetypes",
    "templates": ROOT / "authority_graph/templates",
    "instances": ROOT / "authority_graph/instances",
    "segues": ROOT / "authority_graph/segues",
    "policies": ROOT / "authority_graph/policies",
    "projections": ROOT / "authority_graph/projections",
}

status = {
    "id": "projection:foundation_status",
    "kind": "projection",
    "authority": "canon/foundation + authority_graph",
    "complete": True,
    "checks": {},
}

for key, path in REQUIRED.items():
    exists = path.exists()
    status["checks"][key] = {"path": str(path), "exists": exists}
    if not exists:
        status["complete"] = False

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(OUT)
PY

chmod +x "$ROOT/tools/foundation/project_foundation_status.py"
python3 "$ROOT/tools/foundation/project_foundation_status.py"

echo
echo "=== 6. REFRESH FAST AUDIT ==="

./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh
./REPORT_ACTIONABLE_BLOCKERS.sh

echo
echo "=== 7. BUILD PHASE REPORT ==="

python3 - <<'PY' > "$REPORT"
import json
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
con = sqlite3.connect(DB)
cur = con.cursor()

print("# Foundation Phase 02 Report")
print()
print("No filesystem moves were executed.")
print()

print("## Blocker Classification")
print()
for severity, cls, count in cur.execute("""
    SELECT severity, class, count(*)
    FROM blocker_classification
    GROUP BY severity, class
    ORDER BY severity, class
"""):
    print(f"- {severity} | {cls} | {count}")

print()
print("## Actionable Error Count")
print()
errors = cur.execute("""
    SELECT count(*)
    FROM blocker_classification
    WHERE severity='error'
""").fetchone()[0]
print(errors)

print()
print("## Foundation Status")
print()
status_path = ROOT / "context/FOUNDATION_STATUS.json"
if status_path.exists():
    status = json.loads(status_path.read_text())
    print(json.dumps(status, indent=2, sort_keys=True))
else:
    print("missing")

con.close()
PY

cat "$REPORT"

echo
echo "[OK] phase 02 complete"
echo "report: $REPORT"
echo "backup: $BACKUP"
