from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from .bootstrap import load_authority
from .graph import ConstitutionalGraph
from .kinds import KindRegistry
from .object import ConstitutionalObject, PRIMITIVE_FIELDS
from .projection import PROJECTION_TARGETS, ProjectionCache, ProjectionEngine, canonical_json
from .relationships import RelationshipTypeRegistry
from .schema import ConstitutionalSchemaRegistry, SchemaValidationError
from .authority import AuthorityResolver
from .identity import CanonicalIdentityResolver

REQUIRED_PRIMITIVES = set(PRIMITIVE_FIELDS)


class ConstitutionalValidationError(ValueError): pass


class ConstitutionalRegistry:
    """Read-only constitutional query registry over immutable identities."""

    def __init__(self, root: Path, objects: Iterable[ConstitutionalObject], kinds: KindRegistry,
                 schemas: ConstitutionalSchemaRegistry, relationships: RelationshipTypeRegistry | None = None):
        self.root = root.resolve(); self.kinds = kinds; self.schemas = schemas
        self.relationship_types = relationships or RelationshipTypeRegistry.discover(self.root)
        self._objects: dict[str, ConstitutionalObject] = {}; self._graph: ConstitutionalGraph | None = None
        self.projection_cache = ProjectionCache()
        self._kind_index: dict[str, list[str]] = {}; self._version_index: dict[str, list[str]] = {}
        for obj in objects: self.register(obj)
        self._graph = ConstitutionalGraph(self.values())
        self.identities = CanonicalIdentityResolver(self.values())
        self.authorities = AuthorityResolver(self)
        from .engines import DependencyEngine, LineageEngine, ProvenanceEngine
        from .reflection import RuntimeReflection
        from .resolver import ConstitutionalResolver
        from .recursive import InheritanceEngine, RecursiveConstitution
        from .paths import ConstitutionalPathResolver
        from .events import ConstitutionalEventLog
        self.dependencies=DependencyEngine(self); self.lineage=LineageEngine(self); self.provenance=ProvenanceEngine(self)
        self.resolver=ConstitutionalResolver(self); self.reflection=RuntimeReflection(self)
        self.inheritance=InheritanceEngine(self); self.recursive=RecursiveConstitution(self); self.paths=ConstitutionalPathResolver(self)
        self.events=ConstitutionalEventLog()

    @classmethod
    def load(cls, root: Path | str | None = None) -> "ConstitutionalRegistry":
        runtime_root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        objects, kinds, schemas, relationships = load_authority(runtime_root)
        return cls(runtime_root, objects, kinds, schemas, relationships)

    @classmethod
    def load_migrated(cls, root: Path | str | None = None) -> "ConstitutionalRegistry":
        runtime_root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        objects, kinds, schemas, relationships = load_authority(runtime_root)
        from .migration import discover_runtime
        migration = discover_runtime(runtime_root, objects)
        result = cls(runtime_root, (*objects, *migration.objects), kinds, schemas, relationships)
        result.runtime_migration = migration
        return result

    def register(self, obj: ConstitutionalObject) -> None:
        if obj.id in self._objects: raise ConstitutionalValidationError(f"immutable id already registered: {obj.id}")
        if not self.kinds.contains(obj.kind): raise ConstitutionalValidationError(f"unknown kind: {obj.kind}")
        try: self.schemas.validate(obj)
        except SchemaValidationError as exc: raise ConstitutionalValidationError(str(exc)) from exc
        for relation in obj.relationships:
            if not self.relationship_types.contains(str(relation.get("type"))):
                raise ConstitutionalValidationError(f"unknown relationship type: {relation.get('type')}")
        self._objects[obj.id] = obj
        self._kind_index.setdefault(obj.kind, []).append(obj.id); self._version_index.setdefault(obj.version, []).append(obj.id)
        self._graph = None
        self.projection_cache.invalidate("version")
        if hasattr(self, "identities"): self.identities = CanonicalIdentityResolver(self.values())

    @property
    def graph_model(self) -> ConstitutionalGraph:
        if self._graph is None: self._graph = ConstitutionalGraph(self.values())
        return self._graph
    @property
    def ids(self) -> tuple[str, ...]: return tuple(sorted(self._objects))
    def values(self) -> tuple[ConstitutionalObject, ...]: return tuple(self._objects[i] for i in self.ids)
    def get(self, object_id: str) -> ConstitutionalObject: return self._objects[self.identities.resolve(object_id)] if hasattr(self, "identities") else self._objects[object_id]
    def get_exact(self, object_id: str) -> ConstitutionalObject: return self._objects[object_id]
    find_by_id = get
    def by_kind(self, kind: str) -> tuple[ConstitutionalObject, ...]: return tuple(self._objects[i] for i in sorted(self._kind_index.get(kind, ())))
    find_by_kind = by_kind
    def by_version(self, version: str) -> tuple[ConstitutionalObject, ...]: return tuple(self._objects[i] for i in sorted(self._version_index.get(version, ())))
    def find_by_authority(self, authority: Mapping[str, Any] | str) -> tuple[ConstitutionalObject, ...]:
        return tuple(o for o in self.values() if (canonical_json(o.to_primitives()["authority"]) == canonical_json(authority) if not isinstance(authority, str) else authority in canonical_json(o.to_primitives()["authority"])))
    def find_by_relationship(self, relationship_type: str, target: str | None = None) -> tuple[ConstitutionalObject, ...]:
        return tuple(o for o in self.values() if any(r["type"] == relationship_type and (target is None or r["target"] == target) for r in o.relationships))

    def lineage_lookup(self, object_id: str) -> dict[str, Any]: return self.lineage.reconstruct(object_id)
    def provenance_lookup(self, object_id: str) -> dict[str, Any]:
        result=self.provenance.reconstruct(object_id); obj=self.get(object_id); parent=obj.lineage.get("parent")
        result.update({"parent_source":self.get(str(parent)).to_primitives()["provenance"].get("sources", ()) if parent else (),"declared":obj.to_primitives()["provenance"]})
        return result
    def find_by_provenance(self, key: str, value: Any) -> tuple[ConstitutionalObject, ...]:
        return tuple(o for o in self.values() if self.provenance_lookup(o.id).get(key) == value)
    def dependency_lookup(self, object_id: str, transitive: bool = True) -> tuple[str, ...]: return self.graph_model.dependencies(object_id) if transitive else self.graph_model.direct_dependencies(object_id)
    find_dependencies = dependency_lookup
    def reverse_dependency_lookup(self, object_id: str, transitive: bool = False) -> tuple[str, ...]: return self.graph_model.reverse_dependencies(object_id, transitive)
    def relationship_lookup(self, object_id: str, relationship_type: str | None = None): return self.graph_model.relationships(object_id, relationship_type)
    def schema_lookup(self, kind: str): return self.schemas.schema_for_kind(kind)
    def projection_targets(self, object_id: str) -> tuple[str, ...]:
        return self.inheritance.projection_targets(object_id) if hasattr(self,"inheritance") else tuple(self.get(object_id).metadata.get("projection_targets",PROJECTION_TARGETS))
    def projection_lookup(self, object_id: str) -> tuple[str, ...]: return self.projection_targets(object_id)
    find_projections = projection_lookup
    def find_ancestors(self, object_id: str) -> tuple[str, ...]: return self.graph_model.ancestors(object_id)
    def find_descendants(self, object_id: str) -> tuple[str, ...]: return self.graph_model.descendants(object_id)
    def governing_doctrine(self, object_id: str):
        local=next((self.get(i) for i in (object_id,*self.find_ancestors(object_id)) if self.get(i).kind=="doctrine"),None)
        if local: return local
        related=next((self.get(str(r["target"])) for i in (object_id,*self.find_ancestors(object_id))
                      for r in self.get(i).relationships if r.get("type") in {"governed_by","derived_from"}
                      and self.get(str(r["target"])).kind=="doctrine"),None)
        return related or next(iter(self.by_kind("doctrine")),None)
    def inherited_authority(self, object_id: str): return self.inheritance.authority(object_id)
    def inherited_projections(self, object_id: str): return self.inheritance.projection_targets(object_id)
    def inherited_schemas(self, object_id: str): return self.inheritance.schemas(object_id)
    def inherited_validators(self, object_id: str): return self.inheritance.validators(object_id)
    def recursive_dependencies(self, object_id: str): return self.dependencies.transitive(object_id)
    def recursive_relationships(self, object_id: str): return self.inheritance.relationships(object_id)
    def constitutional_path(self, source: str, target: str): return self.paths.constitutional(source,target)
    def universe(self, object_id: str, nested: bool=False): return self.recursive.universe(object_id,nested=nested)
    def temporal(self, events=None):
        from .temporal import TemporalConstitution
        return TemporalConstitution(events or self.events.events(),self.values())
    def pipeline(self,target: str="runtime"):
        from .pipeline import ConstitutionalProjectionPipeline
        return ConstitutionalProjectionPipeline(self).run(target)
    def diff(self,other):
        from .diff import ConstitutionalDiffer
        return ConstitutionalDiffer().compare(self,other)
    def self_audit(self):
        from .audit import ConstitutionalSelfAudit
        return ConstitutionalSelfAudit(self).run()
    def contribute(self,engine: str,assertions):
        from .contributions import ConstitutionalAssertionAPI
        return ConstitutionalAssertionAPI(self).contribute(engine,assertions)
    def all_systems(self): return self.by_kind("system")
    def all_faculties(self): return self.by_kind("faculty")
    def all_services(self): return self.by_kind("service")
    def all_exiles(self): return self.by_kind("exile")
    def all_doctrines(self): return self.by_kind("doctrine")
    def all_operators(self): return self.by_kind("operator")
    def all_concepts(self): return self.by_kind("concept")
    def authority_chain(self, object_id: str): return self.authorities.chain(object_id) if hasattr(self, "authorities") else tuple(self.get(i).authority for i in tuple(reversed(self.find_ancestors(object_id))) + (object_id,))
    find_authority_chain = authority_chain
    def provenance_chain(self, object_id: str): return tuple(self.get(i).provenance for i in tuple(reversed(self.find_ancestors(object_id))) + (object_id,))
    find_provenance_chain = provenance_chain
    def lineage_chain(self, object_id: str): return tuple(reversed(self.find_ancestors(object_id))) + (object_id,)
    find_lineage_chain = lineage_chain
    def dependency_tree(self, object_id: str):
        def build(item: str, path: frozenset[str]):
            if item in path: return {"id":item,"cycle":True,"dependencies":[]}
            return {"id":item,"dependencies":[build(child,path|{item}) for child in self.graph_model.direct_dependencies(item)]}
        return build(object_id, frozenset())
    find_dependency_tree = dependency_tree
    def relationship_graph(self, object_id: str | None = None):
        graph = self.graph_model.export()
        if object_id is None: return graph
        related = {object_id} | {e["target"] for e in graph["edges"] if e["source"] == object_id} | {e["source"] for e in graph["edges"] if e["target"] == object_id}
        return {"nodes":[n for n in graph["nodes"] if n["id"] in related],"edges":[e for e in graph["edges"] if e["source"] in related and e["target"] in related]}
    find_relationship_graph = relationship_graph
    def canonical_lookup(self, identity: str): return self.get(self.identities.resolve(identity))
    def lookup(self, criterion: str | None=None, value: Any=None, **query: Any): return self.resolver.lookup(criterion,value,**query)
    def reflect(self, object_id: str): return self.reflection.inspect(object_id)
    def registration(self, object_id: str):
        obj=self.get(object_id); return {**obj.to_primitives(),"schema":dict(self.schemas.schema_for_kind(obj.kind)),
            "projection_targets":self.projection_targets(obj.id),"implementation_references":tuple(obj.metadata.get("implementation_refs",()))}
    def invalidate_projections(self, reason: str): self.projection_cache.invalidate(reason)

    def object(self, object_id: str) -> dict[str, Any]:
        item = self.get(object_id).to_primitives(); lineage = self.lineage_lookup(object_id)
        children = list(self.graph_model.direct_children(object_id))
        legacy = deepcopy(item); legacy.update({"parent": lineage["parent"], "children": children, "lineage": {**lineage, "children": children}, "created_from": item["provenance"].get("sources", []), "projection_targets": item["metadata"].get("projection_targets", list(PROJECTION_TARGETS)), "constitutional_kind": item["kind"]})
        return legacy
    def project(self, target: str, context=None, chained=()) -> dict[str, Any]: return ProjectionEngine(self).project(target, context, chained)
    def graph(self) -> dict[str, Any]:
        exported = self.graph_model.export(); return {"nodes":[self.object(n["id"]) for n in exported["nodes"]], "edges":exported["edges"]}
    def faculty_system_matrix(self) -> list[dict[str, str]]: return [{"faculty":f.id,"system":s.id,"type":"projects_through"} for f in self.by_kind("faculty") for s in self.by_kind("system")]
