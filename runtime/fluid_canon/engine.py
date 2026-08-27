from __future__ import annotations

from collections import deque
from typing import Iterable

from runtime.constitution import ConstitutionalObject, ConstitutionalRegistry
from .model import ASSERTION_TYPES, service_assertion

class FluidCanonValidationError(ValueError): pass

class FluidCanonEngine:
    """Stateless canon queries over a constitutional registry snapshot."""
    def __init__(self,registry: ConstitutionalRegistry): self.registry=registry
    @classmethod
    def install(cls,registry: ConstitutionalRegistry,timestamp: str="2026-07-21T00:00:00Z"):
        if "service:fluid-canon" in registry.ids: return cls(registry)
        return cls(registry.contribute("engine:fluid-canon",(service_assertion(timestamp),)).registry)
    def contribute(self,assertions: Iterable[ConstitutionalObject]):
        values=tuple(assertions); self._validate_batch(values)
        try: engine=type(self)(self.registry.contribute("engine:fluid-canon",values).registry)
        except ValueError as exc: raise FluidCanonValidationError(str(exc)) from exc
        report=engine.validate()
        if not report["valid"]: raise FluidCanonValidationError(str(report["checks"]))
        return engine
    def _validate_batch(self,values):
        if any(obj.metadata.get("engine")!="fluid-canon" or obj.metadata.get("assertion_type") not in ASSERTION_TYPES for obj in values):
            raise FluidCanonValidationError("Fluid Canon accepts typed constitutional assertions only")
        objects=(*self.assertions(),*values); nodes={o.id for o in objects}; adjacency={i:set() for i in nodes}; indegree={i:0 for i in nodes}
        for obj in objects:
            for target in obj.lineage.get("supersedes",()):
                target=str(target)
                if target in nodes and target not in adjacency[obj.id]: adjacency[obj.id].add(target); indegree[target]+=1
        queue=deque(sorted(i for i in nodes if indegree[i]==0)); visited=0
        while queue:
            current=queue.popleft(); visited+=1
            for target in sorted(adjacency[current]):
                indegree[target]-=1
                if indegree[target]==0: queue.append(target)
        if visited!=len(nodes): raise FluidCanonValidationError("supersession cycle")
    def assertions(self,subject: str|None=None,*,at: str|None=None,version: str|None=None):
        values=[]
        for obj in self.registry.values():
            if obj.metadata.get("engine")!="fluid-canon" or "assertion_type" not in obj.metadata: continue
            if subject is not None and obj.metadata.get("subject")!=subject: continue
            if at is not None and obj.created_at>at: continue
            if version is not None and self._version_key(obj.version)>self._version_key(version): continue
            values.append(obj)
        return tuple(values)
    @staticmethod
    def _version_key(value: str):
        parts=str(value).split(".")
        return (0,*(int(p) for p in parts)) if parts and all(p.isdigit() for p in parts) else (1,str(value))
    def current_truth(self,subject: str|None=None): return self.historical_truth(subject)
    def historical_truth(self,subject: str|None=None,*,at: str|None=None,version: str|None=None):
        eligible=self.assertions(subject,at=at,version=version); ids={o.id for o in eligible}
        superseded={str(old) for obj in eligible for old in obj.lineage.get("supersedes",()) if str(old) in ids}
        return tuple(obj for obj in eligible if obj.id not in superseded)
    def why(self,identity: str):
        obj=self._assertion(identity)
        return {"identity":obj.id,"type":obj.metadata["assertion_type"],"subject":obj.metadata["subject"],
                "claim":obj.metadata.get("claim"),"asserted_by":self.who_asserted(identity),
                "evidence":tuple(o.id for o in self.evidence_chain(identity)),"conflicts":tuple(o.id for o in self.conflict_chain(identity)),
                "supersedes":tuple(obj.lineage.get("supersedes",())),"superseded_by":tuple(o.id for o in self.who_superseded(identity)),
                "authority_chain":tuple(dict(a) for a in self.authority_chain(identity)),"provenance":obj.to_primitives()["provenance"]}
    def who_asserted(self,identity: str):
        provenance=self._assertion(identity).provenance
        return provenance.get("asserted_by",provenance.get("created_by"))
    def who_superseded(self,identity: str):
        ids=self.registry.graph_model._walk((identity,),"supersedes",True)
        return tuple(self.registry.get_exact(i) for i in ids if self.registry.get_exact(i).metadata.get("engine")=="fluid-canon")
    def evidence_chain(self,identity: str): return self._relationship_chain(identity,{"evidence"},{"derived_from"})
    def conflict_chain(self,identity: str): return self._relationship_chain(identity,{"conflict","resolves"},{"references"},True)
    def authority_chain(self,identity: str): return self.registry.authority_chain(self._assertion(identity).id)
    def _relationship_chain(self,identity: str,roles: set[str],types: set[str],undirected: bool=False):
        self._assertion(identity); seen={identity}; queue=deque((identity,)); result=[]
        while queue:
            current=queue.popleft(); candidates=[]
            for relation in self.registry.get_exact(current).relationships:
                if relation.get("type") in types and relation.get("role") in roles: candidates.append(str(relation["target"]))
            if undirected:
                for obj in self.assertions():
                    if any(r.get("target")==current and r.get("type") in types and r.get("role") in roles for r in obj.relationships): candidates.append(obj.id)
            for target in sorted(set(candidates)):
                if target not in seen: seen.add(target); result.append(self.registry.get_exact(target)); queue.append(target)
        return tuple(result)
    def _assertion(self,identity: str):
        obj=self.registry.get_exact(identity)
        if obj.metadata.get("engine")!="fluid-canon" or "assertion_type" not in obj.metadata: raise KeyError(identity)
        return obj
    def validate(self):
        checks={"orphans":[],"authority_gaps":[],"supersession_cycles":[],"invalid_evidence":[],"broken_provenance":[]}
        ids=set(self.registry.ids); assertions=self.assertions()
        for obj in assertions:
            parent=obj.lineage.get("parent")
            if not parent or parent not in ids: checks["orphans"].append(obj.id)
            if not self.registry.inherited_authority(obj.id): checks["authority_gaps"].append(obj.id)
            if not obj.provenance.get("sources") or not obj.provenance.get("asserted_by"): checks["broken_provenance"].append(obj.id)
            for relation in obj.relationships:
                if relation.get("role")=="evidence":
                    target=str(relation.get("target"))
                    if target not in ids or self.registry.get_exact(target).metadata.get("assertion_type") not in {"Evidence","Source"}:
                        checks["invalid_evidence"].append({"id":obj.id,"target":target})
        involved={o.id for o in assertions}
        checks["supersession_cycles"]=[cycle for cycle in self.registry.graph_model.detect_cycles("supersedes") if set(cycle)<=involved]
        return {"valid":not any(checks.values()),"checks":checks,"assertion_count":len(assertions)}
