from __future__ import annotations

from typing import Any


class RuntimeReflection:
    """Deterministic answers derived exclusively from registered constitutional data."""
    def __init__(self, registry: Any): self.registry=registry
    def inspect(self, identity: str) -> dict[str, Any]:
        obj=self.registry.get(identity); lineage=self.registry.lineage.reconstruct(obj.id)
        provenance=self.registry.provenance.reconstruct(obj.id); graph=self.registry.graph_model.export()
        implementation=tuple(obj.metadata.get("implementation_refs", ()))
        documentation=tuple(x for x in provenance["creation_source"] if str(x).lower().endswith((".md",".rst",".txt")))
        return {
            "identity":obj.id, "kind":obj.kind, "purpose":obj.description,
            "declared_at":tuple(provenance["creation_source"]), "governed_by":dict(self.registry.authorities.effective(obj.id)),
            "created_by":{"authority":provenance["creation_authority"],"method":provenance["creation_method"]},
            "schema":dict(self.registry.schemas.schema_for_kind(obj.kind)),
            "dependents":self.registry.dependencies.reverse(obj.id), "dependencies":self.registry.dependencies.direct(obj.id),
            "superseded_by":lineage["superseded_by"], "supersedes":lineage["supersedes"],
            "runtime_components":implementation, "documentation":documentation,
            "graph_nodes":tuple(n for n in graph["nodes"] if n["id"]==obj.id),
            "projection_targets":self.registry.projection_targets(obj.id), "lineage":lineage, "provenance":provenance,
        }
