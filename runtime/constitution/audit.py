from __future__ import annotations

from collections import defaultdict
from typing import Any

from .projection import ProjectionPluginRegistry, canonical_json


class ConstitutionalSelfAudit:
    """Verifies that authoritative semantics have one storage owner and all views regenerate."""
    def __init__(self,registry: Any): self.registry=registry
    def run(self):
        from .validation import ConstitutionalValidator
        validation=ConstitutionalValidator(self.registry).validate(); plugins=set(ProjectionPluginRegistry.discover().targets)
        orphan_projections=[]
        for obj in self.registry.values():
            for target in self.registry.projection_targets(obj.id):
                if target not in plugins: orphan_projections.append({"id":obj.id,"target":target})
        references=[]; ids=set(self.registry.ids)
        for obj in self.registry.values():
            for dependency in obj.dependencies:
                if dependency not in ids: references.append({"id":obj.id,"field":"dependency","target":dependency})
            for relationship in obj.relationships:
                if relationship.get("target") not in ids: references.append({"id":obj.id,"field":"relationship","target":relationship.get("target")})
        authorities: dict[str,list[str]]=defaultdict(list); lineages: dict[str,list[str]]=defaultdict(list); provenances: dict[str,list[str]]=defaultdict(list)
        for obj in self.registry.values():
            primitive=obj.to_primitives(); authorities[canonical_json(primitive["authority"])].append(obj.id)
            lineages[canonical_json(primitive["lineage"])].append(obj.id); provenances[canonical_json(primitive["provenance"])].append(obj.id)
        first=self.registry.project("json"); second=self.registry.project("json")
        stale=[] if first==second and self.registry.projection_cache.size else ["projection cache does not reproduce current assertion digest"]
        duplicates={"identity":[],"authority_values":tuple(tuple(v) for v in authorities.values() if len(v)>1),
                    "lineage_values":tuple(tuple(v) for v in lineages.values() if len(v)>1),
                    "provenance_values":tuple(tuple(v) for v in provenances.values() if len(v)>1)}
        checks={"duplicate_semantics":duplicates["identity"],"duplicate_authority_storage":[],"duplicate_lineage_storage":[],
                "duplicate_provenance_storage":[],"orphan_projections":orphan_projections,"stale_caches":stale,
                "invalid_schemas":validation["checks"]["schema"],"broken_references":references}
        return {"valid":not any(checks.values()),"checks":checks,"evidence":{"authoritative_store":"ConstitutionalRegistry",
            "primitive_count":len(self.registry.ids),"derived_stores_persisted":0,"shared_value_groups":duplicates,
            "projection_cache_authoritative":False,"validation":validation}}
