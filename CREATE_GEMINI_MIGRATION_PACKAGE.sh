#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
OUT="$ROOT/exports"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PKG="$OUT/savant-gemini-migration-$STAMP"
ZIP="$OUT/savant-gemini-migration-$STAMP.zip"

mkdir -p "$OUT"
rm -rf "$PKG"
mkdir -p "$PKG"

export ROOT PKG STAMP

python3 - <<'PY'
import json
import os
import hashlib
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.environ["ROOT"])
PKG = Path(os.environ["PKG"])

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
    "exports",
    "repair_backups",
}

IGNORE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".swp",
    ".swo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp3",
    ".wav",
    ".mp4",
    ".mov",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".lock",
}

SECRET_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}

def skip(path: Path) -> bool:
    return (
        any(part in IGNORE_DIRS for part in path.parts)
        or path.suffix.lower() in IGNORE_SUFFIXES
        or path.name in SECRET_NAMES
    )

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def cmd_out(cmd):
    try:
        p = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=60,
        )
        return (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return str(exc)

files = []
dirs = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    current = Path(dirpath)

    dirnames[:] = [
        name
        for name in dirnames
        if not skip(current / name)
    ]

    for name in dirnames:
        path = current / name
        if not skip(path):
            dirs.append(path)

    for name in filenames:
        path = current / name
        if path.is_file() and not skip(path):
            files.append(path)

files = sorted(files, key=lambda p: str(p))
dirs = sorted(dirs, key=lambda p: str(p))

for subdir in (
    "source",
    "graphs",
    "databases",
    "reports",
    "manifests",
    "raw_context",
    "handoff",
    "environment",
):
    (PKG / subdir).mkdir(parents=True, exist_ok=True)
PY

python3 - <<'PY'
import json
import os
import hashlib
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.environ["ROOT"])
PKG = Path(os.environ["PKG"])

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".cache", "dist", "build", ".venv", ".venv_voice",
    "venv", "site-packages", "exports", "repair_backups"
}
IGNORE_SUFFIXES = {
    ".pyc", ".pyo", ".swp", ".swo", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".mp3", ".wav", ".mp4", ".mov", ".zip", ".tar", ".gz",
    ".tgz", ".lock"
}
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "known_hosts"}

def skip(path: Path) -> bool:
    return (
        any(part in IGNORE_DIRS for part in path.parts)
        or path.suffix.lower() in IGNORE_SUFFIXES
        or path.name in SECRET_NAMES
    )

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def cmd_out(cmd):
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=60)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return str(exc)

files = []
dirs = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    current = Path(dirpath)
    dirnames[:] = [name for name in dirnames if not skip(current / name)]

    for name in dirnames:
        path = current / name
        if not skip(path):
            dirs.append(path)

    for name in filenames:
        path = current / name
        if path.is_file() and not skip(path):
            files.append(path)

files = sorted(files, key=lambda p: str(p))
dirs = sorted(dirs, key=lambda p: str(p))

copy_roots = [
    "canon", "ontology", "runtime", "context", "audit", "imports",
    "vault", "port", "tools", "scripts", "ops", "_reports"
]

for top in copy_roots:
    src = ROOT / top
    if src.exists():
        shutil.copytree(
            src,
            PKG / "source" / top,
            ignore=lambda d, names: [n for n in names if skip(Path(d) / n)],
            dirs_exist_ok=True,
        )

root_dst = PKG / "source/root"
root_dst.mkdir(parents=True, exist_ok=True)

for path in ROOT.iterdir():
    if path.is_file() and not skip(path):
        shutil.copy2(path, root_dst / path.name)

for path in ROOT.rglob("*"):
    if skip(path) or not path.is_file():
        continue
    if path.suffix in {".db", ".sqlite", ".sqlite3"}:
        dst = PKG / "databases" / path.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)

for name in [
    "SEMANTIC_REFERENCE_GRAPH.json",
    "AUTHORITY_GRAPH_COMPILED.json",
    "CANONICAL_OWNERSHIP_GRAPH.json",
    "FULL_REFERENCE_REWRITE_SIMULATION.json",
    "PHASE05_MOVE_SIMULATION.json",
    "FOUNDATION_STATUS.json",
    "STRICT_REPAIR_GATE.json",
]:
    src = ROOT / "context" / name
    if src.exists():
        shutil.copy2(src, PKG / "graphs" / name)

manifest = []

for path in files:
    try:
        st = path.stat()
        manifest.append({
            "path": str(path.relative_to(ROOT)),
            "absolute_path": str(path),
            "size_bytes": st.st_size,
            "mtime_epoch": st.st_mtime,
            "sha256": sha256(path),
            "suffix": path.suffix,
            "is_executable": os.access(path, os.X_OK),
        })
    except Exception as exc:
        manifest.append({"path": str(path), "error": str(exc)})

(PKG / "manifests/PROJECT_MANIFEST.json").write_text(
    json.dumps(
        {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "root": str(ROOT),
            "file_count": len(files),
            "dir_count": len(dirs),
            "files": manifest,
        },
        indent=2,
        sort_keys=True,
    ) + "\n",
    encoding="utf-8",
)

with (PKG / "FILE_INDEX.tsv").open("w", encoding="utf-8") as f:
    f.write("path\tsize_bytes\tmtime_epoch\tsha256\texecutable\n")
    for row in manifest:
        if "error" not in row:
            f.write(
                f"{row['path']}\t{row['size_bytes']}\t{row['mtime_epoch']}\t"
                f"{row['sha256']}\t{row['is_executable']}\n"
            )

