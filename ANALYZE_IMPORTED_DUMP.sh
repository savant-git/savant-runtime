#!/usr/bin/env bash
set -euo pipefail

SRC="/root/savant-runtime/imports/source-dumps/latest_source_dump.txt"
OUTDIR="/root/savant-runtime/imports/source-dumps/analysis_$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$OUTDIR"

python3 - "$SRC" "$OUTDIR" <<'PY'
import re, json
from pathlib import Path
from collections import Counter

src = Path(__import__("sys").argv[1])
outdir = Path(__import__("sys").argv[2])
text = src.read_text(errors="replace")

terms = [
    "palaver","savant","vite","react","flask","fastapi","server.py",
    "openai","gemini","generativelanguage","aws","s3",".env",
    "graph","authority","lineage","ontology","voice","speechrecognition",
    "speechsynthesis","exile","innate","gate","obelisk"
]

counts = {t: len(re.findall(re.escape(t), text, re.I)) for t in terms}

paths = sorted(set(re.findall(
    r'([A-Za-z0-9_./@-]+\.(?:py|js|jsx|ts|tsx|html|css|json|md|txt|sh|yml|yaml|toml))',
    text
)))

likely_files = []
for p in paths:
    low = p.lower()
    if any(x in low for x in [
        "server.py","package.json","vite.config","main.jsx","app.jsx",
        "index.html","src/","api","palaver","savant"
    ]):
        likely_files.append(p)

report = {
    "source": str(src),
    "bytes": src.stat().st_size,
    "term_counts": counts,
    "paths_detected_count": len(paths),
    "likely_project_files": likely_files[:300],
    "all_paths_sample": paths[:500],
    "assessment": {
        "is_full_runtime_dump": False,
        "reason": "Downloaded file is only 159K and parser found one whole-dump section, not a structured source dump with per-file boundaries.",
        "missing_from_dump": [
            "voice implementation",
            "authority source",
            "lineage source",
            "ontology source",
            "full Palaver runtime tree"
        ]
    }
}

(outdir / "dump_assessment.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

with (outdir / "dump_assessment.md").open("w", encoding="utf-8") as w:
    w.write("# IMPORTED SOURCE DUMP ASSESSMENT\n\n")
    w.write(f"Source: `{src}`\n\n")
    w.write(f"Bytes: `{src.stat().st_size}`\n\n")

    w.write("## Term Counts\n\n")
    for k,v in sorted(counts.items()):
        w.write(f"- `{k}`: {v}\n")

    w.write("\n## Likely Project Files Mentioned\n\n")
    for p in likely_files[:120]:
        w.write(f"- `{p}`\n")

    w.write("\n## Assessment\n\n")
    w.write("This is not a complete current runtime source dump.\n\n")
    w.write("It is useful as historical/partial context, but it is not enough to generate an authoritative runtime patch.\n\n")

    w.write("## Required Next Input\n\n")
    w.write("Generate and upload a fresh dump from `/root/savant-runtime`, excluding `node_modules`, `.venv`, caches, logs, and build outputs.\n")

print(outdir)
PY

sed -n '1,220p' "$OUTDIR/dump_assessment.md"
