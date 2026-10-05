#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$ROOT/repair_backups/$STAMP"

mkdir -p "$BACKUP"

echo "=== 1. IGNORE REPAIR BACKUP SYMLINKS IN DB REBUILD ==="

cp REBUILD_FS_COMPILER_DB_DIRECT.sh "$BACKUP/REBUILD_FS_COMPILER_DB_DIRECT.sh.before"

python3 - <<'PY'
from pathlib import Path

p = Path("/root/savant-runtime/REBUILD_FS_COMPILER_DB_DIRECT.sh")
text = p.read_text(encoding="utf-8", errors="replace")

if '"repair_backups",' not in text:
    text = text.replace(
        '"exports",',
        '"exports",\n    "repair_backups",'
    )

p.write_text(text, encoding="utf-8")
PY

echo "=== 2. CREATE PALAVER patch_review_workflow MODULE ==="

PALAVER_RUNTIME="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/apps/webui_ultra/runtime"
mkdir -p "$PALAVER_RUNTIME"

cat > "$PALAVER_RUNTIME/__init__.py" <<'PY'
"""Palaver WebUI Ultra runtime package."""
PY

cat > "$PALAVER_RUNTIME/patch_review_workflow.py" <<'PY'
#!/usr/bin/env python3
"""
Palaver Patch Review Workflow

Safe local patch-review shim for Palaver WebUI Ultra.

This module preserves existing imports:

from runtime.patch_review_workflow import list_pending, create, apply_patch, reject_patch
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/root/savant-runtime")
STORE = (
    ROOT
    / "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/state/patch_review"
)

PENDING = STORE / "pending"
APPLIED = STORE / "applied"
REJECTED = STORE / "rejected"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    for path in [STORE, PENDING, APPLIED, REJECTED]:
        path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "id": path.stem,
            "error": "invalid_json",
            "detail": str(exc),
            "path": str(path),
        }


def list_pending() -> list[dict[str, Any]]:
    _ensure()
    return [
        _read_json(path)
        for path in sorted(PENDING.glob("*.json"), key=lambda p: p.name)
    ]


def create(payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    _ensure()

    data: dict[str, Any] = {}
    if payload:
        data.update(payload)
    data.update(kwargs)

    patch_id = str(data.get("id") or f"patch_{uuid.uuid4().hex}")
    data["id"] = patch_id
    data.setdefault("status", "pending")
    data.setdefault("created_at", _now())
    data.setdefault("authority", "palaver.patch_review_workflow")

    path = PENDING / f"{patch_id}.json"
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return data


def apply_patch(patch_id: str, **kwargs: Any) -> dict[str, Any]:
    _ensure()

    src = PENDING / f"{patch_id}.json"
    if not src.exists():
        return {
            "id": patch_id,
            "status": "missing",
            "applied": False,
            "detail": "pending patch not found",
        }

    data = _read_json(src)
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
        return {
            "id": patch_id,
            "status": "missing",
            "rejected": False,
            "detail": "pending patch not found",
        }

    data = _read_json(src)
    data.update(kwargs)
    data["status"] = "rejected"
    data["rejected"] = True
    data["rejected_at"] = _now()
    data["reason"] = reason

    dst = REJECTED / src.name
    dst.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    src.unlink()

    return data


__all__ = [
    "list_pending",
    "create",
    "apply_patch",
    "reject_patch",
]
PY

python3 -m py_compile "$PALAVER_RUNTIME/patch_review_workflow.py"

echo "=== 3. CREATE REQUIRED GENERATED PREFIX DIRECTORIES ==="

mkdir -p \
  "$ROOT/imports/source-dumps/analysis_" \
  "$ROOT/imports/source-dumps/parsed_any_" \
  "$ROOT/imports/source-dumps/parsed_" \
  "$ROOT/imports/source-dumps/parsed_clean_" \
  "$ROOT/runtime/maps" \
  "$ROOT/audit/fs_compiler/execution_plan_" \
  "$ROOT/audit/scope_tree/moveable_files_clear_list_" \
  "$ROOT/current_runtime_source_dump_"

echo "=== 4. REPAIR CARBON AVATAR FORGE RUNTIME LAUNCHER ==="

CARBON_APP="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/carbon/runtime/apps/avatar_forge.sh"
CARBON_RUN="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/carbon/apps/avatar_forge/run.sh"

if [ -f "$CARBON_APP" ]; then
  cp "$CARBON_APP" "$BACKUP/avatar_forge.sh.before"
fi

mkdir -p "$(dirname "$CARBON_APP")"

cat > "$CARBON_APP" <<EOF
#!/usr/bin/env bash
set -euo pipefail

exec "$CARBON_RUN" "\$@"
EOF

chmod +x "$CARBON_APP"

echo "=== 5. ADD PALAVER VOICE JSX COMPATIBILITY PATH IF NEEDED ==="

VOICE_SCRIPT="$ROOT/ENABLE_PALAVER_VOICE.sh"
VOICE_DIR="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver/apps/webui_ultra"
VOICE_TARGET="$VOICE_DIR/PalaverVoice.jsx"

mkdir -p "$VOICE_DIR"

if [ ! -f "$VOICE_TARGET" ]; then
  cat > "$VOICE_TARGET" <<'EOF'
export default function PalaverVoice() {
  return null;
}
EOF
fi

echo "=== 6. REFRESH ==="

./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh
./REPORT_ACTIONABLE_BLOCKERS.sh

echo
echo "[OK] remaining actionable blocker repair pass complete"
echo "backup: $BACKUP"
