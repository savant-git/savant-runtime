from __future__ import annotations

from collections import deque
from typing import Any, Iterable


class ConstitutionalPathResolver:
    def __init__(self, registry: Any): self.registry=registry
    def shortest(self, source: str, target: str, edge_types: Iterable[str] | None=None, *, undirected: bool=True):
        allowed=set(edge_types or ()); graph=self.registry.graph_model
        if source not in graph.nodes or target not in graph.nodes: raise KeyError(source if source not in graph.nodes else target)
        queue=deque((source,)); previous={source:None}
        while queue:
            node=queue.popleft()
            if node==target: break
            candidates=[]
            types=allowed or set(graph._forward)|set(graph._reverse)
            for kind in sorted(types):
                candidates.extend((n,kind,"forward") for n in graph._forward[kind][node])
                if undirected: candidates.extend((n,kind,"reverse") for n in graph._reverse[kind][node])
            for neighbor,kind,direction in sorted(candidates):
                if neighbor not in previous: previous[neighbor]=(node,kind,direction); queue.append(neighbor)
        if target not in previous: return ()
        result=[]; cursor=target
        while previous[cursor] is not None:
            parent,kind,direction=previous[cursor]; result.append({"source":parent,"target":cursor,"type":kind,"direction":direction}); cursor=parent
        return tuple(reversed(result))
    def constitutional(self, source: str, target: str): return self.shortest(source,target)
    def lineage(self, source: str, target: str): return self.shortest(source,target,("contains","supersedes"))
    def dependency(self, source: str, target: str): return self.shortest(source,target,("depends_on",),undirected=False)
    def relationship(self, source: str, target: str):
        reserved={"contains","supersedes","depends_on"}; kinds={e["type"] for e in self.registry.graph_model.edges}-reserved
        return self.shortest(source,target,kinds)
    def governance(self, identity: str):
        doctrine=self.registry.governing_doctrine(identity)
        return self.lineage(identity,doctrine.id) if doctrine else self.lineage(identity,"reality")
    def authority(self, identity: str): return self.lineage(identity,"reality")
    def projection(self, identity: str, target: str):
        declaring=next((i for i in reversed(self.registry.inheritance.chain(identity)) if target in self.registry.get(i).metadata.get("projection_targets",())),None)
        return self.lineage(identity,declaring) if declaring else ()
    def schema(self, identity: str, schema_id: str | None=None):
        wanted=schema_id or self.registry.schemas.schema_for_kind(self.registry.get(identity).kind).get("id")
        candidate=next((o.id for o in self.registry.values() if o.kind=="schema" and (o.id==wanted or o.canonical_name==wanted)),None)
        return self.shortest(identity,candidate) if candidate else ()
