#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT/audit/foundation_phase_08"
REPORT="$REPORT_DIR/phase_08_canonical_ownership_graph_$STAMP.md"

mkdir -p "$REPORT_DIR" "$ROOT/tools/ownership_graph"

cat > "$ROOT/tools/ownership_graph/compile_canonical_ownership_graph.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
AUTHORITY = ROOT / "context/AUTHORITY_GRAPH_COMPILED.json"
SEMANTIC = ROOT / "context/SEMANTIC_REFERENCE_GRAPH.json"
OUT = ROOT / "context/CANONICAL_OWNERSHIP_GRAPH.json"

EXILES = {
    "carbon", "cataxis", "coda", "envoy", "filament", "graffiti", "lore", "mobius",
    "modus", "niche", "notary", "opus", "pact", "palaver", "shatter", "underscore",
    "urge", "zero",
}

OWNERSHIP_ROOTS = [
    "canon",
    "authority_graph",
    "ontology",
    "ops",
    "tools",
    "context",
]

def owner_from_rel(rel: str) -> dict:
    parts = Path(rel).parts

    if rel.startswith("canon/foundation/"):
        return {
            "owner": "savant",
            "scope": "foundation",
            "canonical_zone": "canon.foundation",
            "authority_tier": 0,
        }

    if rel.startswith("authority_graph/"):
        zone = parts[1] if len(parts) > 1 else "root"
        return {
            "owner": "savant",
            "scope": zone,
            "canonical_zone": f"authority_graph.{zone}",
            "authority_tier": 1,
        }

    if "exiles" in parts:
        i = parts.index("exiles")
        if i + 1 < len(parts):
            exile = parts[i + 1]
            if exile in EXILES:
                subzone = parts[i + 2] if i + 2 < len(parts) else "root"
                return {
                    "owner": exile,
                    "scope": "single_exile",
                    "canonical_zone": f"exile.{exile}.{subzone}",
                    "authority_tier": 7,
                }
            if exile == "segue":
                return {
                    "owner": "exiles",
                    "scope": "all_exiles",
                    "canonical_zone": "exiles.segue",
                    "authority_tier": 6,
                }

    if rel.startswith("ontology/obelisks/"):
        return {
            "owner": "obelisks",
            "scope": "ontology",
            "canonical_zone": "ontology.obelisks",
            "authority_tier": 5,
        }

    if rel.startswith("ops/"):
        return {
            "owner": "runtime_ops",
            "scope": "ops",
            "canonical_zone": "ops",
            "authority_tier": 9,
        }

    if rel.startswith("tools/"):
        return {
            "owner": "savant_tools",
            "scope": "tools",
            "canonical_zone": "tools",
            "authority_tier": 9,
        }

    if rel.startswith("context/"):
        return {
            "owner": "projection",
            "scope": "context_projection",
            "canonical_zone": "context",
            "authority_tier": 10,
        }

    return {
        "owner": "unknown",
        "scope": "unknown",
        "canonical_zone": "unknown",
        "authority_tier": 99,
    }

def desired_parent(rel: str, owner: str, scope: str, zone: str) -> str:
    p = Path(rel)
    basename = p.name

    if zone.startswith("canon."):
        return str(Path("canon/foundation"))

    if zone.startswith("authority_graph."):
        parts = p.parts
        if len(parts) >= 2:
            return str(Path("authority_graph") / parts[1])
        return "authority_graph"

    if scope == "single_exile" and owner in EXILES:
        parts = p.parts
        if "exiles" in parts:
            i = parts.index("exiles")
            if i + 2 < len(parts):
                return str(Path(*parts[: i + 3]))
        return ""

    if scope == "all_exiles":
        return "ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue"

    if scope == "ops":
        if basename.endswith(".sh"):
            return "ops/runtime/scripts"
        return "ops"

    if scope == "tools":
        return str(p.parent)

    return str(p.parent)

def main() -> int:
    if not DB.exists():
        raise SystemExit("[ERROR] missing fs compiler DB")

    authority = {}
    semantic = {}

    if AUTHORITY.exists():
        authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))

    if SEMANTIC.exists():
        semantic = json.loads(SEMANTIC.read_text(encoding="utf-8"))

    con = sqlite3.connect(DB)
    cur = con.cursor()

    files = cur.execute("""
        SELECT path, relpath, basename, kind, extension, sha256
        FROM files
        WHERE ignored=0
        ORDER BY relpath
    """).fetchall()

    nodes = {}
    violations = []
    unknowns = []

    for path, rel, basename, kind, ext, sha in files:
        info = owner_from_rel(rel)
        parent = desired_parent(rel, info["owner"], info["scope"], info["canonical_zone"])

        canonical = True
        reason = "ok"

        if info["owner"] == "unknown":
            canonical = False
            reason = "unknown_owner"
            unknowns.append(rel)

        if kind == "file" and ext == "sh" and "/" not in rel:
            canonical = False
            reason = "root_shell_script_should_be_projected_or_ops_scoped"

        node = {
            "path": rel,
            "absolute_path": path,
            "basename": basename,
            "kind": kind,
            "extension": ext,
            "sha256": sha,
            "owner": info["owner"],
            "scope": info["scope"],
            "canonical_zone": info["canonical_zone"],
            "authority_tier": info["authority_tier"],
            "desired_parent": parent,
            "canonical": canonical,
            "reason": reason,
        }

        nodes[rel] = node

        if not canonical:
            violations.append(node)

    con.close()

    graph = {
        "id": "canonical_ownership_graph",
        "node_count": len(nodes),
        "violation_count": len(violations),
        "unknown_count": len(unknowns),
        "authority_node_count": authority.get("node_count"),
        "semantic_node_count": semantic.get("node_count"),
        "nodes": nodes,
        "violations": violations,
        "unknowns": unknowns,
    }

    OUT.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "id": graph["id"],
        "node_count": graph["node_count"],
        "violation_count": graph["violation_count"],
        "unknown_count": graph["unknown_count"],
        "out": str(OUT),
    }, indent=2, sort_keys=True))

    return 0 if graph["unknown_count"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/tools/ownership_graph/compile_canonical_ownership_graph.py"

echo "=== FAST AUDIT REFRESH ==="
./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh

echo "=== AUTHORITY + SEMANTIC REFRESH ==="
python3 "$ROOT/tools/semantic_graph/build_semantic_reference_graph.py" || true
python3 "$ROOT/tools/authority_graph/compile_authority_graph.py" || true

echo "=== CANONICAL OWNERSHIP GRAPH ==="
set +e
python3 "$ROOT/tools/ownership_graph/compile_canonical_ownership_graph.py" | tee "$REPORT"
STATUS="${PIPESTATUS[0]}"
set -e

echo
echo "[OK] phase 08 ownership graph report:"
echo "$REPORT"
echo "/root/savant-runtime/context/CANONICAL_OWNERSHIP_GRAPH.json"

if [ "$STATUS" -ne 0 ]; then
  echo
  echo "[BLOCKED] Ownership graph has unknown owners."
  exit 0
fi

echo
echo "[PASS] Ownership graph has no unknown owners."
