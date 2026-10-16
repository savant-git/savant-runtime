#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT/audit/foundation_phase_07"
REPORT="$REPORT_DIR/phase_07_authority_graph_$STAMP.md"

mkdir -p "$REPORT_DIR" "$ROOT/tools/authority_graph"

cat > "$ROOT/tools/authority_graph/compile_authority_graph.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path("/root/savant-runtime")
OUT = ROOT / "context/AUTHORITY_GRAPH_COMPILED.json"

IGNORE = {
    ".git",
    ".venv",
    ".venv_voice",
    "node_modules",
    "__pycache__",
    "site-packages",
    "exports",
    "repair_backups",
}

AUTHORITY_ROOTS = [
    ROOT / "canon",
    ROOT / "authority_graph",
    ROOT / "ontology",
]

AUTHORITY_NAMES = {
    "entity.json",
    "module.json",
    "contracts.json",
    "capabilities.json",
    "interfaces.json",
    "manifests.json",
    "templates.json",
    "versions.json",
    "defaults.json",
    "inheritance.json",
    "edges.json",
    "nodes.json",
    "relationships.json",
}

def ignored(path: Path) -> bool:
    return any(part in IGNORE for part in path.parts)

def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))

def authority_tier(path: Path) -> int:
    r = rel(path)

    if r.startswith("canon/foundation/"):
        return 0
    if r.startswith("authority_graph/meta_archetypes/"):
        return 1
    if r.startswith("authority_graph/archetypes/"):
        return 2
    if r.startswith("authority_graph/templates/"):
        return 3
    if r.startswith("authority_graph/instances/"):
        return 4
    if r.startswith("authority_graph/segues/"):
        return 5
    if r.startswith("authority_graph/policies/"):
        return 6
    if "/authority/" in r or "/canon/" in r:
        return 7
    if "/registry/" in r or "/lineage/" in r or "/graph/" in r:
        return 8
    return 9

def kind_from_path(path: Path, data: Any | None) -> str:
    if isinstance(data, dict) and isinstance(data.get("kind"), str):
        return data["kind"]

    r = rel(path)

    if r.startswith("canon/"):
        return "canon"
    if "meta_archetypes" in r:
        return "meta_archetype"
    if "archetypes" in r:
        return "archetype"
    if "templates" in r:
        return "template"
    if "instances" in r:
        return "instance"
    if "segues" in r:
        return "segue"
    if "policies" in r:
        return "policy"
    if path.name == "entity.json":
        return "entity"
    if path.name == "module.json":
        return "module"
    return "authority_artifact"

def owner_from_path(path: Path) -> str:
    parts = path.parts

    if "exiles" in parts:
        i = parts.index("exiles")
        if i + 1 < len(parts):
            return parts[i + 1]

    if "innates" in parts:
        return "innates"
    if "gates" in parts:
        return "gates"
    if "obelisks" in parts:
        return "obelisks"

    return "savant"

def iter_authority_files() -> list[Path]:
    files: list[Path] = []

    for root in AUTHORITY_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if ignored(path) or not path.is_file():
                continue

            if path.suffix == ".md":
                if "canon" in path.parts or "foundation" in path.parts:
                    files.append(path)

            elif path.suffix == ".json":
                if path.name in AUTHORITY_NAMES:
                    files.append(path)
                elif any(part in {"authority_graph", "authority", "canon", "registry", "lineage", "graph", "segue"} for part in path.parts):
                    files.append(path)

    return sorted(set(files), key=lambda p: rel(p))

def collect_refs(obj: Any) -> list[str]:
    refs: list[str] = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {
                "id",
                "kind",
                "type",
                "owner",
                "authority",
                "source",
                "target",
                "from",
                "to",
                "parent",
                "child",
                "depends_on",
                "dependencies",
                "requires",
                "provides",
                "inherits",
                "extends",
                "template",
                "archetype",
                "meta_archetype",
                "segue",
                "segues",
                "projection",
                "projections",
            }:
                refs.extend(collect_refs(v))
            else:
                refs.extend(collect_refs(v))

    elif isinstance(obj, list):
        for x in obj:
            refs.extend(collect_refs(x))

    elif isinstance(obj, str):
        s = obj.strip()
        if s and (":" in s or "/" in s or "." in s):
            refs.append(s)

    return refs

def main() -> int:
    nodes = {}
    edges = []
    conflicts = []
    parse_failures = []

    id_to_path = {}

    for path in iter_authority_files():
        data = None
        parse_error = ""

        if path.suffix == ".json":
            try:
                data = read_json(path)
            except Exception as exc:
                parse_error = str(exc)
                parse_failures.append({"path": rel(path), "error": parse_error})

        node_id = None
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            node_id = data["id"]

        if not node_id:
            node_id = rel(path)

        if node_id in nodes:
            conflicts.append({
                "id": node_id,
                "first_path": nodes[node_id]["path"],
                "second_path": rel(path),
            })

        node = {
            "id": node_id,
            "path": rel(path),
            "kind": kind_from_path(path, data),
            "owner": owner_from_path(path),
            "authority_tier": authority_tier(path),
            "parse_error": parse_error,
        }

        nodes[node_id] = node
        id_to_path[node_id] = rel(path)

    for path in iter_authority_files():
        if path.suffix != ".json":
            continue

        try:
            data = read_json(path)
        except Exception:
            continue

        source_id = data.get("id") if isinstance(data, dict) and data.get("id") else rel(path)

        for ref in collect_refs(data):
            target = ""
            resolved = False

            if ref in id_to_path:
                target = ref
                resolved = True
            elif ref.startswith(("canon/", "authority_graph/", "ontology/")):
                target_path = ROOT / ref
                if target_path.exists():
                    target = ref
                    resolved = True

            edges.append({
                "source": source_id,
                "reference": ref,
                "target": target,
                "resolved": resolved,
            })

    unresolved = [e for e in edges if not e["resolved"]]

    graph = {
        "id": "authority_graph_compiled",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "unresolved_count": len(unresolved),
        "conflict_count": len(conflicts),
        "parse_failure_count": len(parse_failures),
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
        "conflicts": conflicts,
        "parse_failures": parse_failures,
    }

    OUT.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "id": graph["id"],
        "node_count": graph["node_count"],
        "edge_count": graph["edge_count"],
        "unresolved_count": graph["unresolved_count"],
        "conflict_count": graph["conflict_count"],
        "parse_failure_count": graph["parse_failure_count"],
        "out": str(OUT),
    }, indent=2, sort_keys=True))

    return 0 if not conflicts and not parse_failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/tools/authority_graph/compile_authority_graph.py"

echo "=== FAST AUDIT REFRESH ==="
./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh

echo "=== SEMANTIC GRAPH ==="
python3 "$ROOT/tools/semantic_graph/build_semantic_reference_graph.py" || true

echo "=== AUTHORITY GRAPH ==="
set +e
python3 "$ROOT/tools/authority_graph/compile_authority_graph.py" | tee "$REPORT"
STATUS="${PIPESTATUS[0]}"
set -e

echo
echo "[OK] phase 07 authority graph report:"
echo "$REPORT"
echo "/root/savant-runtime/context/AUTHORITY_GRAPH_COMPILED.json"

if [ "$STATUS" -ne 0 ]; then
  echo
  echo "[BLOCKED] Authority graph has conflicts or parse failures."
  exit 0
fi

echo
echo "[PASS] Authority graph compiled without hard conflicts."
