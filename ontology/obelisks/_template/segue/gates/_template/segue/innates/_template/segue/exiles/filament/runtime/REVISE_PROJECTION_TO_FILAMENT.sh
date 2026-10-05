.#!/usr/bin/env bash
set -euo pipefail

ROOT="/root/savant-runtime"
EXILES_ROOT="$ROOT/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

FILAMENT="$EXILES_ROOT/filament"
PROJECTION="$EXILES_ROOT/projection"
OPUS="$EXILES_ROOT/opus"

mkdir -p \
  "$FILAMENT/runtime" \
  "$FILAMENT/runtime/projectors" \
  "$FILAMENT/registry/views" \
  "$FILAMENT/registry/projectors" \
  "$FILAMENT/registry/contracts" \
  "$FILAMENT/canon" \
  "$FILAMENT/authority" \
  "$FILAMENT/lineage" \
  "$FILAMENT/graph" \
  "$FILAMENT/observatory" \
  "$FILAMENT/interface/api" \
  "$FILAMENT/interface/runtime" \
  "$FILAMENT/interface/events" \
  "$FILAMENT/interface/capabilities" \
  "$FILAMENT/introspection"

cat > "$FILAMENT/entity.json" <<'JSON'
{
  "id": "filament",
  "type": "exile",
  "status": "active",
  "owner": "filament",
  "purpose": "Filament owns deterministic projection, derived views, graph projections, interface projections, and relationship-visible renderings from authoritative primitives.",
  "rule": "Other exiles expose authoritative primitives. Filament derives projections."
}
JSON

cat > "$FILAMENT/canon/filament_projection_ownership.md" <<'MD'
# FILAMENT PROJECTION OWNERSHIP
# STATUS: CANON
# AUTHORITY: USER DIRECTIVE

Filament is the projection exile.

Projection is not a separate exile.

Filament owns deterministic derived views across:

- graph
- UI
- API
- runtime
- docs
- search
- observatory

Other exiles store authoritative primitives only.

Filament derives views from primitives without mutating source authority.
MD

cat > "$FILAMENT/registry/views/canonical_views.json" <<'JSON'
{
  "id": "filament.canonical_views",
  "owner": "filament",
  "status": "active",
  "views": {
    "graph": {
      "purpose": "Derive graph-addressable node and edge views."
    },
    "ui": {
      "purpose": "Derive interface-ready display views."
    },
    "api": {
      "purpose": "Derive API response shapes from authoritative primitives."
    },
    "runtime": {
      "purpose": "Derive runtime execution views."
    },
    "docs": {
      "purpose": "Derive readable documentation views."
    },
    "search": {
      "purpose": "Derive searchable index views."
    },
    "observatory": {
      "purpose": "Derive telemetry and monitoring views."
    }
  }
}
JSON

cat > "$FILAMENT/registry/contracts/projection_contract.json" <<'JSON'
{
  "id": "filament.projection_contract",
  "type": "runtime_contract",
  "status": "active",
  "owner": "filament",
  "rule": "Filament reads authoritative primitives and emits deterministic derived projections without mutating source authority."
}
JSON

cat > "$FILAMENT/interface/capabilities/capabilities.json" <<'JSON'
{
  "id": "filament.capabilities",
  "owner": "filament",
  "type": "capability_manifest",
  "status": "active",
  "capabilities": [
    "derive_graph_view",
    "derive_ui_view",
    "derive_api_view",
    "derive_runtime_view",
    "derive_docs_view",
    "derive_search_view",
    "derive_observatory_view"
  ]
}
JSON

