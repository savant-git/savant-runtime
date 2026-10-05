from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import perf_counter_ns
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Protocol

from .bootstrap import bootstrap as constitutional_bootstrap
from .object import ConstitutionalObject
from .projection import ProjectionPluginRegistry
from .validation import ConstitutionalValidator, RuntimeMigrationValidator


class LifecyclePhase(str, Enum):
    DECLARED="declared"; DISCOVERED="discovered"; VALIDATED="validated"; REGISTERED="registered"
    BOOTSTRAPPED="bootstrapped"; READY="ready"; PROJECTED="projected"; ACTIVE="active"
    DEPRECATED="deprecated"; RETIRED="retired"


_TRANSITIONS = {
    LifecyclePhase.DECLARED:{LifecyclePhase.DISCOVERED}, LifecyclePhase.DISCOVERED:{LifecyclePhase.VALIDATED},
    LifecyclePhase.VALIDATED:{LifecyclePhase.REGISTERED}, LifecyclePhase.REGISTERED:{LifecyclePhase.BOOTSTRAPPED},
    LifecyclePhase.BOOTSTRAPPED:{LifecyclePhase.READY}, LifecyclePhase.READY:{LifecyclePhase.PROJECTED},
    LifecyclePhase.PROJECTED:{LifecyclePhase.ACTIVE}, LifecyclePhase.ACTIVE:{LifecyclePhase.PROJECTED,LifecyclePhase.DEPRECATED},
    LifecyclePhase.DEPRECATED:{LifecyclePhase.RETIRED}, LifecyclePhase.RETIRED:set(),
}


class LifecycleTransitionError(ValueError): pass


class LifecycleTracker:
    """Projected lifecycle state; never persisted as constitutional authority."""
    def __init__(self, identities: Iterable[str]): self._states={i:LifecyclePhase.DECLARED for i in identities}
    def add(self, identity: str) -> None:
        if identity in self._states: raise ValueError(f"lifecycle identity already exists: {identity}")
        self._states[identity]=LifecyclePhase.DECLARED
    def transition(self, identity: str, phase: LifecyclePhase) -> LifecyclePhase:
        current=self._states[identity]
        if phase not in _TRANSITIONS[current]: raise LifecycleTransitionError(f"illegal lifecycle transition: {identity}: {current.value} -> {phase.value}")
        self._states[identity]=phase; return phase
    def get(self, identity: str) -> LifecyclePhase: return self._states[identity]
    def snapshot(self) -> Mapping[str,str]: return MappingProxyType({i:self._states[i].value for i in sorted(self._states)})


@dataclass(frozen=True)
class BusEvent:
    sequence: int; topic: str; object_id: str; payload: Mapping[str,Any]


class ConstitutionalBus:
    """In-memory transport only; events are notifications, never authoritative state."""
    def __init__(self): self._sequence=0; self._subscribers:dict[str,list[Callable[[BusEvent],None]]]={}
    def subscribe(self, topic: str, handler: Callable[[BusEvent],None]) -> Callable[[],None]:
        self._subscribers.setdefault(topic,[]).append(handler)
        def unsubscribe(): self._subscribers.get(topic,[]).remove(handler)
        return unsubscribe
    def publish(self, topic: str, object_id: str, payload: Mapping[str,Any]|None=None) -> BusEvent:
        self._sequence+=1; event=BusEvent(self._sequence,topic,object_id,MappingProxyType(dict(payload or {})))
        for handler in tuple((*self._subscribers.get(topic,()),*self._subscribers.get("*",()))): handler(event)
        return event


class HealthState(str,Enum):
    HEALTHY="healthy"; DEGRADED="degraded"; INVALID="invalid"; DEPRECATED="deprecated"; FAILED="failed"


@dataclass(frozen=True)
class HealthProjection:
    object_id: str; state: HealthState; reasons: tuple[str,...]; authority_chain: tuple[Mapping[str,Any],...]


@dataclass(frozen=True)
class Diagnostic:
    code: str; object_id: str; message: str; dependency: str|None
    authority_chain: tuple[Mapping[str,Any],...]; lineage: tuple[str,...]; provenance: tuple[Mapping[str,Any],...]


@dataclass(frozen=True)
class Metric:
    name: str; duration_ns: int; object_count: int; edge_count: int


class ConstitutionalSubsystemContract(Protocol):
    identity: str
    def discover(self, platform: "ConstitutionalPlatform") -> Any: ...
    def validate(self, platform: "ConstitutionalPlatform") -> Any: ...
    def register(self, platform: "ConstitutionalPlatform") -> Any: ...
    def bootstrap(self, platform: "ConstitutionalPlatform") -> Any: ...
    def project(self, platform: "ConstitutionalPlatform", target: str) -> Any: ...
    def shutdown(self, platform: "ConstitutionalPlatform") -> Any: ...
    def health(self, platform: "ConstitutionalPlatform") -> HealthProjection: ...
    def diagnostics(self, platform: "ConstitutionalPlatform") -> tuple[Diagnostic,...]: ...
    def migration(self, platform: "ConstitutionalPlatform") -> Any: ...


