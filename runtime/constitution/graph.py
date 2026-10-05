from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Iterable

from .object import ConstitutionalObject


class ConstitutionalGraph:
    """Unbounded typed graph with iterative traversal and deterministic export."""

    def __init__(self, objects: Iterable[ConstitutionalObject]):
        source = tuple(objects)
        self.nodes = {obj.id: obj for obj in source}
        if len(self.nodes) != len(source): raise ValueError("duplicate graph node identities")
        self.edges: list[dict[str, str]] = []
        for obj in source:
            parent = obj.lineage.get("parent")
            if parent: self.edges.append({"source": str(parent), "target": obj.id, "type": "contains"})
            self.edges.extend({"source": obj.id, "target": d, "type": "depends_on"} for d in obj.dependencies)
            self.edges.extend({"source": obj.id, "target": str(r["target"]), "type": str(r["type"])} for r in obj.relationships)
            self.edges.extend({"source": obj.id, "target": str(x), "type": "supersedes"} for x in obj.lineage.get("supersedes", ()))
        self.edges.sort(key=lambda e: (e["source"], e["type"], e["target"]))
        self._forward: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        self._reverse: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for edge in self.edges:
            if edge["source"] not in self.nodes or edge["target"] not in self.nodes: raise ValueError(f"edge references unknown node: {edge}")
            self._forward[edge["type"]][edge["source"]].append(edge["target"])
            self._reverse[edge["type"]][edge["target"]].append(edge["source"])
        self.detect_cycles("contains", raise_on_cycle=True)

    def _walk(self, starts: Iterable[str], edge_type: str, reverse: bool = False) -> tuple[str, ...]:
        adjacent = self._reverse[edge_type] if reverse else self._forward[edge_type]
        start = set(starts); seen = set(start); queue = deque(sorted(start))
        while queue:
            for target in sorted(adjacent[queue.popleft()]):
                if target not in seen: seen.add(target); queue.append(target)
        return tuple(sorted(seen - start))

    def ancestors(self, object_id: str) -> tuple[str, ...]:
        result: list[str] = []; cursor = object_id; seen = {object_id}
        while self._reverse["contains"][cursor]:
            cursor = sorted(self._reverse["contains"][cursor])[0]
            if cursor in seen: raise ValueError(f"contains cycle includes {cursor}")
            seen.add(cursor); result.append(cursor)
        return tuple(result)
    def descendants(self, object_id: str) -> tuple[str, ...]: return self._walk([object_id], "contains")
    def direct_children(self, object_id: str) -> tuple[str, ...]: return tuple(sorted(set(self._forward["contains"][object_id])))
    def orphans(self, root: str="reality") -> tuple[str, ...]:
        reachable={root,*self.descendants(root)} if root in self.nodes else set()
        return tuple(sorted(set(self.nodes)-reachable))
    def direct_dependencies(self, object_id: str) -> tuple[str, ...]: return tuple(sorted(set(self._forward["depends_on"][object_id])))
    def dependencies(self, object_id: str) -> tuple[str, ...]: return self._walk([object_id], "depends_on")
    def reverse_dependencies(self, object_id: str, transitive: bool = False) -> tuple[str, ...]:
        return self._walk([object_id], "depends_on", True) if transitive else tuple(sorted(set(self._reverse["depends_on"][object_id])))
    def relationships(self, object_id: str, relationship_type: str | None = None) -> tuple[dict[str, str], ...]:
        return tuple(e.copy() for e in self.edges if e["source"] == object_id and e["type"] not in {"contains", "depends_on"} and (relationship_type is None or e["type"] == relationship_type))

    def detect_cycles(self, edge_type: str, raise_on_cycle: bool = False) -> tuple[tuple[str, ...], ...]:
        adjacent = self._forward[edge_type]; reverse = self._reverse[edge_type]
        seen: set[str] = set(); order: list[str] = []
        for root in sorted(self.nodes):
            if root in seen: continue
            seen.add(root); stack: list[tuple[str, Any]] = [(root, iter(sorted(adjacent[root])))]
            while stack:
                node, targets = stack[-1]
                try: target = next(targets)
                except StopIteration: stack.pop(); order.append(node); continue
                if target not in seen:
                    seen.add(target); stack.append((target, iter(sorted(adjacent[target]))))
        assigned: set[str] = set(); components: list[tuple[str, ...]] = []
        for root in reversed(order):
            if root in assigned: continue
            component: set[str] = set(); stack = [root]; assigned.add(root)
            while stack:
                node = stack.pop(); component.add(node)
                for target in reverse[node]:
                    if target not in assigned: assigned.add(target); stack.append(target)
            if len(component) > 1 or root in adjacent[root]: components.append(tuple(sorted(component)))
        cycles = tuple(sorted(components))
        if cycles and raise_on_cycle: raise ValueError(f"{edge_type} cycle includes {', '.join(cycles[0])}")
        return cycles

    def export(self) -> dict[str, Any]:
        return {"nodes": [{"id": o.id, "kind": o.kind} for o in sorted(self.nodes.values(), key=lambda x: x.id)], "edges": [e.copy() for e in self.edges], "visualization_hooks": {"node_kind":"kind","edge_kind":"type","dependency_cycles":self.detect_cycles("depends_on")}}
