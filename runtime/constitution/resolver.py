from __future__ import annotations

from typing import Any


class ConstitutionalResolver:
    """Single deterministic query surface over constitutional authority."""

    _CRITERIA = {"id", "kind", "authority", "parent", "children", "relationship",
                 "dependency", "schema", "version", "status", "domain", "metadata"}

    def __init__(self, registry: Any):
        self.registry = registry

    def lookup(self, criterion: str | None = None, value: Any = None, **query: Any) -> Any:
        if criterion is not None:
            if query: raise TypeError("use a criterion or one named query")
            query = {criterion: value}
        if len(query) != 1: raise TypeError("lookup requires exactly one criterion")
        name, expected = next(iter(query.items()))
        if name not in self._CRITERIA: raise KeyError(name)
        if name == "id": return self.registry.get(str(expected))
        if name == "kind": return self.registry.by_kind(str(expected))
        if name == "authority": return self.registry.find_by_authority(expected)
        if name == "parent": return tuple(self.registry.get(i) for i in self.registry.graph_model.direct_children(str(expected)))
        if name == "children": return tuple(self.registry.get(i) for i in self.registry.graph_model.direct_children(str(expected)))
        if name == "relationship": return self.registry.find_by_relationship(str(expected))
        if name == "dependency": return tuple(o for o in self.registry.values() if str(expected) in self.registry.dependencies.direct(o.id))
        if name == "schema":
            if str(expected) in self.registry.schemas.ids: return self.registry.schemas.get(str(expected))
            return tuple(o for o in self.registry.values() if self.registry.schemas.schema_for_kind(o.kind).get("id") == expected)
        if name == "version": return self.registry.by_version(str(expected))
        if name == "status": return tuple(o for o in self.registry.values() if o.status == expected)
        if name == "domain":
            domain = str(expected); prefix = domain if domain.startswith("domain:") else f"domain:{domain}"
            return tuple(o for o in self.registry.values() if o.id == prefix or prefix in self.registry.graph_model.ancestors(o.id))
        key, separator, metadata_value = str(expected).partition("=")
        return tuple(o for o in self.registry.values() if key in o.metadata and (not separator or str(o.metadata[key]) == metadata_value))

    def __call__(self, criterion: str, value: Any) -> Any:
        return self.lookup(criterion, value)
