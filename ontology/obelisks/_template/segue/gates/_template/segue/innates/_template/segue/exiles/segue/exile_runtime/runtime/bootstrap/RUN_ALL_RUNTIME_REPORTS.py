from __future__ import annotations

import json
import sys
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "services"

if str(SERVICES) not in sys.path:
    sys.path.insert(0, str(SERVICES))

from ENTITY_AUDIT import audit
from ENTITY_GRAPH import build_entity_graph
from ENTITY_VALIDATOR import validate_entities
from REGISTRY_SERVICE import collect_registry_area
from RUNTIME_SERVICE import runtime_files


OUT = Path("/root/savant-runtime/ontology/runtime_reports")
OUT.mkdir(parents=True, exist_ok=True)


def write(name: str, data):
    path = OUT / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[WRITE] {path}")


if __name__ == "__main__":
    audit()

    write("entity_graph.json", build_entity_graph())
    write("entity_validation.json", validate_entities())
    write("runtime_files.json", runtime_files())

    for area in [
        "capabilities",
        "contracts",
        "defaults",
        "interfaces",
        "manifests",
        "schemas",
        "templates",
        "versions",
    ]:
        write(f"registry_{area}.json", collect_registry_area(area))
