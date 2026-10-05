#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
ENV_FILE="/root/.env"
BUCKET="savant-ai-cluster"
PREFIX="source-dumps"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="/root/savant-runtime/current_runtime_source_dump_${STAMP}.txt"

set -a
source "$ENV_FILE"
set +a

cd "$ROOT"

python3 - <<'PY' "$ROOT" "$OUT"
import os, hashlib, json
from pathlib import Path
from datetime import datetime, timezone

root = Path(__import__("sys").argv[1])
out = Path(__import__("sys").argv[2])

SKIP_DIRS = {
    ".git","node_modules","__pycache__",".pytest_cache",".mypy_cache",
    ".venv","venv","env","dist","build",".cache","coverage"
}
SKIP_SUFFIX = {
    ".log",".png",".jpg",".jpeg",".gif",".webp",".mp4",".mov",".zip",".gz",".tar",".tgz",
    ".sqlite",".db",".pyc",".woff",".woff2",".ttf"
}
KEEP_SUFFIX = {
    ".py",".js",".jsx",".ts",".tsx",".html",".css",".json",".md",".txt",".sh",".yml",".yaml",".toml"
}

def skip(p):
    parts=set(p.relative_to(root).parts)
    if parts & SKIP_DIRS:
        return True
    if p.suffix.lower() in SKIP_SUFFIX:
        return True
    if p.suffix.lower() not in KEEP_SUFFIX:
        return True
    if p.stat().st_size > 750_000:
        return True
    return False

def sha(p):
    h=hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

files=[]
for p in sorted(root.rglob("*")):
    if p.is_file() and not skip(p):
        files.append(p)

with out.open("w", encoding="utf-8", errors="replace") as w:
    w.write("CURRENT SAVANT RUNTIME SOURCE DUMP\n")
    w.write("="*100+"\n")
    w.write(f"Created UTC: {datetime.now(timezone.utc).isoformat()}\n")
    w.write(f"Root: {root}\n")
    w.write(f"Files included: {len(files)}\n\n")

    w.write("FILE TREE\n")
    w.write("="*100+"\n")
    for p in files:
        w.write(str(p.relative_to(root))+"\n")

    for p in files:
        rel = p.relative_to(root)
        body = p.read_text(encoding="utf-8", errors="replace")
        w.write("\n"+"="*100+"\n")
        w.write(f"FILE: {rel}\n")
        w.write(f"BYTES: {p.stat().st_size}\n")
        w.write(f"SHA256: {sha(p)}\n")
        w.write("="*100+"\n\n")
        w.write(body)
        if not body.endswith("\n"):
            w.write("\n")

print(out)
PY

aws s3 cp "$OUT" "s3://${BUCKET}/${PREFIX}/$(basename "$OUT")"

echo "[OK] uploaded:"
echo "s3://${BUCKET}/${PREFIX}/$(basename "$OUT")"
