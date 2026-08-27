from __future__ import annotations
from collections import defaultdict
from typing import Any, Callable, Mapping

EXTENSION_POINTS = ("kind","schema","validator","projection","relationship","doctrine","faculty","service","operator")

class ConstitutionalExtensions:
    """Compositional extension API; registrations are data or callables, never subclasses."""
    def __init__(self): self._items: dict[str, dict[str, Any]] = defaultdict(dict)
    def register(self, point: str, identity: str, extension: Any) -> None:
        if point not in EXTENSION_POINTS: raise ValueError(f"unknown extension point: {point}")
        if identity in self._items[point]: raise ValueError(f"duplicate {point}: {identity}")
        self._items[point][identity] = extension
    def discover(self, point: str) -> tuple[Any, ...]: return tuple(self._items[point][i] for i in sorted(self._items[point]))
    def register_kind(self, identity: str, value: Mapping[str, Any]): self.register("kind", identity, value)
    def register_schema(self, identity: str, value: Mapping[str, Any]): self.register("schema", identity, value)
    def register_validator(self, identity: str, value: Callable): self.register("validator", identity, value)
    def register_projection(self, identity: str, value: Callable): self.register("projection", identity, value)
    def register_relationship(self, identity: str, value: Mapping[str, Any]): self.register("relationship", identity, value)
    def register_doctrine(self, identity: str, value: Mapping[str, Any]): self.register("doctrine", identity, value)
    def register_faculty(self, identity: str, value: Mapping[str, Any]): self.register("faculty", identity, value)
    def register_service(self, identity: str, value: Mapping[str, Any]): self.register("service", identity, value)
    def register_operator(self, identity: str, value: Mapping[str, Any]): self.register("operator", identity, value)
