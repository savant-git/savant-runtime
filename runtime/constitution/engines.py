from __future__ import annotations

from typing import Any


class LineageEngine:
    def __init__(self, registry: Any): self.registry = registry
    def ancestors(self, identity: str): return self.registry.graph_model.ancestors(identity)
    def descendants(self, identity: str): return self.registry.graph_model.descendants(identity)
    def supersedes(self, identity: str): return self.registry.graph_model._walk((identity,), "supersedes")
    def superseded_by(self, identity: str): return self.registry.graph_model._walk((identity,), "supersedes", True)
    def migrations(self, identity: str):
        obj = self.registry.get(identity); raw = obj.provenance
        return tuple(str(raw[k]) for k in sorted(raw) if "migration" in k and raw[k])
    def origin(self, identity: str):
        ancestors = self.ancestors(identity); return ancestors[-1] if ancestors else identity
    def reconstruct(self, identity: str):
        return {"origin":self.origin(identity), "parent":self.registry.get(identity).lineage.get("parent"),
                "ancestors":self.ancestors(identity), "ancestry":self.ancestors(identity),
                "descendants":self.descendants(identity), "supersedes":self.supersedes(identity),
                "superseded_by":self.superseded_by(identity), "revision_history":self.supersedes(identity),
                "migrations":self.migrations(identity), "authority_chain":self.registry.authorities.chain(identity)}
    def visualize(self, identity: str):
        ids = {identity, *self.ancestors(identity), *self.descendants(identity), *self.supersedes(identity), *self.superseded_by(identity)}
        graph = self.registry.graph_model.export()
        return {"nodes":[n for n in graph["nodes"] if n["id"] in ids],
                "edges":[e for e in graph["edges"] if e["source"] in ids and e["target"] in ids and e["type"] in {"contains","supersedes"}]}
    def validate(self):
        errors=[]
        try: self.registry.graph_model.detect_cycles("contains", True)
        except ValueError as exc: errors.append(str(exc))
        return tuple(errors)


class ProvenanceEngine:
    FIELDS=("creation_authority","creation_source","creation_method","migration_source","schema_source",
            "bootstrap_source","projection_source","implementation_source","validation_source")
    def __init__(self, registry: Any): self.registry=registry
    def reconstruct(self, identity: str):
        obj=self.registry.get(identity); raw=obj.to_primitives()["provenance"]; metadata=obj.to_primitives()["metadata"]
        result={"creation_authority":dict(self.registry.authorities.effective(identity)),
                "creation_source":raw.get("sources", []), "creation_method":raw.get("method", raw.get("migration", "declaration")),
                "migration_source":raw.get("migration_source", raw.get("migration")),
                "schema_source":self.registry.schemas.schema_for_kind(obj.kind).get("id"),
                "bootstrap_source":raw.get("bootstrap_source", "runtime.constitution.bootstrap"),
                "projection_source":tuple(self.registry.projection_targets(identity)),
                "implementation_source":tuple(metadata.get("implementation_refs", ())),
                "validation_source":"runtime.constitution.validation"}
        return result
    def validate(self, identity: str):
        value=self.reconstruct(identity); return tuple(k for k in self.FIELDS if k not in value)


class DependencyEngine:
    def __init__(self, registry: Any): self.registry=registry
    def direct(self, identity: str): return self.registry.graph_model.direct_dependencies(identity)
    def reverse(self, identity: str, transitive: bool=False): return self.registry.graph_model.reverse_dependencies(identity, transitive)
    def transitive(self, identity: str): return self.registry.graph_model.dependencies(identity)
    def closure(self, identities=()):
        starts=tuple(identities) or self.registry.ids
        return tuple(sorted(set(starts).union(*(set(self.transitive(i)) for i in starts))))
    def cycles(self): return self.registry.graph_model.detect_cycles("depends_on")
    def validate(self):
        ids=set(self.registry.ids)
        return tuple({"id":o.id,"dependency":d} for o in self.registry.values() for d in self.direct(o.id) if d not in ids)
    def visualize(self, identity: str | None=None):
        graph=self.registry.graph_model.export(); edges=[e for e in graph["edges"] if e["type"]=="depends_on"]
        if identity is None: ids=set(self.registry.ids)
        else: ids={identity,*self.transitive(identity),*self.reverse(identity,True)}; edges=[e for e in edges if e["source"] in ids and e["target"] in ids]
        return {"nodes":[n for n in graph["nodes"] if n["id"] in ids],"edges":edges,"cycles":self.cycles()}
