from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .events import ConstitutionalEvent


class TemporalConstitution:
    """Pure event replay over immutable snapshots; replay never mutates the catalog."""
    def __init__(self, events: Iterable[ConstitutionalEvent], initial: Iterable[Any]=()):
        self.events=tuple(events); self.initial={o.id:o.to_primitives() for o in initial}
    def _selected(self, *, sequence: int|None=None, occurred_at: str|None=None, version: str|None=None):
        events=self.events
        if sequence is not None: events=tuple(e for e in events if e.sequence<=sequence)
        if occurred_at is not None: events=tuple(e for e in events if e.occurred_at<=occurred_at)
        if version is not None:
            positions=[e.sequence for e in events if e.version==version]
            events=tuple(e for e in events if positions and e.sequence<=max(positions))
        return events
    def reconstruct(self, object_id: str, *, sequence: int|None=None, occurred_at: str|None=None, version: str|None=None):
        state=deepcopy(self.initial.get(object_id)); history=[]
        for event in self._selected(sequence=sequence,occurred_at=occurred_at,version=version):
            if event.object_id!=object_id: continue
            mapping=event.to_mapping(); evidence=mapping["evidence"]; history.append(mapping)
            if "state" in evidence: state=deepcopy(dict(evidence["state"]))
            if state is None: state={"id":object_id}
            for field,value in dict(evidence.get("changes",{})).items(): state[field]=deepcopy(value)
            if "field" in evidence: state[str(evidence["field"])]=deepcopy(evidence.get("value"))
            if event.type=="ObjectSuperseded": state.setdefault("lineage",{}).setdefault("superseded_by",[]).append(evidence.get("by"))
            elif event.type=="RelationshipAdded": state.setdefault("relationships",[]).append(deepcopy(evidence.get("relationship")))
            elif event.type=="RelationshipRemoved": state["relationships"]=[r for r in state.get("relationships",[]) if r!=evidence.get("relationship")]
            elif event.type=="AuthorityChanged": state["authority"]=deepcopy(evidence.get("authority",evidence.get("value",{})))
            elif event.type=="SchemaChanged": state.setdefault("metadata",{})["schema"]=evidence.get("schema")
        return {"object_id":object_id,"state":state,"events":tuple(history),"sequence":history[-1]["sequence"] if history else 0}
    def at_sequence(self,object_id: str,sequence: int): return self.reconstruct(object_id,sequence=sequence)
    def at_time(self,object_id: str,occurred_at: str): return self.reconstruct(object_id,occurred_at=occurred_at)
    def at_version(self,object_id: str,version: str): return self.reconstruct(object_id,version=version)
    def lineage(self,object_id: str,**point): return (self.reconstruct(object_id,**point)["state"] or {}).get("lineage")
    def authority(self,object_id: str,**point): return (self.reconstruct(object_id,**point)["state"] or {}).get("authority")
    def relationships(self,object_id: str,**point): return (self.reconstruct(object_id,**point)["state"] or {}).get("relationships",[])
    def dependencies(self,object_id: str,**point): return (self.reconstruct(object_id,**point)["state"] or {}).get("dependencies",[])
    def schema(self,object_id: str,**point): return (self.reconstruct(object_id,**point)["state"] or {}).get("metadata",{}).get("schema")