with (PKG / "CHECKSUMS.sha256").open("w", encoding="utf-8") as f:
    for row in manifest:
        if "error" not in row:
            f.write(f"{row['sha256']}  {row['path']}\n")

with (PKG / "source/SOURCE_DUMP.txt").open("w", encoding="utf-8") as out:
    out.write("SAVANT COMPLETE GEMINI MIGRATION SOURCE DUMP\n")
    out.write("=" * 120 + "\n")
    out.write(f"created_utc: {datetime.now(timezone.utc).isoformat()}\n")
    out.write(f"root: {ROOT}\n")
    out.write(f"files: {len(files)}\n\n")

    for path in files:
        out.write("\n" + "=" * 120 + "\n")
        out.write(f"FILE: {path.relative_to(ROOT)}\n")
        out.write(f"ABS: {path}\n")
        try:
            out.write(f"SHA256: {sha256(path)}\n")
            out.write("=" * 120 + "\n")
            if path.stat().st_size > 2_000_000:
                out.write(f"[SKIPPED_TOO_LARGE] {path.stat().st_size} bytes\n")
            else:
                text = path.read_text(encoding="utf-8", errors="replace")
                out.write(text)
                if not text.endswith("\n"):
                    out.write("\n")
        except Exception as exc:
            out.write(f"[READ_ERROR] {exc}\n")

(PKG / "00_EXECUTIVE_STATE.md").write_text(
"""# Gemini Handoff

Continue Savant from the exact current state.

Current phase:
Phase 09 rule-based ownership compiler.

Known current state from latest terminal:

- Filesystem DB populated.
- Broken symlinks: 0.
- Ownership unknown: 4.
- Ownership violations: 104.
- Semantic graph unresolved: 1338.
- Authority graph conflicts: 80.
- Authority unresolved: 4006.
- One missing relative shell blocker.
- Move execution remains blocked.

Do not execute filesystem moves yet.

First command after unpacking:

cd /root/savant-runtime
./FAST_SAVANT_STATUS.sh

If accelerator is missing:

cd /root/savant-runtime
chmod +x ACCELERATE_SAVANT_WORKFLOW_NOW.sh
./ACCELERATE_SAVANT_WORKFLOW_NOW.sh
./FAST_SAVANT_STATUS.sh
""",
encoding="utf-8",
)

(PKG / "01_ARCHITECTURE_RULES.md").write_text(
"""# Architecture Rules

- Authority before inference.
- Authority before projection.
- Store only authoritative primitives.
- Generate everything else by deterministic projection.
- Prefer projection over storage.
- Prefer composition over duplication.
- Prefer extension over replacement.
- Everything must expose lineage, provenance, dependencies, and relationships.
- Everything must be recursively composable.
- Everything must be graph-addressable.
- No subsystem may become a dead end.
- No filesystem moves unless proof gates pass.
- Files are projections unless explicitly marked authority.

Canonical root chain:

meta archetype
-> archetype
-> template
-> instance
-> segue
-> authority graph
-> projection
""",
encoding="utf-8",
)

(PKG / "02_NEXT_STEPS.md").write_text(
"""# Next Steps

1. Finish accelerator install if needed.
2. Run FAST_SAVANT_STATUS.sh.
3. Inspect the 4 unknown owners.
4. Patch ownership classifier narrowly.
5. Reduce 104 ownership violations.
6. Rebuild semantic, authority, and ownership graphs.
7. Resolve or classify authority conflicts.
8. Run strict repair gate.
9. Run full move/rewrite simulation.
10. Execute no moves until all gates prove safe.
""",
encoding="utf-8",
)

(PKG / "03_DO_NOT_DO.md").write_text(
"""# Do Not Do

- Do not restart architecture.
- Do not delete source files.
- Do not flatten runtime/package structures.
- Do not execute filesystem moves yet.
- Do not treat generated projections as authority.
- Do not replace current implementation when extension is possible.
- Do not classify unknowns broadly just to reduce blocker count.
- Do not hide semantic unresolved references.
""",
encoding="utf-8",
)

(PKG / "environment/ENVIRONMENT.txt").write_text(
    "python:\n" + cmd_out(["python3", "--version"])
    + "\n\npip freeze:\n" + cmd_out(["python3", "-m", "pip", "freeze"])
    + "\n\nnode:\n" + cmd_out(["node", "--version"])
    + "\n\nnpm:\n" + cmd_out(["npm", "--version"])
    + "\n\nuname:\n" + cmd_out(["uname", "-a"])
    + "\n",
    encoding="utf-8",
)

(PKG / "TREE.txt").write_text(
    cmd_out([
        "bash",
        "-lc",
        "find /root/savant-runtime "
        "\\( -path '*/node_modules/*' -o -path '*/.git/*' -o -path '*/__pycache__/*' -o -path '*/.venv/*' -o -path '*/site-packages/*' -o -path '*/exports/*' -o -path '*/repair_backups/*' \\) -prune "
        "-o -print | sort",
    ]),
    encoding="utf-8",
)

print(f"[OK] package staged: {PKG}")
print(f"files: {len(files)}")
print(f"dirs: {len(dirs)}")
PY

cd "$OUT"

zip -qr "$ZIP" "$(basename "$PKG")"

if [ -d /storage/emulated/0/Download ]; then
  cp "$ZIP" /storage/emulated/0/Download/
fi

echo
echo "[OK] Gemini migration ZIP created:"
echo "$ZIP"
echo
echo "Android copy:"
echo "/storage/emulated/0/Download/$(basename "$ZIP")"
echo
ls -lh "$ZIP"
