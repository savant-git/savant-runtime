#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="$ROOT/audit/savant_repair_foundation_report_$STAMP.md"

mkdir -p "$ROOT/audit"

echo "=== REBUILD COMPILER GRAPH ==="
if [ -x "$ROOT/RERUN_FS_COMPILER_ALL_NONMOVE_PASSES.sh" ]; then
  "$ROOT/RERUN_FS_COMPILER_ALL_NONMOVE_PASSES.sh" || true
fi

echo "=== CREATE FOUNDATION READINESS REPORT ==="

python3 - <<'PY' > "$REPORT"
import json
import py_compile
import subprocess
from pathlib import Path

ROOT = Path("/root/savant-runtime")

print("# Savant Repair + Foundation Hardening Report")
print()
print("Generated from live tree.")
print()

checks = []

required_paths = [
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
    "context/FOUNDATION_CONTEXT.md",
]

print("## Required Foundation Paths")
print()

missing = []
for rel in required_paths:
    path = ROOT / rel
    status = "OK" if path.exists() else "MISSING"
    print(f"- {status}: `{rel}`")
    if not path.exists():
        missing.append(rel)

print()

failures = []

for path in ROOT.rglob("*.json"):
    if any(part in {".venv", "node_modules", "__pycache__", "site-packages"} for part in path.parts):
        continue
    try:
        json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        failures.append(("json", str(path.relative_to(ROOT)), str(e)))

for path in ROOT.rglob("*.py"):
    if any(part in {".venv", "node_modules", "__pycache__", "site-packages"} for part in path.parts):
        continue
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as e:
        failures.append(("python", str(path.relative_to(ROOT)), str(e)))

for path in ROOT.rglob("*.sh"):
    if any(part in {".venv", "node_modules", "__pycache__", "site-packages"} for part in path.parts):
        continue
    proc = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
    if proc.returncode != 0:
        failures.append(("shell", str(path.relative_to(ROOT)), proc.stderr.strip()))

print("## Parse / Compile Audit")
print()
if failures:
    print("BLOCKED")
    print()
    for kind, rel, err in failures[:300]:
        print(f"- {kind}: `{rel}` — {err}")
else:
    print("PASS: JSON, Python, and shell syntax checks passed.")

print()
print("## Structural Verdict")
print()
if missing or failures:
    print("NOT READY FOR MOVES.")
else:
    print("READY FOR NEXT NON-MOVE PHASE: dependency-aware refactoring engine.")
print()
print("Filesystem moves remain blocked until reference rewrite simulation has zero blockers.")
PY

cat "$REPORT"

echo
echo "[OK] report:"
echo "$REPORT"