cat > "$FILAMENT/runtime/projectors/base.py" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class FilamentProjectionError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json_safe(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(read_text(path))
    except Exception as e:
        return {
            "path": str(path),
            "error": "invalid_json",
            "detail": str(e)
        }


def entity_record(path: Path) -> Dict[str, Any]:
    return {
        "path": str(path),
        "name": path.name,
        "is_dir": path.is_dir(),
        "is_file": path.is_file()
    }
PY

cat > "$FILAMENT/runtime/projectors/graph_view.py" <<'PY'
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from projectors.base import read_json_safe


def project_graph(root: str) -> Dict[str, Any]:
    base = Path(root)
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for entity in base.rglob("entity.json"):
        data = read_json_safe(entity)
        node_id = data.get("id") or str(entity.parent)

        nodes.append({
            "id": node_id,
            "type": data.get("type", "unknown"),
            "path": str(entity.parent),
            "status": data.get("status", "unknown")
        })

        parent = entity.parent.parent
        if (parent / "entity.json").exists():
            pdata = read_json_safe(parent / "entity.json")
            edges.append({
                "source": pdata.get("id") or str(parent),
                "target": node_id,
                "relation": "contains"
            })

    return {
        "owner": "filament",
        "projection": "graph",
        "root": str(base),
        "nodes": nodes,
        "edges": edges
    }
PY

cat > "$FILAMENT/runtime/projectors/docs_view.py" <<'PY'
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from projectors.base import read_json_safe


def project_docs(root: str) -> Dict[str, Any]:
    base = Path(root)
    rows: List[Dict[str, Any]] = []

    for entity in base.rglob("entity.json"):
        data = read_json_safe(entity)
        rows.append({
            "id": data.get("id"),
            "type": data.get("type"),
            "status": data.get("status"),
            "purpose": data.get("purpose", ""),
            "path": str(entity.parent)
        })

    return {
        "owner": "filament",
        "projection": "docs",
        "root": str(base),
        "entities": rows
    }
PY

cat > "$FILAMENT/runtime/filament_projection.py" <<'PY'
from __future__ import annotations

from typing import Any, Dict

from projectors.docs_view import project_docs
from projectors.graph_view import project_graph


def project(root: str, view: str = "graph") -> Dict[str, Any]:
    if view == "graph":
        return project_graph(root)

    if view == "docs":
        return project_docs(root)

    raise ValueError(f"unsupported filament projection view: {view}")
PY

touch "$FILAMENT/runtime/__init__.py"
touch "$FILAMENT/runtime/projectors/__init__.py"

# Retire accidental projection exile if it exists.
if [ -d "$PROJECTION" ]; then
  mkdir -p "$EXILES_ROOT/_retired"
  mv "$PROJECTION" "$EXILES_ROOT/_retired/projection_retired_$(date -u +%Y%m%dT%H%M%SZ)"
fi

# Remove projection from old generated lists/scripts where safe.
find "$ROOT" -type f \( -name "*.sh" -o -name "*.json" -o -name "*.md" -o -name "*.py" \) \
  -not -path "*/node_modules/*" \
  -not -path "*/.venv*/*" \
  -print0 \
| xargs -0 sed -i \
  -e 's/Projection is an exile./Filament is the projection exile./g' \
  -e 's/Projection owns/Filament owns/g' \
  -e 's/projection owns/filament owns/g' \
  -e 's/"owner": "projection"/"owner": "filament"/g' \
  -e 's/"id": "projection"/"id": "filament"/g' \
  -e 's/exiles\/projection/exiles\/filament/g' \
  -e 's/PROJECTION_EXILE/FILAMENT_EXILE/g' \
  -e 's/PROJECTION="/FILAMENT="/g' || true

cat > "$FILAMENT/graph/projection_ownership.json" <<'JSON'
{
  "id": "filament:projection_ownership",
  "type": "authority_edge",
  "source": "exile:filament",
  "target": "domain:projection",
  "relation": "owns",
  "authority": "user_directive",
  "description": "Filament is the canonical exile responsible for projection."
}
JSON

echo "[OK] Projection ownership revised to Filament."
echo
echo "FILAMENT:"
find "$FILAMENT" -maxdepth 4 -type f | sort
echo
echo "RETIRED PROJECTION:"
find "$EXILES_ROOT/_retired" -maxdepth 2 -type d 2>/dev/null | sort || true
