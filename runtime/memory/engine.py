from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any,Iterable,Mapping

from runtime.constitution import ConstitutionalEvent,ConstitutionalObject,ConstitutionalRegistry
from runtime.constitution.projection import canonical_json
from runtime.fluid_canon import FluidCanonEngine
from .model import CANONICAL_MEMORY_TYPES,service_assertion

class MemoryValidationError(ValueError): pass

class MemoryEngine:
    """No memory store: all results are regenerated from a constitutional snapshot."""
    def __init__(self,canon: FluidCanonEngine): self.canon=canon; self.registry=canon.registry
    @classmethod
    def install(cls,registry: ConstitutionalRegistry,timestamp: str="2026-07-21T00:00:00Z"):
        canon=FluidCanonEngine.install(registry,timestamp)
        if "service:memory" not in canon.registry.ids:
            registry=canon.registry.contribute("engine:memory",(service_assertion(timestamp),)).registry
            canon=FluidCanonEngine(registry)
        return cls(canon)
    def contribute(self,memories: Iterable[ConstitutionalObject]):
        values=tuple(memories)
        if any(obj.metadata.get("memory_type") not in CANONICAL_MEMORY_TYPES for obj in values):
            raise MemoryValidationError("Memory accepts canonical memory assertions only")
        try: engine=type(self)(self.canon.contribute(values))
        except ValueError as exc: raise MemoryValidationError(str(exc)) from exc
        report=engine.validate()
        if not report["valid"]: raise MemoryValidationError(str(report["checks"]))
        return engine
    def memories(self,memory_type: str|None=None,*,at: str|None=None,current: bool=False):
        source=self.canon.historical_truth(at=at) if current else self.canon.assertions(at=at)
        values=[o for o in source if o.metadata.get("memory_type") in CANONICAL_MEMORY_TYPES
                and (memory_type is None or o.metadata.get("memory_type")==memory_type) and self._valid_at(o,at)]
        return tuple(values)
    @staticmethod
    def _valid_at(obj: ConstitutionalObject,at: str|None):
        if at is None: return True
        validity=obj.metadata.get("memory_validity",{}); start=validity.get("from"); end=validity.get("until")
        return (not start or start<=at) and (not end or at<=end)
    def project(self,identity: str):
        obj=self.registry.get_exact(identity)
        if obj.metadata.get("memory_type") not in CANONICAL_MEMORY_TYPES: raise KeyError(identity)
        return {"identity":obj.id,"memory_type":obj.metadata["memory_type"],"content":obj.metadata.get("claim"),
            "authority":dict(self.registry.inherited_authority(obj.id)),"lineage":self.registry.lineage_lookup(obj.id),
            "provenance":obj.to_primitives()["provenance"],"relationships":tuple(dict(r) for r in obj.relationships),
            "dependencies":tuple(obj.dependencies),"validity":dict(obj.metadata.get("memory_validity",{})),
            "confidence":obj.metadata.get("memory_confidence"),"supersession":{"supersedes":tuple(obj.lineage.get("supersedes",())),
            "superseded_by":tuple(o.id for o in self.canon.who_superseded(obj.id))}}
    @staticmethod
    def _tokens(value: Any): return frozenset(re.findall(r"[\w]+",canonical_json(value).casefold()))
    def retrieve_semantic(self,query: Any,*,limit: int=10,memory_type: str|None=None,at: str|None=None):
        wanted=self._tokens(query); matches=[]
        for obj in self.memories(memory_type,at=at,current=True):
            tokens=self._tokens({"subject":obj.metadata.get("subject"),"content":obj.metadata.get("claim")})
            score=len(wanted&tokens)/len(wanted|tokens) if wanted or tokens else 1.0
            if score: matches.append((score,obj.id))
        selected=sorted(matches,key=lambda x:(-x[0],x[1]))[:max(0,limit)]
        return tuple({"identity":identity,"score":score,"memory":self.project(identity)} for score,identity in selected)
    def retrieve_relationships(self,identity: str,relationship_type: str|None=None):
        edges=self.registry.graph_model.edges; ids={e["target"] for e in edges if e["source"]==identity and (relationship_type is None or e["type"]==relationship_type)}
        ids.update(e["source"] for e in edges if e["target"]==identity and (relationship_type is None or e["type"]==relationship_type))
        return tuple(self.registry.get_exact(i) for i in sorted(ids) if i in self.registry.ids and self.registry.get_exact(i).metadata.get("memory_type") in CANONICAL_MEMORY_TYPES)
    def retrieve_authority(self,authority: Mapping[str,Any]|str):
        needle=canonical_json(authority) if not isinstance(authority,str) else authority
        return tuple(o for o in self.memories() if (canonical_json(self.registry.inherited_authority(o.id))==needle if not isinstance(authority,str)
            else needle in canonical_json(self.registry.inherited_authority(o.id))))
    def retrieve_timeline(self,*,start: str|None=None,end: str|None=None,memory_type: str|None=None):
        values=(o for o in self.memories(memory_type) if (not start or o.created_at>=start) and (not end or o.created_at<=end))
        return tuple(sorted(values,key=lambda o:(o.created_at,o.id)))
    def retrieve_dependency(self,identity: str,*,transitive: bool=True):
        return tuple(o for o in self.memories() if identity in (self.registry.dependencies.transitive(o.id) if transitive else self.registry.dependencies.direct(o.id)))
    def retrieve_kindred(self,*identities: str):
        wanted={str(i) for i in identities}
        return tuple(o for o in self.memories() if wanted.intersection(str(v) for v in o.metadata.get("kindred",())))
    def project_event(self,event: ConstitutionalEvent):
        constitutional=self.registry.reflect(event.object_id) if event.object_id in self.registry.ids else None
        return MappingProxyType({"memory_type":"episodic","transient":True,"event":event.to_mapping(),"constitutional":constitutional})
    def working_memory(self,identities: Iterable[str]=(),events: Iterable[ConstitutionalEvent]=()):
        items=tuple(MappingProxyType(self.project(i)) for i in sorted(set(identities)))
        event_items=tuple(self.project_event(e) for e in sorted(events,key=lambda e:e.sequence))
        return MappingProxyType({"memory_type":"working","transient":True,"items":items,"events":event_items})
    def validate(self):
        checks={"authority":[],"lineage":[],"provenance":[],"validity":[],"confidence":[],"references":[]}; ids=set(self.registry.ids)
        for obj in self.memories():
            if not self.registry.inherited_authority(obj.id): checks["authority"].append(obj.id)
            if obj.lineage.get("parent") not in ids: checks["lineage"].append(obj.id)
            if not obj.provenance.get("sources") or not obj.provenance.get("asserted_by"): checks["provenance"].append(obj.id)
            validity=obj.metadata.get("memory_validity",{}); start=validity.get("from"); end=validity.get("until")
            if start and end and start>end: checks["validity"].append(obj.id)
            confidence=obj.metadata.get("memory_confidence")
            if not isinstance(confidence,(int,float)) or not 0<=confidence<=1: checks["confidence"].append(obj.id)
            for relation in obj.relationships:
                if relation.get("target") not in ids: checks["references"].append({"id":obj.id,"target":relation.get("target")})
        return {"valid":not any(checks.values()),"checks":checks,"memory_count":len(self.memories())}
