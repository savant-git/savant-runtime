from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable

class IdentityCollisionError(ValueError): pass

@dataclass(frozen=True)
class IdentityMigration:
    source: str
    canonical: str
    reason: str

class CanonicalIdentityResolver:
    def __init__(self, objects: Iterable[Any]):
        self._canonical: dict[str, str] = {}; self._migrations: list[IdentityMigration] = []
        for obj in objects:
            self._claim(obj.id, obj.id)
            metadata = obj.to_primitives()["metadata"]
            for alias in metadata.get("aliases", ()): self._claim(str(alias), obj.id)
            for old in metadata.get("historical_names", ()): self._claim(str(old), obj.id)
            for old in obj.lineage.get("supersedes", ()): self._claim(str(old), obj.id, True)
    def _claim(self, name: str, canonical: str, superseded: bool = False) -> None:
        existing = self._canonical.get(name)
        if existing and existing != canonical and not superseded: raise IdentityCollisionError(f"identity collision: {name} resolves to {existing} and {canonical}")
        self._canonical[name] = canonical
    def resolve(self, identity: str) -> str:
        if identity not in self._canonical: raise KeyError(identity)
        return self._canonical[identity]
    def migrate(self, identity: str, reason: str = "canonicalization") -> IdentityMigration:
        migration = IdentityMigration(identity, self.resolve(identity), reason); self._migrations.append(migration); return migration
    @property
    def migrations(self) -> tuple[IdentityMigration, ...]: return tuple(self._migrations)
