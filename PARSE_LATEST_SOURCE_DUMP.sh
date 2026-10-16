#!/usr/bin/env bash
set -euo pipefail

SRC="/root/savant-runtime/imports/source-dumps/latest_source_dump.txt"
OUTDIR="/root/savant-runtime/imports/source-dumps/parsed_$(date -u +%Y%m%dT%H%M%SZ)"

[ -f "$SRC" ] || { echo "[ERROR] missing $SRC"; exit 1; }

mkdir -p "$OUTDIR"

python3 - "$SRC" "$OUTDIR" <<'PY'
import re, json
from pathlib import Path
from collections import Counter, defaultdict

src = Path(__import__("sys").argv[1])
outdir = Path(__import__("sys").argv[2])
text = src.read_text(encoding="utf-8", errors="replace")

file_re = re.compile(
    r"\n={40,}\nFILE:\s*(.*?)\nBYTES:\s*(.*?)\nSHA256:\s*(.*?)\n={40,}\n\n",
    re.S
)

matches = list(file_re.finditer(text))
files = []

for i, m in enumerate(matches):
    start = m.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    files.append({
        "path": m.group(1).strip(),
        "bytes": int(m.group(2).strip()) if m.group(2).strip().isdigit() else 0,
        "sha256": m.group(3).strip(),
        "body": text[start:end].strip("\n")
    })

if not files:
    files = [{
        "path": "latest_source_dump.txt",
        "bytes": len(text.encode("utf-8", errors="replace")),
        "sha256": "",
        "body": text
    }]

KEYWORDS = {
    "palaver": ["palaver"],
    "frontend": ["react", "vite", "createroot", "jsx", "tsx", "index.html"],
    "backend": ["flask", "fastapi", "express", "server.py", "@app.", "app.post", "app.get"],
    "voice": ["speechrecognition", "webkitspeechrecognition", "speechsynthesis", "speechsynthesisutterance"],
    "ai_api": ["openai", "gemini", "generativelanguage", "anthropic", "api_key"],
    "env": [".env", "os.getenv", "process.env", "dotenv"],
    "aws_s3": ["aws", "s3", "boto3", "bucket"],
    "authority": ["authority"],
    "lineage": ["lineage"],
    "graph": ["graph"],
    "ontology": ["ontology"],
    "exile": ["exile", "innate", "gate", "obelisk", "prodigal", "quirk"],
}

def tags_for(path, body):
    low = (path + "\n" + body).lower()
    return sorted([k for k, vals in KEYWORDS.items() if any(v in low for v in vals)])

tag_counts = Counter()
records = []
endpoints = defaultdict(list)
envvars = defaultdict(list)
symbols = defaultdict(list)

for f in files:
    path = f["path"]
    body = f["body"]
    tags = tags_for(path, body)
    for t in tags:
        tag_counts[t] += 1

    for m in re.finditer(r"""@app\.(get|post|put|delete)\(["']([^"']+)["']\)""", body):
        endpoints[path].append({"method": m.group(1).upper(), "path": m.group(2)})

    for m in re.finditer(r"""(?:os\.getenv\(["']|process\.env\.|import\.meta\.env\.)([A-Z0-9_]+)""", body):
        envvars[path].append(m.group(1))

    for m in re.finditer(r"^\s*(?:class|def|function|const|let|var)\s+([A-Za-z0-9_]+)", body, re.M):
        symbols[path].append(m.group(1))

    records.append({
        "path": path,
        "bytes": f["bytes"],
        "sha256": f["sha256"],
        "tags": tags,
        "endpoints": endpoints[path],
        "envvars": sorted(set(envvars[path])),
        "symbols": symbols[path][:80],
    })

manifest = {
    "source": str(src),
    "sections": len(files),
    "tag_counts": dict(tag_counts),
    "records": records,
}

(outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

with (outdir / "architecture_report.md").open("w", encoding="utf-8") as w:
    w.write("# SOURCE DUMP ARCHITECTURE REPORT\n\n")
    w.write(f"Source: `{src}`\n\n")
    w.write(f"Sections parsed: `{len(files)}`\n\n")

    w.write("## Tag Counts\n\n")
    for k, v in sorted(tag_counts.items()):
        w.write(f"- `{k}`: {v}\n")

    w.write("\n## Key Findings\n\n")
    all_low = text.lower()
    checks = {
        "Palaver references": "palaver" in all_low,
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

    w.write("\n## Parsed Sections\n\n")
    for r in records:
        w.write(f"### `{r['path']}`\n\n")
        w.write(f"- bytes: `{r['bytes']}`\n")
        w.write(f"- tags: `{', '.join(r['tags']) or 'none'}`\n")
        if r["endpoints"]:
            w.write(f"- endpoints: `{r['endpoints']}`\n")
        if r["envvars"]:
            w.write(f"- envvars: `{r['envvars']}`\n")
        if r["symbols"]:
            w.write(f"- symbols: `{r['symbols']}`\n")
        w.write("\n")

with (outdir / "critical_extract.txt").open("w", encoding="utf-8") as w:
    for f in files:
        tags = tags_for(f["path"], f["body"])
        if tags:
            w.write("\n" + "=" * 100 + "\n")
            w.write(f"FILE: {f['path']}\n")
            w.write(f"TAGS: {', '.join(tags)}\n")
            w.write("=" * 100 + "\n\n")
            w.write(f["body"][:250000])
            w.write("\n")

print(outdir)
PY

echo
echo "[OK] parsed:"
echo "$OUTDIR"
echo
sed -n '1,260p' "$OUTDIR/architecture_report.md"
