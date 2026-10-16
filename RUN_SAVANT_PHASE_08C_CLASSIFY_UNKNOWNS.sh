#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTDIR="$ROOT/audit/foundation_phase_08"
mkdir -p "$OUTDIR"

python3 <<'PY'
from pathlib import Path
import json
from collections import defaultdict

ROOT = Path("/root/savant-runtime")
GRAPH = ROOT/"context/CANONICAL_OWNERSHIP_GRAPH.json"

graph = json.loads(GRAPH.read_text())

unknown = graph.get("unknowns", [])

groups = defaultdict(list)

for rel in unknown:

    p = Path(rel)

    if len(p.parts) == 1:
        groups["root_runtime"].append(rel)
        continue

    if "repair_backups" in p.parts:
        groups["repair_backups"].append(rel)
        continue

    if "imports" in p.parts:
        groups["imports"].append(rel)
        continue

    if "__pycache__" in p.parts:
        groups["pycache"].append(rel)
        continue

    if ".venv" in p.parts or ".venv_voice" in p.parts:
        groups["venv"].append(rel)
        continue

    if "site-packages" in p.parts:
        groups["site_packages"].append(rel)
        continue

    if "audit" in p.parts:
        groups["audit"].append(rel)
        continue

    if "context" in p.parts:
        groups["context"].append(rel)
        continue

    if "tools" in p.parts:
        groups["tools"].append(rel)
        continue

    if "ops" in p.parts:
        groups["ops"].append(rel)
        continue

    if "ontology" in p.parts:
        groups["ontology"].append(rel)
        continue

    groups["other"].append(rel)

report = ROOT/"audit/foundation_phase_08"/"unknown_owner_groups.json"
report.write_text(json.dumps(groups,indent=2))

print()
print("========== UNKNOWN OWNER GROUPS ==========")
print()

for k in sorted(groups):
    print(f"{k:20} {len(groups[k]):5}")

print()
print(report)
PY
