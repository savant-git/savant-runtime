from __future__ import annotations
from typing import Any, Mapping

class AuthorityValidationError(ValueError): pass

class AuthorityResolver:
    def __init__(self, registry: Any): self.registry = registry
    def chain(self, object_id: str) -> tuple[Mapping[str, Any], ...]:
        lineage = tuple(reversed(self.registry.find_ancestors(object_id))) + (object_id,)
        return tuple(self.registry.get(item_id).authority for item_id in lineage if self.registry.get(item_id).authority)
    def effective(self, object_id: str) -> Mapping[str, Any]:
        result: dict[str, Any] = {}
        for authority in self.chain(object_id): result.update(authority)
        return result
    def validate(self, object_id: str) -> None:
        chain = self.chain(object_id)
        if not chain or not all(isinstance(a, Mapping) and a for a in chain): raise AuthorityValidationError(f"invalid authority chain: {object_id}")
    def trace(self, object_id: str) -> dict[str, Any]:
        return {"object_id":object_id,"chain":[dict(a) for a in self.chain(object_id)],"effective":dict(self.effective(object_id))}
