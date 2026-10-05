from __future__ import annotations

from typing import Any, Iterable, Mapping

from .projection import PROJECTION_TARGETS, canonical_json


RECURSIVE_KINDS = ("domain","system","faculty","service","operator","exile","concept","schema",
                   "relationship","doctrine","instance","segue","policy","validator")


def _merge_mappings(values: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any]={}
    for value in values:
        for key in sorted(value):
            current=value[key]
            if isinstance(current, Mapping) and isinstance(result.get(key), Mapping):
                result[key]=_merge_mappings((result[key],current))
            else: result[key]=current
    return result


class InheritanceEngine:
    """Root-to-leaf inheritance; dependencies intentionally never inherit."""
    def __init__(self, registry: Any): self.registry=registry
    def chain(self, identity: str): return tuple(reversed(self.registry.graph_model.ancestors(identity)))+(identity,)
    def authority(self, identity: str): return _merge_mappings(self.registry.get(i).authority for i in self.chain(identity))
    def relationships(self, identity: str):
        unique={canonical_json(dict(r)):dict(r) for i in self.chain(identity) for r in self.registry.get(i).relationships}
        return tuple(unique[k] for k in sorted(unique))
    def projection_targets(self, identity: str):
        targets={str(v) for i in self.chain(identity) for v in self.registry.get(i).metadata.get("projection_targets",())}
        return tuple(sorted(targets or PROJECTION_TARGETS))
    def metadata(self, identity: str): return _merge_mappings(self.registry.get(i).metadata for i in self.chain(identity))
    def validators(self, identity: str):
        metadata=self.metadata(identity); values=(*metadata.get("validation_rules",()),*metadata.get("validators",()))
        return tuple(sorted({str(v) for v in values}))
    def schemas(self, identity: str):
        values=[]
        for item in self.chain(identity):
            schema=dict(self.registry.schemas.schema_for_kind(self.registry.get(item).kind))
            if schema.get("id") not in {v.get("id") for v in values}: values.append(schema)
        return tuple(values)
    def effective(self, identity: str):
        return {"authority":self.authority(identity),"relationships":self.relationships(identity),
                "projection_targets":self.projection_targets(identity),"metadata":self.metadata(identity),
                "validation_rules":self.validators(identity),"schemas":self.schemas(identity),
                "dependencies":self.registry.dependencies.direct(identity)}
    def validate(self):
        errors=[]
        for identity in self.registry.ids:
            try: self.effective(identity)
            except Exception as exc: errors.append({"id":identity,"error":str(exc)})
        return tuple(errors)


class RecursiveConstitution:
    """Projects an unlimited constitutional universe from parent edges."""
    def __init__(self, registry: Any): self.registry=registry
    def children(self, identity: str): return tuple(self.registry.get(i) for i in self.registry.graph_model.direct_children(identity))
    def universe(self, identity: str, *, nested: bool=False):
        obj=self.registry.get(identity); descendants=self.registry.graph_model.descendants(identity)
        grouped={kind:[] for kind in RECURSIVE_KINDS}
        for item in descendants:
            child=self.registry.get(item); grouped.setdefault(child.kind,[]).append(item)
        result={"object":obj.to_primitives(),"children":self.registry.graph_model.direct_children(identity),
                "descendants":descendants,"contains":{k:tuple(sorted(v)) for k,v in sorted(grouped.items())},
                "inheritance":self.registry.inheritance.effective(identity)}
        if nested: result["universe"]=tuple(self.universe(i,nested=True) for i in result["children"])
        return result
