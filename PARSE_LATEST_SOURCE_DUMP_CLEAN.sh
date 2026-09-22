#!/usr/bin/env bash
set -euo pipefail

SRC="/root/savant-runtime/imports/source-dumps/latest_source_dump.txt"
OUTDIR="/root/savant-runtime/imports/source-dumps/parsed_clean_$(date -u +%Y%m%dT%H%M%SZ)"

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

SKIP_PARTS = {
    ".venv_voice",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "site-packages",
    "dist-info",
}

files = []

for i, m in enumerate(matches):
    path = m.group(1).strip()
    parts = set(Path(path).parts)

    if parts & SKIP_PARTS:
        continue

    start = m.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

    files.append({
        "path": path,
        "bytes": int(m.group(2).strip()) if m.group(2).strip().isdigit() else 0,
        "sha256": m.group(3).strip(),
        "body": text[start:end].strip("\n")
    })

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
    "registry": ["registry"],
    "vault": ["vault"],
    "observatory": ["observatory", "observatories"],
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

    for m in re.finditer(r"""@app\.(get|post|put|delete|patch)\(["']([^"']+)["']\)""", body):
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

critical = [
    r for r in records
    if r["tags"] or any(x in r["path"].lower() for x in [
        "package.json",
        "vite.config",
        "server.py",
        "main.jsx",
        "index.html",
        "requirements",
        "runtime",
        "ontology",
        "registry",
    ])
]

manifest = {
    "source": str(src),
    "raw_sections": len(matches),
    "project_sections": len(files),
    "critical_sections": len(critical),
    "tag_counts": dict(tag_counts),
    "records": records,
}

(outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

with (outdir / "architecture_report.md").open("w", encoding="utf-8") as w:
    w.write("# CLEAN SAVANT RUNTIME ARCHITECTURE REPORT\n\n")
    w.write(f"Source: `{src}`\n\n")
    w.write(f"Raw sections: `{len(matches)}`\n\n")
    w.write(f"Project sections after dependency exclusion: `{len(files)}`\n\n")
    w.write(f"Critical sections: `{len(critical)}`\n\n")

    w.write("## Tag Counts\n\n")
    for k, v in sorted(tag_counts.items()):
        w.write(f"- `{k}`: {v}\n")

    w.write("\n## Key Findings\n\n")
    joined = "\n".join((r["path"] + "\n" + next((f["body"] for f in files if f["path"] == r["path"]), "")) for r in records).lower()

    checks = {
        "Palaver references": "palaver" in joined,
        "Frontend references": "react" in joined or "vite" in joined,
        "Backend references": "flask" in joined or "fastapi" in joined or "server.py" in joined,
        "Voice references": "speechrecognition" in joined or "speechsynthesis" in joined,
        "AI API references": "openai" in joined or "gemini" in joined or "generativelanguage" in joined,
        "AWS/S3 references": "s3" in joined or "aws" in joined,
        "Authority references": "authority" in joined,
        "Lineage references": "lineage" in joined,
        "Graph references": "graph" in joined,
        "Ontology references": "ontology" in joined,
        "Registry references": "registry" in joined,
        "Vault references": "vault" in joined,
        "Observatory references": "observatory" in joined or "observatories" in joined,
    }

    for name, ok in checks.items():
        w.write(f"- {'OK' if ok else 'MISSING'} — {name}\n")

    w.write("\n## Critical Project Sections\n\n")
    for r in critical:
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

with (outdir / "critical_sources.txt").open("w", encoding="utf-8") as w:
    body_by_path = {f["path"]: f["body"] for f in files}

    for r in critical:
        w.write("\n" + "=" * 100 + "\n")
        w.write(f"FILE: {r['path']}\n")
        w.write(f"TAGS: {', '.join(r['tags']) or 'none'}\n")
        w.write("=" * 100 + "\n\n")
        w.write(body_by_path.get(r["path"], "")[:300000])
        w.write("\n")

print(outdir)
PY

echo
echo "[OK] clean parsed:"
echo "$OUTDIR"
echo
sed -n '1,260p' "$OUTDIR/architecture_report.md"
