#!/usr/bin/env bash
set -euo pipefail

BASE="/root/savant-runtime/imports/source-dumps"
PARSED="$(find "$BASE" -maxdepth 1 -type d -name 'parsed_clean_*' | sort | tail -1)"
OUT="$PARSED/runtime_map.md"

[ -d "$PARSED" ] || { echo "[ERROR] no parsed_clean directory found"; exit 1; }

python3 - "$PARSED" "$OUT" <<'PY'
import json
from pathlib import Path
from collections import defaultdict

parsed = Path(__import__("sys").argv[1])
out = Path(__import__("sys").argv[2])
manifest = json.loads((parsed / "manifest.json").read_text())

records = manifest["records"]

groups = defaultdict(list)
for r in records:
    for t in r["tags"]:
        groups[t].append(r)

priority = [
    "palaver",
    "backend",
    "frontend",
    "voice",
    "ai_api",
    "env",
    "authority",
    "lineage",
    "graph",
    "ontology",
    "registry",
    "vault",
    "observatory",
    "exile",
    "aws_s3",
]

with out.open("w", encoding="utf-8") as w:
    w.write("# SAVANT RUNTIME MAP FROM CURRENT SOURCE\n\n")
    w.write(f"Parsed source: `{manifest['source']}`\n\n")
    w.write(f"Raw sections: `{manifest['raw_sections']}`\n\n")
    w.write(f"Project sections: `{manifest['project_sections']}`\n\n")
    w.write(f"Critical sections: `{manifest['critical_sections']}`\n\n")

    w.write("## System Status\n\n")
    for k in priority:
        w.write(f"- `{k}`: {len(groups.get(k, []))} files\n")

    w.write("\n## Core Runtime Files By Concern\n\n")

    for tag in priority:
        items = groups.get(tag, [])
        if not items:
            continue
        w.write(f"### {tag.upper()}\n\n")
        for r in items[:80]:
            w.write(f"- `{r['path']}`")
            if r.get("endpoints"):
                w.write(f" endpoints={r['endpoints']}")
            if r.get("envvars"):
                w.write(f" env={r['envvars']}")
            w.write("\n")
        w.write("\n")

    w.write("## Backend Endpoints\n\n")
    found = False
    for r in records:
        if r.get("endpoints"):
            found = True
            w.write(f"### `{r['path']}`\n\n")
            for e in r["endpoints"]:
                w.write(f"- `{e['method']} {e['path']}`\n")
            w.write("\n")
    if not found:
        w.write("No Flask-style endpoints detected.\n\n")

    w.write("## Environment Variables\n\n")
    env_map = defaultdict(set)
    for r in records:
        for e in r.get("envvars", []):
            env_map[e].add(r["path"])

    for e in sorted(env_map):
        w.write(f"- `{e}`\n")
        for p in sorted(env_map[e])[:20]:
            w.write(f"  - `{p}`\n")

    w.write("\n## Immediate Engineering Assessment\n\n")
    w.write("Confirmed from current dump:\n\n")
    w.write("- Palaver has frontend source.\n")
    w.write("- Palaver has backend source.\n")
    w.write("- Voice layer exists in project scripts/UI patches.\n")
    w.write("- AI provider integration exists but needs credential/API validation.\n")
    w.write("- Authority, lineage, graph, ontology, registry, vault, and observatory terms exist in source.\n\n")

    w.write("Problems visible from current dump:\n\n")
    w.write("- Runtime dump still includes generated/import analysis artifacts and patch scripts.\n")
    w.write("- Voice implementation appears patch-script based rather than integrated into canonical app source.\n")
    w.write("- Parser detected many ontology references, but runtime map still needs filesystem-source validation before canon patching.\n\n")

    w.write("Recommended next patch:\n\n")
    w.write("1. Move Palaver voice from patch scripts into canonical Palaver app source.\n")
    w.write("2. Wire frontend `/api/palaver` to backend `127.0.0.1:8787` through Vite proxy or production proxy.\n")
    w.write("3. Add a persistent service launcher for backend, frontend, and tunnel.\n")
    w.write("4. Add runtime map artifacts under `/root/savant-runtime/runtime/maps/`.\n")
    w.write("5. Add canon records for Palaver voice interface, backend endpoint, speech normalization, and AI-provider dependency.\n")

print(out)
PY

cat "$OUT"