@dataclass(frozen=True)
class SubsystemAttachment:
    identity: str
    implementation: str
    version: str="1.0.0"
    def discover(self, platform):
        candidate=Path(self.implementation)
        return candidate.is_file() if candidate.suffix==".py" else importlib.util.find_spec(self.implementation) is not None
    def validate(self, platform): return platform.registry.get(self.identity)
    def register(self, platform): return self.identity in platform.registry.ids
    def bootstrap(self, platform): return {"identity":self.identity,"implementation":self.implementation}
    def project(self, platform, target): return platform.project(target,self.identity)
    def shutdown(self, platform): return {"identity":self.identity,"shutdown":True}
    def health(self, platform): return platform.health(self.identity)
    def diagnostics(self, platform): return platform.diagnostics(self.identity)
    def migration(self, platform): return {"identity":self.identity,"reversible":platform.migration_report.get("reversible",False)}


@dataclass(frozen=True)
class ConstitutionalCapability:
    identity: str; version: str; operators: tuple[str,...]; dependencies: tuple[str,...]


@dataclass(frozen=True)
class ConstitutionalPlugin:
    identity: str; version: str; definitions: tuple[Mapping[str,Any],...]; subsystem: SubsystemAttachment


FUTURE_ATTACHMENT_POINTS = ("fluid_canon","memory","persona","reasoning","planning","knowledge","conversation","narrative","projects","documents","characters","scenes","world_state","timeline","relationship_engine","kindred_engine","projection_engine","context_engine")


class FutureSubsystemInterface(Protocol):
    def entrypoint(self) -> ConstitutionalSubsystemContract: ...


