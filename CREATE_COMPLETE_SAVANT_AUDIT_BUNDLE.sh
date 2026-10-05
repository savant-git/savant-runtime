
#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
OUT="$ROOT/exports"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE="$OUT/savant_complete_audit_bundle_$STAMP"
DUMP="$BUNDLE/savant_complete_source_dump_$STAMP.txt"

mkdir -p "$BUNDLE"

echo "[1/8] writing complete scoped source dump"

python3 - <<'PY' > "$DUMP"
import os
import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/root/savant-runtime")

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "dist",
    "build",
    ".venv",
    ".venv_voice",
    "venv",
    "site-packages",
}

IGNORE_SUFFIXES = {
    ".pyc", ".pyo", ".swp", ".swo", ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp3", ".wav", ".mp4", ".mov", ".zip", ".tar", ".gz", ".tgz", ".db",
    ".sqlite", ".sqlite3", ".lock"
}

MAX_FILE_BYTES = 2_000_000

def skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & IGNORE_DIRS:
        return True
    if path.suffix.lower() in IGNORE_SUFFIXES:
        return True
    if "/exports/" in str(path):
        return True
    return False

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

files = []
dirs = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    pdir = Path(dirpath)
    dirnames[:] = [d for d in dirnames if not skip(pdir / d)]

    for d in dirnames:
        p = pdir / d
        if not skip(p):
            dirs.append(p)

    for name in filenames:
        p = pdir / name
        if not skip(p) and p.is_file():
            files.append(p)

files = sorted(files, key=lambda p: str(p))
dirs = sorted(dirs, key=lambda p: str(p))

print("SAVANT COMPLETE SOURCE DUMP")
print("=" * 120)
print("created_utc:", datetime.now(timezone.utc).isoformat())
print("root:", ROOT)
print("directories:", len(dirs))
print("files:", len(files))
print()

print("TREE")
print("=" * 120)
for p in dirs:
    print(str(p.relative_to(ROOT)) + "/")
for p in files:
    print(str(p.relative_to(ROOT)))
print()

print("FILE MANIFEST")
print("=" * 120)
for p in files:
    try:
        st = p.stat()
        print(json.dumps({
            "path": str(p),
            "relpath": str(p.relative_to(ROOT)),
            "size_bytes": st.st_size,
            "sha256": sha256(p),
            "modified_epoch": st.st_mtime,
        }, sort_keys=True))
    except Exception as e:
        print(json.dumps({
            "path": str(p),
            "error": str(e),
        }, sort_keys=True))
print()

print("SOURCE CONTENTS")
print("=" * 120)

for p in files:
    rel = str(p.relative_to(ROOT))
    print()
    print("=" * 120)
    print(f"FILE: {rel}")
    print(f"ABS: {p}")
    print("=" * 120)

    try:
        size = p.stat().st_size
        if size > MAX_FILE_BYTES:
            print(f"[SKIPPED_TOO_LARGE] {size} bytes")
            continue

        data = p.read_text(encoding="utf-8", errors="replace")
        print(data)
    except Exception as e:
        print(f"[READ_ERROR] {e}")
PY

echo "[2/8] copying compiler reports and audit outputs"
mkdir -p "$BUNDLE/audit"
cp -a "$ROOT/audit" "$BUNDLE/audit/current_audit_tree" 2>/dev/null || true

echo "[3/8] running compiler audit if available"
if [ -x "$ROOT/RERUN_FS_COMPILER_ALL_NONMOVE_PASSES.sh" ]; then
  "$ROOT/RERUN_FS_COMPILER_ALL_NONMOVE_PASSES.sh" > "$BUNDLE/compiler_rerun_$STAMP.log" 2>&1 || true
fi

echo "[4/8] creating filesystem inventory"
find "$ROOT" \
  \( -path '*/node_modules/*' -o -path '*/.git/*' -o -path '*/__pycache__/*' -o -path '*/.venv/*' -o -path '*/site-packages/*' -o -path '*/exports/*' \) -prune \
  -o -print \
  | sort > "$BUNDLE/filesystem_inventory_$STAMP.txt"

echo "[5/8] creating source-only checksum manifest"
find "$ROOT" \
  -type f \
  \( -path '*/node_modules/*' -o -path '*/.git/*' -o -path '*/__pycache__/*' -o -path '*/.venv/*' -o -path '*/site-packages/*' -o -path '*/exports/*' \) -prune \
  -o -type f -print \
  | sort \
  | while read -r f; do
      sha256sum "$f" || true
    done > "$BUNDLE/checksums_$STAMP.sha256"

echo "[6/8] creating recursive compliance brief"
cat > "$BUNDLE/RECURSIVE_COMPLIANCE_BRIEF.md" <<'EOF'
# Recursive Compliance Brief

Required architecture:

- Store only authoritative primitives.
- Represent authority as instances and segues.
- Generate commands, capabilities, modules, engines, registry, context, UI, exports, and reports as deterministic projections.
- Files are projections, not primary architecture.
- Segues are first-class transition objects.
- Meta Archetype → Archetype → Template → Instance → Segue → Authority Graph → Projection is the target root.
- Existing implementation must be extended, not replaced.
- No filesystem moves are safe until compile/import/reference/symlink/path checks all pass.

Immediate correction path:

1. Preserve current tree.
2. Produce full source dump.
3. Run compiler audit.
4. Repair broken syntax/import/reference issues.
5. Create foundation authority layer.
6. Make future generated scripts expose provenance, lineage, dependencies, relationships, and originating instances/segues.
EOF

echo "[7/8] creating transfer tarball"
cd "$OUT"
tar -czf "savant_complete_audit_bundle_$STAMP.tar.gz" "savant_complete_audit_bundle_$STAMP"

echo "[8/8] copying to Android downloads if available"
if [ -d /storage/emulated/0/Download ]; then
  cp "$OUT/savant_complete_audit_bundle_$STAMP.tar.gz" /storage/emulated/0/Download/
  cp "$DUMP" /storage/emulated/0/Download/
fi

echo
echo "[OK] created:"
echo "$OUT/savant_complete_audit_bundle_$STAMP.tar.gz"
echo "$DUMP"
echo
echo "Android copies if available:"
echo "/storage/emulated/0/Download/savant_complete_audit_bundle_$STAMP.tar.gz"
echo "/storage/emulated/0/Download/savant_complete_source_dump_$STAMP.txt"
