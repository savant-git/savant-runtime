from __future__ import annotations

from hashlib import sha256
import importlib
import json
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from .graph import ConstitutionalGraph


def canonical_json(value: Any) -> str: return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ProjectionContext:
    target: str
    options: Mapping[str, Any] = field(default_factory=dict)
    authority_chain: tuple[Mapping[str, Any], ...] = ()
    depth: int = 0


@dataclass(frozen=True)
class ProjectionArtifact:
    target: str
    payload: Any
    digest: str
    authority_chain: tuple[Mapping[str, Any], ...]
    source_ids: tuple[str, ...]
    children: tuple["ProjectionArtifact", ...] = ()

    def to_mapping(self) -> dict[str, Any]:
        return {"target": self.target, "payload": self.payload, "digest": self.digest,
                "authority_chain": [dict(a) for a in self.authority_chain], "source_ids": list(self.source_ids),
                "children": [child.to_mapping() for child in self.children]}


class ProjectionPluginRegistry:
    def __init__(self):
        self._plugins: dict[str, Callable[[list[dict[str, Any]], dict[str, Any]], Any]] = {}
    @classmethod
    def discover(cls) -> "ProjectionPluginRegistry":
        result = cls(); package = importlib.import_module("runtime.constitution.projections")
        for info in sorted(pkgutil.iter_modules(package.__path__), key=lambda x: x.name):
            module = importlib.import_module(f"{package.__name__}.{info.name}")
            for target, plugin in getattr(module, "PLUGINS", {}).items(): result.register(target, plugin)
        return result
    def register(self, target: str, plugin: Callable) -> None:
        if target in self._plugins: raise ValueError(f"projection target already registered: {target}")
        self._plugins[target] = plugin
    @property
    def targets(self) -> tuple[str, ...]: return tuple(sorted(self._plugins))
    def get(self, target: str) -> Callable: return self._plugins[target]


PROJECTION_TARGETS = ProjectionPluginRegistry.discover().targets


class ProjectionCache:
    """Non-authoritative memoization; entries are keyed by constitutional digest."""
    INVALIDATION_EVENTS = frozenset({"schema", "authority", "version", "lineage", "provenance", "relationship"})
    def __init__(self): self._values: dict[tuple[Any, ...], ProjectionArtifact] = {}; self._generation=0
    def get(self, key): return self._values.get((self._generation, *key))
    def put(self, key, value): self._values[(self._generation, *key)]=value; return value
    def invalidate(self, reason: str) -> None:
        if reason not in self.INVALIDATION_EVENTS: raise ValueError(f"unknown projection invalidation reason: {reason}")
        self._generation += 1; self._values.clear()
    @property
    def size(self): return len(self._values)


class ProjectionEngine:
    """Pure deterministic, discoverable projections that cannot mutate authority."""
    def __init__(self, registry: Any, plugins: ProjectionPluginRegistry | None = None, cache: ProjectionCache | None = None):
        self.registry = registry; self.plugins = plugins or ProjectionPluginRegistry.discover(); self.cache=cache or getattr(registry,"projection_cache",ProjectionCache())
    def project_artifact(self, target: str, context: ProjectionContext | None = None,
                         chained: Iterable[str] = ()) -> ProjectionArtifact:
        if target not in self.plugins.targets: raise ValueError(f"unknown projection target: {target}")
        before = canonical_json([o.to_primitives() for o in self.registry.values()])
        chained=tuple(chained); key=(target,canonical_json(dict((context or ProjectionContext(target)).options)),chained,sha256(before.encode()).hexdigest())
        cached=self.cache.get(key)
        if cached is not None: return cached
        objects = [self.registry.get(i).to_primitives() for i in self.registry.ids]
        graph = ConstitutionalGraph(self.registry.values()).export()
        authorities = [dict(self.registry.authority_chain(i)[-1]) for i in self.registry.ids if self.registry.authority_chain(i)]
        unique = {canonical_json(a): a for a in authorities}
        authority_chain = tuple(unique[k] for k in sorted(unique))
        ctx = context or ProjectionContext(target, authority_chain=authority_chain)
        payload = self.plugins.get(target)(objects, graph)
        children = tuple(self.project_artifact(child, ProjectionContext(child, ctx.options, ctx.authority_chain, ctx.depth + 1)) for child in chained)
        basis = {"target":target,"payload":payload,"authority_chain":authority_chain,"source_ids":list(self.registry.ids),"children":[c.to_mapping() for c in children]}
        artifact = ProjectionArtifact(target, payload, sha256(canonical_json(basis).encode()).hexdigest(), authority_chain, self.registry.ids, children)
        if before != canonical_json([o.to_primitives() for o in self.registry.values()]): raise RuntimeError("projection mutated authority")
        return self.cache.put(key,artifact)

    def project(self, target: str, context: ProjectionContext | None = None,
                chained: Iterable[str] = ()) -> dict[str, Any]:
        return self.project_artifact(target, context, chained).to_mapping()
