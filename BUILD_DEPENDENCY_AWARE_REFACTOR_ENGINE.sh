#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
ENGINE="$ROOT/tools/refactor_engine"
mkdir -p "$ENGINE"

cat > "$ENGINE/refactor_engine.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
OUT = ROOT / "audit/refactor_engine"
OUT.mkdir(parents=True, exist_ok=True)

TEXT_EXTS = {
    ".sh", ".py", ".json", ".md", ".txt", ".yaml", ".yml", ".toml",
    ".service", ".timer", ".js", ".jsx", ".ts", ".tsx", ".css", ".html"
}

IGNORE_PARTS = {".git", ".venv", "node_modules", "__pycache__", "site-packages", "exports"}

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def text_files() -> list[Path]:
    rows = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_PARTS for part in path.parts):
            continue
        if path.suffix in TEXT_EXTS or path.name.endswith((".service", ".timer")):
            rows.append(path)
    return sorted(rows)

def load_moves() -> list[tuple[str, str]]:
    if not DB.exists():
        return []

    con = sqlite3.connect(DB)
    cur = con.cursor()

    rows = cur.execute("""
        SELECT f.path, m.proposed_target
        FROM move_candidates m
        JOIN files f ON f.id=m.file_id
        WHERE m.decision='CANDIDATE'
        ORDER BY f.path
    """).fetchall()

    con.close()
    return [(src, dst) for src, dst in rows]

def build_rewrite_plan() -> dict:
    moves = load_moves()
    files = text_files()

    replacements = []
    for src, dst in moves:
        srcp = Path(src)
        dstp = Path(dst)

        forms = {
            str(srcp): str(dstp),
            str(srcp.relative_to(ROOT)): str(dstp.relative_to(ROOT)),
        }

        for old, new in forms.items():
            replacements.append((old, new, src, dst))

    affected = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        file_changes = []

        for old, new, src, dst in replacements:
            if old in text:
                file_changes.append({
                    "old": old,
                    "new": new,
                    "move_source": src,
                    "move_target": dst,
                    "count": text.count(old),
                })

        if file_changes:
            affected.append({
                "path": str(path),
                "relpath": str(path.relative_to(ROOT)),
                "sha256_before": sha256_text(text),
                "changes": file_changes,
            })

    return {
        "root": str(ROOT),
        "moves": [{"source": s, "target": d} for s, d in moves],
        "affected_files": affected,
    }

def main() -> int:
    plan = build_rewrite_plan()
    path = OUT / "rewrite_plan.json"
    path.write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")

    print("[OK] dependency-aware rewrite plan built")
    print("moves:", len(plan["moves"]))
    print("affected_files:", len(plan["affected_files"]))
    print("plan:", path)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ENGINE/refactor_engine.py"

cat > "$ENGINE/report_rewrite_plan.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/root/savant-runtime")
PLAN = ROOT / "audit/refactor_engine/rewrite_plan.json"

if not PLAN.exists():
    raise SystemExit("[ERROR] Missing rewrite_plan.json")

plan = json.loads(PLAN.read_text(encoding="utf-8"))

print("=== REFACTOR REWRITE PLAN ===")
print("moves:", len(plan.get("moves", [])))
print("affected_files:", len(plan.get("affected_files", [])))

print()
print("=== MOVES ===")
for move in plan.get("moves", []):
    print(f"{move['source']} -> {move['target']}")

print()
print("=== REQUIRED REWRITES ===")
for item in plan.get("affected_files", []):
    print()
    print(item["relpath"])
    for ch in item["changes"]:
        print(f"  {ch['count']}x {ch['old']} -> {ch['new']}")
PY

chmod +x "$ENGINE/report_rewrite_plan.py"

echo "[OK] refactor engine installed:"
echo "$ENGINE/refactor_engine.py"
echo "$ENGINE/report_rewrite_plan.py"
