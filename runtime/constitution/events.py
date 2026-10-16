from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .projection import canonical_json


EVENT_TYPES=("ObjectCreated","ObjectSuperseded","ObjectMigrated","SchemaChanged","RelationshipAdded",
             "RelationshipRemoved","AuthorityChanged","ProjectionGenerated","ValidationSucceeded","ValidationFailed",
             "object_created","object_updated","object_projected","schema_validated","relationship_added",
             "dependency_added","lineage_updated","provenance_updated")


def _freeze(value: Any) -> Any:
    if isinstance(value,Mapping): return MappingProxyType({str(k):_freeze(v) for k,v in value.items()})
    if isinstance(value,(tuple,list)): return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value,Mapping): return {k:_thaw(v) for k,v in value.items()}
    if isinstance(value,tuple): return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True,slots=True)
class ConstitutionalEvent:
    sequence: int
    type: str
    object_id: str
    occurred_at: str
    evidence: Mapping[str,Any]
    version: str | None=None
    digest: str=""
    def __post_init__(self):
        if self.type not in EVENT_TYPES: raise ValueError(f"unknown constitutional event: {self.type}")
        object.__setattr__(self,"evidence",_freeze(self.evidence))
        basis={"sequence":self.sequence,"type":self.type,"object_id":self.object_id,"occurred_at":self.occurred_at,
               "evidence":_thaw(self.evidence),"version":self.version}
        expected=sha256(canonical_json(basis).encode()).hexdigest()
        if self.digest and self.digest!=expected: raise ValueError("constitutional event digest mismatch")
        object.__setattr__(self,"digest",expected)
    def to_mapping(self):
        return {"sequence":self.sequence,"type":self.type,"object_id":self.object_id,"occurred_at":self.occurred_at,
                "evidence":_thaw(self.evidence),"version":self.version,"digest":self.digest}


class ConstitutionalEventLog:
    def __init__(self, events: Iterable[ConstitutionalEvent]=()):
        self._events=tuple(events); self._validate()
    def _validate(self):
        if tuple(e.sequence for e in self._events)!=tuple(range(1,len(self._events)+1)): raise ValueError("event sequence is not contiguous")
    def append(self,event_type: str,object_id: str,occurred_at: str,evidence: Mapping[str,Any]|None=None,
               version: str|None=None) -> ConstitutionalEvent:
        event=ConstitutionalEvent(len(self._events)+1,event_type,object_id,occurred_at,evidence or {},version)
        self._events=(*self._events,event); return event
    def evolved(self,event_type: str,object_id: str,occurred_at: str,evidence: Mapping[str,Any]|None=None,
                version: str|None=None) -> "ConstitutionalEventLog":
        event=ConstitutionalEvent(len(self._events)+1,event_type,object_id,occurred_at,evidence or {},version)
        return ConstitutionalEventLog((*self._events,event))
    def events(self,object_id: str|None=None): return tuple(e for e in self._events if object_id is None or e.object_id==object_id)
    def verify(self): return all(ConstitutionalEvent(**e.to_mapping()).digest==e.digest for e in self._events)
