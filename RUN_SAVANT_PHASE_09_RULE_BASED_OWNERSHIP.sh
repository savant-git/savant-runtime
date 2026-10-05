#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT/audit/foundation_phase_09"
REPORT="$REPORT_DIR/phase_09_rule_based_ownership_$STAMP.md"
BACKUP="$ROOT/repair_backups/$STAMP"

mkdir -p "$REPORT_DIR" "$BACKUP" "$ROOT/tools/ownership_graph"

echo "======================================================="
echo "PHASE 09: RULE-BASED OWNERSHIP COMPILER"
echo "======================================================="

cp "$ROOT/tools/ownership_graph/compile_canonical_ownership_graph.py" \
   "$BACKUP/compile_canonical_ownership_graph.py.before_phase09" 2>/dev/null || true

cat > "$ROOT/tools/ownership_graph/compile_canonical_ownership_graph.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
OUT = ROOT / "context/CANONICAL_OWNERSHIP_GRAPH.json"

EXILES = {
    "carbon", "cataxis", "coda", "envoy", "filament", "graffiti", "lore", "mobius",
    "modus", "niche", "notary", "opus", "pact", "palaver", "shatter", "underscore",
    "urge", "zero",
}

GENERATED_PREFIXES = {
    "audit": ("audit", "generated_audit", "generated.audit", 100),
    "imports": ("imports", "imported_source", "imports", 100),
    "exports": ("exports", "generated_export", "exports", 100),
    "_reports": ("reports", "generated_report", "reports", 100),
    "repair_backups": ("backup", "repair_backup", "repair_backups", 100),
}

AUTHORITY_PREFIXES = {
    "canon": ("savant", "canon", "canon", 0),
    "authority_graph": ("savant", "authority_graph", "authority_graph", 1),
    "ontology": ("ontology", "ontology", "ontology", 5),
}

RUNTIME_PREFIXES = {
    "runtime": ("runtime", "runtime", "runtime", 9),
    "vault": ("vault", "vault", "vault", 8),
    "tools": ("savant_tools", "tools", "tools", 9),
    "scripts": ("runtime_ops", "scripts", "scripts", 9),
    "ops": ("runtime_ops", "ops", "ops", 9),
    "context": ("projection", "context_projection", "context", 10),
    "port": ("port", "port_namespace", "port", 8),
    "webui_ultra": ("palaver", "legacy_webui_projection", "palaver.webui_ultra", 10),
}