class ConstitutionalPlatform:
    def __init__(self, root: Path, registry: Any, migration: Any, migration_report: Mapping[str,Any]):
        self.root=root; self.registry=registry; self.runtime_migration=migration; self.migration_report=dict(migration_report)
        self.bus=ConstitutionalBus(); self.lifecycle=LifecycleTracker(registry.ids); self._metrics:list[Metric]=[]
        self._subsystems:dict[str,SubsystemAttachment]={}; self._validation:dict[str,Any]={}; self._diagnostics:list[Diagnostic]=[]

    @classmethod
    def start(cls, root: Path|str, plugin_paths: Iterable[Path]=()) -> "ConstitutionalPlatform":
        root=Path(root).resolve(); started=perf_counter_ns(); result=constitutional_bootstrap(root)
        platform=cls(root,result.registry,result.runtime_migration,result.report or {})
        platform._record("bootstrap",started); platform._advance_all(LifecyclePhase.DISCOVERED)
        platform.discover_subsystems()
        for path in plugin_paths: platform.load_plugin(path)
        platform.validate(); platform._advance_all(LifecyclePhase.VALIDATED); platform._advance_all(LifecyclePhase.REGISTERED)
        for subsystem in platform.subsystems: subsystem.register(platform)
        platform._advance_all(LifecyclePhase.BOOTSTRAPPED)
        for subsystem in platform.subsystems: subsystem.bootstrap(platform)
        platform._advance_all(LifecyclePhase.READY); platform.project("runtime")
        return platform

    def _record(self,name: str,started: int): self._metrics.append(Metric(name,perf_counter_ns()-started,len(self.registry.ids),len(self.registry.graph_model.edges)))
    def _advance_all(self,phase: LifecyclePhase):
        for identity in self.registry.ids: self.lifecycle.transition(identity,phase); self.bus.publish("lifecycle",identity,{"phase":phase.value})
    def discover_subsystems(self) -> tuple[SubsystemAttachment,...]:
        started=perf_counter_ns()
        for path in sorted((self.root/"runtime").rglob("constitutional.py")):
            if "constitution" in path.relative_to(self.root/"runtime").parts: continue
            module=self._load_module(path,"savant_subsystem")
            attachment=module.entrypoint()
            if attachment.identity in self._subsystems: raise ValueError(f"duplicate subsystem entry point: {attachment.identity}")
            self._subsystems[attachment.identity]=attachment; attachment.discover(self)
        self._record("discovery",started); return self.subsystems
    def load_plugin(self,path: Path) -> ConstitutionalPlugin:
        plugin=self._load_module(Path(path),"savant_plugin").entrypoint()
        if not isinstance(plugin,ConstitutionalPlugin): raise TypeError("plugin entrypoint must return ConstitutionalPlugin")
        from .contributions import ConstitutionalAssertionAPI
        contribution=ConstitutionalAssertionAPI(self.registry).contribute(plugin.identity,plugin.definitions)
        self.registry=contribution.registry
        for obj in contribution.assertions:
            self.lifecycle.add(obj.id)
            for phase in (LifecyclePhase.DISCOVERED,): self.lifecycle.transition(obj.id,phase)
        if plugin.subsystem.identity in self._subsystems: raise ValueError(f"duplicate subsystem entry point: {plugin.subsystem.identity}")
        self._subsystems[plugin.subsystem.identity]=plugin.subsystem; plugin.subsystem.discover(self); return plugin
    def _load_module(self,path: Path,prefix: str):
        name=f"{prefix}_{abs(hash(str(path.resolve())))}"; spec=importlib.util.spec_from_file_location(name,path)
        if spec is None or spec.loader is None: raise ImportError(path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
    @property
    def subsystems(self): return tuple(self._subsystems[i] for i in sorted(self._subsystems))
    @property
    def capabilities(self) -> tuple[ConstitutionalCapability,...]:
        values=[]
        for service in self.registry.by_kind("service"):
            operators=tuple(sorted(o.id for o in self.registry.by_kind("operator") if any(r.get("type")=="implements" and r.get("target")==service.id for r in o.relationships)))
            values.append(ConstitutionalCapability(service.id,service.version,operators,tuple(service.dependencies)))
        return tuple(values)
    def capability(self,identity: str): return next(c for c in self.capabilities if c.identity==identity)
    def compose_capabilities(self,*identities: str) -> ConstitutionalCapability:
        selected=tuple(self.capability(i) for i in identities)
        return ConstitutionalCapability("+".join(identities),"+".join(c.version for c in selected),
            tuple(sorted({o for c in selected for o in c.operators})),tuple(sorted({d for c in selected for d in c.dependencies})))
    def validate(self):
        started=perf_counter_ns(); constitutional=ConstitutionalValidator(self.registry).validate(); migration=RuntimeMigrationValidator(self.registry,self.runtime_migration).validate()
        self._validation={"constitutional":constitutional,"migration":migration}; self._record("validation",started)
        if not constitutional["valid"] or not migration["valid"]: raise ValueError("constitutional platform validation failed")
        for subsystem in self.subsystems: subsystem.validate(self)
        return self._validation
    def project(self,target: str,object_id: str|None=None):
        started=perf_counter_ns()
        try: artifact=self.registry.project(target)
        except Exception as exc:
            identity=object_id or "reality"; self._diagnostics.append(self._diagnostic("projection_rejected",identity,str(exc))); self.bus.publish("projection.rejected",identity,{"error":str(exc)}); raise
        identities=(object_id,) if object_id else self.registry.ids
        for identity in identities:
            current=self.lifecycle.get(identity)
            if current in {LifecyclePhase.READY,LifecyclePhase.ACTIVE}: self.lifecycle.transition(identity,LifecyclePhase.PROJECTED); self.lifecycle.transition(identity,LifecyclePhase.ACTIVE)
            self.bus.publish("projection",identity,{"target":target,"digest":artifact["digest"]})
        self._record("projection",started); return artifact
    def health(self,object_id: str) -> HealthProjection:
        phase=self.lifecycle.get(object_id); reasons=[]
        state=HealthState.DEPRECATED if phase in {LifecyclePhase.DEPRECATED,LifecyclePhase.RETIRED} else HealthState.HEALTHY
        for section,result in self._validation.items():
            if not result.get("valid",False): state=HealthState.INVALID; reasons.append(f"{section} validation failed")
        return HealthProjection(object_id,state,tuple(reasons),self.registry.authority_chain(object_id))
    def diagnostics(self,object_id: str) -> tuple[Diagnostic,...]:
        return tuple(d for d in self._diagnostics if d.object_id==object_id)
    def diagnose_dependency(self,object_id: str,dependency: str,message: str):
        diagnostic=self._diagnostic("dependency_failed",object_id,message,dependency); self._diagnostics.append(diagnostic); self.bus.publish("diagnostic",object_id,{"code":diagnostic.code}); return diagnostic
    def _diagnostic(self,code: str,object_id: str,message: str,dependency: str|None=None):
        return Diagnostic(code,object_id,message,dependency,self.registry.authority_chain(object_id),self.registry.lineage_chain(object_id),self.registry.provenance_chain(object_id))
    def metrics(self) -> tuple[Metric,...]: return tuple(self._metrics)
    def traverse_dependencies(self,object_id: str):
        started=perf_counter_ns(); result=self.registry.dependency_lookup(object_id); self._record("dependency_traversal",started); return result
    def shutdown(self):
        for subsystem in reversed(self.subsystems): subsystem.shutdown(self)
        return {"shutdown":True,"subsystems":len(self.subsystems)}
    def attachment_interface(self,name: str):
        if name not in FUTURE_ATTACHMENT_POINTS: raise KeyError(name)
        return FutureSubsystemInterface


def subsystem_entrypoint(identity: str,implementation: str,version: str="1.0.0") -> SubsystemAttachment:
    return SubsystemAttachment(identity,implementation,version)
