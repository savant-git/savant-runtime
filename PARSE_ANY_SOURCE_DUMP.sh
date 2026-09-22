#!/usr/bin/env bash
set -euo pipefail

SRC="/root/savant-runtime/imports/source-dumps/latest_source_dump.txt"
OUTDIR="/root/savant-runtime/imports/source-dumps/parsed_any_$(date -u +%Y%m%dT%H%M%SZ)"

[ -f "$SRC" ] || { echo "[ERROR] missing $SRC"; exit 1; }

mkdir -p "$OUTDIR"

python3 - "$SRC" "$OUTDIR" <<'PY'
import re, json
from pathlib import Path
from collections import Counter

src = Path(__import__("sys").argv[1])
outdir = Path(__import__("sys").argv[2])
text = src.read_text(encoding="utf-8", errors="replace")

patterns = [
    re.compile(r"\n={20,}\nFILE:\s*(.*?)\n(?:BYTES:.*?\n)?(?:SHA256:.*?\n)?={20,}\n", re.S),
    re.compile(r"\n---+\s*(?:FILE|PATH):\s*(.*?)\s*---+\n", re.I),
    re.compile(r"\n```(?:[a-zA-Z0-9_-]+)?\s*\n#\s*(?:FILE|PATH):\s*(.*?)\n", re.I),
    re.compile(r"\n(?:FILE|PATH):\s*([^\n]+\.(?:py|js|jsx|ts|tsx|html|css|json|md|txt|sh|yml|yaml|toml))\n", re.I),
]

splits = []
for pat in patterns:
    ms = list(pat.finditer(text))
    if len(ms) > len(splits):
        splits = ms

files = []

if splits:
    for i, m in enumerate(splits):
        path = m.group(1).strip().strip("`")
        start = m.end()
        end = splits[i+1].start() if i+1 < len(splits) else len(text)
        body = text[start:end].strip()
        files.append({"path": path, "body": body})
else:
    # fallback: one whole dump
    files.append({"path": src.name, "body": text})

keywords = {
    "frontend": ["react", "vite", "createroot", "jsx", "tsx", "index.html"],
    "backend": ["flask", "fastapi", "express", "server.py", "@app.", "app.post", "app.get"],
    "voice": ["speechrecognition", "webkitspeechrecognition", "speechsynthesis", "speechsynthesisutterance"],
    "ai": ["openai", "gemini", "generativelanguage", "anthropic", "api_key"],
    "env": [".env", "os.getenv", "process.env", "dotenv"],
    "aws": ["aws", "s3", "boto3", "bucket"],
    "savant": ["savant", "palaver", "ontology", "authority", "lineage", "graph", "exile", "innate"],
}

def tags_for(path, body):
    low = (path + "\n" + body).lower()
    return [k for k, vals in keywords.items() if any(v in low for v in vals)]

records = []
tag_counts = Counter()

for f in files:
    tags = tags_for(f["path"], f["body"])
    for t in tags:
        tag_counts[t] += 1

    records.append({
        "path": f["path"],
        "chars": len(f["body"]),
        "tags": tags,
    })

manifest = {
    "source": str(src),
    "format_detected": "split" if splits else "whole_dump_fallback",
    "file_sections": len(files),
    "tag_counts": dict(tag_counts),
    "records": records,
}

(outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

with (outdir / "architecture_report.md").open("w", encoding="utf-8") as w:
    w.write("# SOURCE DUMP ARCHITECTURE REPORT\n\n")
    w.write(f"Source: `{src}`\n\n")
    w.write(f"Format detected: `{manifest['format_detected']}`\n\n")
    w.write(f"Sections parsed: `{len(files)}`\n\n")

    w.write("## Tag Counts\n\n")
    for k, v in sorted(tag_counts.items()):
        w.write(f"- `{k}`: {v}\n")

    w.write("\n## Sections\n\n")
    for r in records:
        w.write(f"- `{r['path']}` — chars={r['chars']} tags={','.join(r['tags']) or 'none'}\n")

    w.write("\n## Key Findings\n\n")
    all_low = text.lower()
    checks = {
        "Palaver references": "palaver" in all_low,
        "Savant references": "savant" in all_low,
        "Frontend references": "react" in all_low or "vite" in all_low,
        "Backend references": "flask" in all_low or "fastapi" in all_low or "server.py" in all_low,
        "Voice references": "speechrecognition" in all_low or "speechsynthesis" in all_low,
        "AI API references": "openai" in all_low or "gemini" in all_low or "generativelanguage" in all_low,
        "AWS/S3 references": "s3" in all_low or "aws" in all_low,
        "Authority references": "authority" in all_low,
        "Lineage references": "lineage" in all_low,
        "Graph references": "graph" in all_low,
        "Ontology references": "ontology" in all_low,
    }
    for name, ok in checks.items():
        w.write(f"- {'OK' if ok else 'MISSING'} — {name}\n")

with (outdir / "critical_extract.txt").open("w", encoding="utf-8") as w:
    for f in files:
        tags = tags_for(f["path"], f["body"])
        if tags or len(files) == 1:
            w.write("\n" + "="*100 + "\n")
            w.write(f"SECTION: {f['path']}\n")
            w.write(f"TAGS: {', '.join(tags) or 'none'}\n")
            w.write("="*100 + "\n\n")
            w.write(f["body"][:200000])
            w.write("\n")

print(outdir)
PY

echo "[OK] parsed:"
echo "$OUTDIR"
sed -n '1,220p' "$OUTDIR/architecture_report.md"