def owner_from_rel(rel: str) -> dict:
    p = Path(rel)
    parts = p.parts
    first = parts[0] if parts else rel

    if "exiles" in parts:
        i = parts.index("exiles")
        if i + 1 < len(parts):
            candidate = parts[i + 1]
            if candidate in EXILES:
                subzone = parts[i + 2] if i + 2 < len(parts) else "root"
                return {
                    "owner": candidate,
                    "scope": "single_exile",
                    "canonical_zone": f"exile.{candidate}.{subzone}",
                    "authority_tier": 7,
                    "generated": False,
                }
            if candidate == "segue":
                return {
                    "owner": "exiles",
                    "scope": "all_exiles",
                    "canonical_zone": "exiles.segue",
                    "authority_tier": 6,
                    "generated": False,
                }

    if first in GENERATED_PREFIXES:
        owner, scope, zone, tier = GENERATED_PREFIXES[first]
        return {
            "owner": owner,
            "scope": scope,
            "canonical_zone": zone,
            "authority_tier": tier,
            "generated": True,
        }

    if first in AUTHORITY_PREFIXES:
        owner, scope, zone, tier = AUTHORITY_PREFIXES[first]
        if rel.startswith("canon/foundation/"):
            zone = "canon.foundation"
            tier = 0
        return {
            "owner": owner,
            "scope": scope,
            "canonical_zone": zone,
            "authority_tier": tier,
            "generated": False,
        }

    if first in RUNTIME_PREFIXES:
        owner, scope, zone, tier = RUNTIME_PREFIXES[first]
        return {
            "owner": owner,
            "scope": scope,
            "canonical_zone": zone,
            "authority_tier": tier,
            "generated": scope.endswith("_projection") or scope.startswith("legacy"),
        }

    if "/" not in rel:
        if rel.endswith(".sh"):
            return {
                "owner": "runtime_ops",
                "scope": "root_orchestration_script",
                "canonical_zone": "ops.runtime.scripts",
                "authority_tier": 9,
                "generated": False,
            }
        if rel.endswith(".py"):
            return {
                "owner": "runtime",
                "scope": "root_runtime_python",
                "canonical_zone": "runtime.root",
                "authority_tier": 9,
                "generated": False,
            }
        if rel.endswith(".log"):
            return {
                "owner": "runtime_logs",
                "scope": "runtime_log",
                "canonical_zone": "logs",
                "authority_tier": 100,
                "generated": True,
            }
        if rel.startswith("current_runtime_source_dump_"):
            return {
                "owner": "imports",
                "scope": "source_dump",
                "canonical_zone": "imports.source_dump",
                "authority_tier": 100,
                "generated": True,
            }
        if rel in {"audit", "imports", "ontology", "authority_graph", "canon", "context", "runtime", "scripts", "tools", "vault", "port", "_reports"}:
            return {
                "owner": "namespace",
                "scope": "top_level_namespace",
                "canonical_zone": f"namespace.{rel}",
                "authority_tier": 50,
                "generated": False,
            }

    return {
        "owner": "unknown",
        "scope": "unknown",
        "canonical_zone": "unknown",
        "authority_tier": 999,
        "generated": False,
    }

def desired_parent(rel: str, info: dict) -> str:
    p = Path(rel)

    if info["generated"]:
        return str(p.parent)

    if info["canonical_zone"] == "ops.runtime.scripts":
        return "ops/runtime/scripts"

    if info["scope"] == "root_runtime_python":
        return "runtime/root"

    return str(p.parent)

def main() -> int:
    if not DB.exists():
        raise SystemExit("[ERROR] missing fs compiler DB")

    con = sqlite3.connect(DB)
    cur = con.cursor()

    rows = cur.execute("""
        SELECT path, relpath, basename, kind, extension, sha256
        FROM files
        WHERE ignored=0
        ORDER BY relpath
    """).fetchall()

    nodes = {}
    violations = []
    unknowns = []

    for path, rel, basename, kind, ext, sha in rows:
        info = owner_from_rel(rel)
        canonical = True
        reason = "ok"

        if info["owner"] == "unknown":
            canonical = False
            reason = "unknown_owner"
            unknowns.append(rel)

        if not info["generated"] and kind == "file" and ext == "sh" and "/" not in rel:
            canonical = False
            reason = "root_shell_script_should_be_ops_scoped"

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
            "generated": info["generated"],
            "desired_parent": desired_parent(rel, info),
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

echo
echo "=== REFRESH ==="
./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh
python3 "$ROOT/tools/semantic_graph/build_semantic_reference_graph.py" || true
python3 "$ROOT/tools/authority_graph/compile_authority_graph.py" || true

echo
echo "=== OWNERSHIP GRAPH ==="
set +e
python3 "$ROOT/tools/ownership_graph/compile_canonical_ownership_graph.py" | tee "$REPORT"
STATUS="${PIPESTATUS[0]}"
set -e

echo
echo "=== UNKNOWN OWNER REPORT ==="
python3 "$ROOT/tools/ownership_graph/report_unknown_owners.py" | tee -a "$REPORT" || true

echo
echo "[OK] phase 09 report:"
echo "$REPORT"
echo "backup: $BACKUP"

if [ "$STATUS" -ne 0 ]; then
  echo
  echo "[BLOCKED] Ownership graph still has unknown owners."
  exit 0
fi

echo
echo "[PASS] Ownership graph has no unknown owners."
