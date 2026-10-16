from __future__ import annotations

from collections import defaultdict
from typing import Any


def migration_readiness_report(registry: Any) -> dict[str, Any]:
    authorities: dict[str, list[str]] = defaultdict(list)
    for obj in registry.values(): authorities[str(obj.to_primitives()["authority"])].append(obj.id)
    validation = __import__("runtime.constitution.validation", fromlist=["ConstitutionalValidator"]).ConstitutionalValidator(registry).validate()
    return {
        "objects_lacking_lineage":[o.id for o in registry.values() if "parent" not in o.lineage],
        "objects_lacking_provenance":[o.id for o in registry.values() if not o.provenance],
        "duplicate_identities":[],
        "duplicate_authorities":[ids for ids in authorities.values() if len(ids)>1],
        "schema_inconsistencies":validation["checks"]["schema"],
        "relationship_inconsistencies":validation["checks"]["relationships"],
        "dependency_inconsistencies":validation["checks"]["dependencies"],
        "dependency_cycles":registry.graph_model.detect_cycles("depends_on"),
        "auto_fixed":False,
    }
