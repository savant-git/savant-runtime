#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$ROOT/audit/foundation_phase_06"
REPORT="$REPORT_DIR/phase_06_semantic_reference_graph_$STAMP.md"

mkdir -p "$REPORT_DIR" "$ROOT/tools/semantic_graph"

cat > "$ROOT/tools/semantic_graph/build_semantic_reference_graph.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path("/root/savant-runtime")
DB = ROOT / "audit/fs_compiler/db/savant_fs_compiler.sqlite"
OUT = ROOT / "context/SEMANTIC_REFERENCE_GRAPH.json"

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

SEMANTIC_FILES = {
    "module.json",
    "entity.json",
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
    "projection_engine.json",
    "runtime_graph.json",
    "authority_index.json",
    "lineage_index.json",
}

KEY_HINTS = {
    "id",
    "kind",
    "type",
    "name",
    "owner",
    "scope",
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
    "capabilities",
    "contracts",
    "interfaces",
    "templates",
    "instances",
    "segues",
    "projections",
    "lineage",
    "inherits",
    "extends",
    "module",
    "engine",
    "runtime",
    "path",
    "file",
}

def ignored(path: Path) -> bool:
    return any(part in IGNORE for part in path.parts)

def file_id(path: Path) -> str:
    return str(path.relative_to(ROOT))

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))

def iter_semantic_json() -> list[Path]:
    rows = []
    for path in ROOT.rglob("*.json"):
        if ignored(path):
            continue
        if path.name in SEMANTIC_FILES or any(part in {"registry", "authority", "lineage", "graph", "interface", "segue"} for part in path.parts):
            rows.append(path)
    return sorted(rows)

def normalize_ref(value: Any) -> list[str]:
    refs: list[str] = []

    if isinstance(value, str):
        v = value.strip()
        if not v:
            return refs

        if "/" in v or ":" in v or "." in v:
            refs.append(v)

    elif isinstance(value, list):
        for item in value:
            refs.extend(normalize_ref(item))

    elif isinstance(value, dict):
        if "id" in value and isinstance(value["id"], str):
            refs.append(value["id"])
        if "path" in value and isinstance(value["path"], str):
            refs.append(value["path"])

    return refs

def walk(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            kpath = f"{path}.{key}" if path else key

            if key in KEY_HINTS:
                for ref in normalize_ref(value):
                    yield kpath, key, ref

            yield from walk(value, kpath)

    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, f"{path}[{idx}]")

def resolve_ref(ref: str) -> dict[str, Any]:
    result = {
        "reference": ref,
        "resolved": False,
        "resolution_kind": "unresolved",
        "target_path": "",
    }

    if ref.startswith("/root/savant-runtime/"):
        p = Path(ref)
        result["target_path"] = str(p)
        result["resolved"] = p.exists()
        result["resolution_kind"] = "absolute_path" if p.exists() else "missing_absolute_path"
        return result

    if ref.startswith("ontology/") or ref.startswith("canon/") or ref.startswith("authority_graph/"):
        p = ROOT / ref
        result["target_path"] = str(p)
        result["resolved"] = p.exists()
        result["resolution_kind"] = "relative_path" if p.exists() else "missing_relative_path"
        return result

    # id-style resolution against JSON ids
    return result

def main() -> int:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    parse_failures: list[dict[str, Any]] = []

    id_index: dict[str, str] = {}

    for path in iter_semantic_json():
        fid = file_id(path)
        try:
            data = load_json(path)
        except Exception as exc:
            parse_failures.append({
                "path": fid,
                "error": str(exc),
            })
            continue

        obj_id = data.get("id") if isinstance(data, dict) else None
        obj_kind = data.get("kind") if isinstance(data, dict) else None

        node_id = obj_id or fid

        nodes[node_id] = {
            "id": node_id,
            "path": fid,
            "kind": obj_kind or "json",
        }

        if obj_id:
            id_index[obj_id] = node_id

    for path in iter_semantic_json():
        fid = file_id(path)
        try:
            data = load_json(path)
        except Exception:
            continue

        src_id = data.get("id") if isinstance(data, dict) and data.get("id") else fid

        for key_path, key, ref in walk(data):
            resolved = resolve_ref(ref)

            target_id = ""
            if ref in id_index:
                target_id = id_index[ref]
                resolved["resolved"] = True
                resolved["resolution_kind"] = "object_id"

            elif resolved["resolved"] and resolved["target_path"]:
                try:
                    target_id = str(Path(resolved["target_path"]).relative_to(ROOT))
                except Exception:
                    target_id = resolved["target_path"]

            edge = {
                "source": src_id,
                "source_path": fid,
                "key_path": key_path,
                "relationship": key,
                "reference": ref,
                "target": target_id,
                "resolved": resolved["resolved"],
                "resolution_kind": resolved["resolution_kind"],
                "target_path": resolved["target_path"],
            }

            edges.append(edge)

            if not edge["resolved"]:
                unresolved.append(edge)

    graph = {
        "id": "semantic_reference_graph",
        "root": str(ROOT),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "unresolved_count": len(unresolved),
        "parse_failure_count": len(parse_failures),
        "nodes": nodes,
        "edges": edges,
        "unresolved": unresolved,
        "parse_failures": parse_failures,
    }

    OUT.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "id": graph["id"],
        "node_count": graph["node_count"],
        "edge_count": graph["edge_count"],
        "unresolved_count": graph["unresolved_count"],
        "parse_failure_count": graph["parse_failure_count"],
        "out": str(OUT),
    }, indent=2, sort_keys=True))

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/tools/semantic_graph/build_semantic_reference_graph.py"

echo "=== FAST AUDIT REFRESH ==="
./RERUN_FS_COMPILER_FAST_NONMOVE_PASSES.sh
./PATCH_FAST_BLOCKER_CLASSIFIER.sh

echo "=== BUILD SEMANTIC REFERENCE GRAPH ==="
python3 "$ROOT/tools/semantic_graph/build_semantic_reference_graph.py" | tee "$REPORT"

echo
echo "[OK] phase 06 semantic graph report:"
echo "$REPORT"
echo "/root/savant-runtime/context/SEMANTIC_REFERENCE_GRAPH.json"
