from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from .projection import canonical_json


PIPELINE_STAGES=("assertions","validation","inheritance","resolution","relationship_expansion",
                 "dependency_expansion","projection","caching","runtime")


@dataclass(frozen=True)
class PipelineState:
    target: str
    assertions: tuple[Mapping[str,Any],...]=()
    validation: Mapping[str,Any]=field(default_factory=dict)
    inherited: Mapping[str,Any]=field(default_factory=dict)
    resolved: Mapping[str,Any]=field(default_factory=dict)
    relationships: Mapping[str,Any]=field(default_factory=dict)
    dependencies: Mapping[str,Any]=field(default_factory=dict)
    artifact: Mapping[str,Any]=field(default_factory=dict)
    cache: Mapping[str,Any]=field(default_factory=dict)
    runtime: Mapping[str,Any]=field(default_factory=dict)
    completed: tuple[str,...]=()


class PipelineStage(Protocol):
    name: str
    def run(self,state: PipelineState,registry: Any) -> PipelineState: ...


class AssertionStage:
    name="assertions"
    def run(self,state,registry):
        values=tuple(MappingProxyType(o.to_primitives()) for o in registry.values())
        return replace(state,assertions=values,completed=(*state.completed,self.name))


class ValidationStage:
    name="validation"
    def run(self,state,registry):
        from .validation import ConstitutionalValidator
        result=ConstitutionalValidator(registry).validate()
        if not result["valid"]: raise ValueError("constitutional pipeline validation failed")
        return replace(state,validation=result,completed=(*state.completed,self.name))


class InheritanceStage:
    name="inheritance"
    def run(self,state,registry):
        values={i:registry.inheritance.effective(i) for i in registry.ids}
        return replace(state,inherited=values,completed=(*state.completed,self.name))


class ResolutionStage:
    name="resolution"
    def run(self,state,registry):
        values={i:registry.reflect(i) for i in registry.ids}
        return replace(state,resolved=values,completed=(*state.completed,self.name))


class RelationshipExpansionStage:
    name="relationship_expansion"
    def run(self,state,registry):
        values={i:registry.recursive_relationships(i) for i in registry.ids}
        return replace(state,relationships=values,completed=(*state.completed,self.name))


class DependencyExpansionStage:
    name="dependency_expansion"
    def run(self,state,registry):
        values={i:{"direct":registry.dependencies.direct(i),"transitive":registry.dependencies.transitive(i),
                   "reverse":registry.dependencies.reverse(i)} for i in registry.ids}
        return replace(state,dependencies=values,completed=(*state.completed,self.name))


class ProjectionStage:
    name="projection"
    def run(self,state,registry):
        artifact=registry.project(state.target)
        return replace(state,artifact=artifact,completed=(*state.completed,self.name))


class CacheStage:
    name="caching"
    def run(self,state,registry):
        status={"authoritative":False,"digest":state.artifact.get("digest"),"entries":registry.projection_cache.size}
        return replace(state,cache=status,completed=(*state.completed,self.name))


class RuntimeStage:
    name="runtime"
    def run(self,state,registry):
        kinds={kind:tuple(o.id for o in registry.by_kind(kind)) for kind in registry.kinds.ids}
        graph=registry.graph_model.export()
        runtime={"registry":tuple(registry.ids),"indexes":{"kind":kinds},"graph":graph,
                 "reverse_indexes":{"dependencies":{i:registry.dependencies.reverse(i) for i in registry.ids}},
                 "dependency_maps":state.dependencies,"projection_tree":state.artifact,
                 "documentation":registry.project("documentation")["payload"],"reflection_table":state.resolved,
                 "visualization":registry.project("visualization")["payload"],"diagnostics":state.validation["checks"]}
        runtime["digest"]=sha256(canonical_json({"artifact":state.artifact.get("digest"),"ids":list(registry.ids),
            "edges":graph["edges"]}).encode()).hexdigest()
        return replace(state,runtime=runtime,completed=(*state.completed,self.name))


class ConstitutionalProjectionPipeline:
    def __init__(self,registry: Any,stages: tuple[PipelineStage,...]|None=None):
        self.registry=registry; self.stages=stages or (AssertionStage(),ValidationStage(),InheritanceStage(),ResolutionStage(),
            RelationshipExpansionStage(),DependencyExpansionStage(),ProjectionStage(),CacheStage(),RuntimeStage())
        if tuple(s.name for s in self.stages)!=PIPELINE_STAGES: raise ValueError("constitutional pipeline stages are incomplete or out of order")
    def run(self,target: str="runtime"):
        state=PipelineState(target)
        for stage in self.stages: state=stage.run(state,self.registry)
        return state
