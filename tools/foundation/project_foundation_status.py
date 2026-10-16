#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/root/savant-runtime")
OUT = ROOT / "context/FOUNDATION_STATUS.json"

REQUIRED = {
    "canon_foundation": ROOT / "canon/foundation",
    "dynamic_canon_authority": ROOT / "canon-system/authority",
    "constitutional_authority": ROOT / "canon-system/authority/constitution",
    "constitutional_schemas": ROOT / "canon-system/authority/constitution/schemas",
    "exile_authority": ROOT / "canon-system/authority/exiles",
    "authority_graph": ROOT / "authority_graph",
    "meta_archetypes": ROOT / "authority_graph/meta_archetypes",
    "archetypes": ROOT / "authority_graph/archetypes",
    "templates": ROOT / "authority_graph/templates",
    "instances": ROOT / "authority_graph/instances",
    "segues": ROOT / "authority_graph/segues",
    "policies": ROOT / "authority_graph/policies",
    "projections": ROOT / "authority_graph/projections",
}

status = {
    "id": "projection:foundation_status",
    "kind": "projection",
    "authority": "canon/foundation + authority_graph + canon-system/authority",
    "complete": True,
    "checks": {},
}

for key, path in REQUIRED.items():
    exists = path.exists()
    status["checks"][key] = {"path": str(path), "exists": exists}
    if not exists: status["complete"] = False

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(OUT)
