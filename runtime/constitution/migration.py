from __future__ import annotations

import ast
import importlib.metadata
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
from collections import Counter

from .object import ConstitutionalObject

MIGRATION_VERSION = "1.0.0"
MIGRATION_TIMESTAMP = "2026-07-21T00:00:00Z"


@dataclass(frozen=True)
class RuntimeDescriptor:
    identity: str
    kind: str
    module: str
    qualname: str | None
    source: str
    dependencies: tuple[str, ...]
    owner: str | None
    fingerprint: str


@dataclass(frozen=True)
class RuntimeMigration:
    descriptors: tuple[RuntimeDescriptor, ...]
    objects: tuple[ConstitutionalObject, ...]
    source_files: tuple[str, ...]
    parse_errors: tuple[dict[str, str], ...]

    @property
    def reversible(self) -> bool:
        return not self.parse_errors and all(o.metadata.get("runtime_source") for o in self.objects)


class RuntimeMigrationPluginRegistry:
    """Composable entry-point discovery for future non-Python runtime surfaces."""
    def __init__(self): self._plugins: dict[str, Any] = {}
    @classmethod
    def discover(cls) -> "RuntimeMigrationPluginRegistry":
        result = cls()
        points = importlib.metadata.entry_points()
        for point in sorted(points.select(group="savant.constitution.runtime"), key=lambda p:p.name):
            result.register(point.name, point.load())
        return result
    def register(self, name: str, plugin: Any) -> None:
        if name in self._plugins: raise ValueError(f"runtime migration plugin already registered: {name}")
        if not callable(plugin): raise TypeError(f"runtime migration plugin is not callable: {name}")
        self._plugins[name] = plugin
    def descriptors(self, root: Path, authority: tuple[ConstitutionalObject, ...]) -> tuple[RuntimeDescriptor, ...]:
        return tuple(item for name in sorted(self._plugins) for item in self._plugins[name](root, authority))


def _module_name(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _owner_for(path: str, authority: Iterable[ConstitutionalObject]) -> str | None:
    matches: list[tuple[int, str]] = []
    for obj in authority:
        for raw in obj.metadata.get("implementation_refs", ()):
            ref = str(raw).rstrip("/")
            if path == ref or path.startswith(ref + "/") or (ref.endswith(".py") and path == ref):
                matches.append((len(ref), obj.id))
    return max(matches)[1] if matches else None


def discover_runtime(root: Path, authority: Iterable[ConstitutionalObject],
                     plugins: RuntimeMigrationPluginRegistry | None = None) -> RuntimeMigration:
    runtime_root = root / "runtime"
    paths = tuple(sorted(p for p in runtime_root.rglob("*.py") if "__pycache__" not in p.parts))
    module_ids = {_module_name(root, p): f"runtime:module:{_module_name(root, p)}" for p in paths}
    descriptors: list[RuntimeDescriptor] = []; errors: list[dict[str, str]] = []
    authority_objects = tuple(authority)
    for path in paths:
        relative = path.relative_to(root).as_posix(); module = _module_name(root, path)
        try: tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append({"source":relative,"error":str(exc)}); continue
        dependencies = sorted({module_ids[name] for node in ast.walk(tree)
                               for name in _import_names(node, module, path.name == "__init__.py") if name in module_ids})
        content = path.read_bytes(); owner = _owner_for(relative, authority_objects)
        descriptors.append(RuntimeDescriptor(module_ids[module], "instance", module, None, relative, tuple(dependencies), owner, sha256(content).hexdigest()))
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                identity = f"runtime:operator:{module}.{node.name}"
                descriptors.append(RuntimeDescriptor(identity,"operator",module,node.name,relative,(module_ids[module],),owner,sha256(f"{sha256(content).hexdigest()}:{node.name}".encode()).hexdigest()))
    descriptors.extend((plugins or RuntimeMigrationPluginRegistry.discover()).descriptors(root, authority_objects))
    identities = [d.identity for d in descriptors]
    if len(set(identities)) != len(identities): raise ValueError("runtime discovery identity collision")
    objects = tuple(_to_object(d) for d in sorted(descriptors, key=lambda d:d.identity))
    return RuntimeMigration(tuple(sorted(descriptors,key=lambda d:d.identity)), objects, tuple(p.relative_to(root).as_posix() for p in paths), tuple(errors))


def _import_names(node: ast.AST, current_module: str, is_package: bool) -> tuple[str, ...]:
    if isinstance(node, ast.Import): return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        if not node.level: return (node.module,) if node.module else ()
        package = current_module.split(".") if is_package else current_module.split(".")[:-1]
        ascend = node.level - 1
        base = package[:len(package)-ascend] if ascend <= len(package) else []
        if node.module: return (".".join((*base, *node.module.split("."))),)
        return tuple(".".join((*base, alias.name)) for alias in node.names)
    return ()


def _to_object(descriptor: RuntimeDescriptor) -> ConstitutionalObject:
    parent = "domain:instances" if descriptor.kind == "instance" else "domain:operators"
    relationships = ([{"type":"derived_from","target":descriptor.owner}] if descriptor.owner else [])
    return ConstitutionalObject.from_mapping({
        "id":descriptor.identity,"kind":descriptor.kind,"canonical_name":descriptor.module if descriptor.qualname is None else f"{descriptor.module}.{descriptor.qualname}",
        "display_name":descriptor.qualname or descriptor.module,"description":f"Discovered runtime {descriptor.kind} adapter for {descriptor.source}.",
        "authority":{"source":"runtime-source","mode":"constitutional-adapter"},"status":"active","version":MIGRATION_VERSION,
        "created_at":MIGRATION_TIMESTAMP,"updated_at":MIGRATION_TIMESTAMP,
        "lineage":{"parent":parent,"supersedes":[],"superseded_by":[]},
        "provenance":{"sources":[descriptor.source],"migration":"runtime-discovery-v1"},
        "relationships":relationships,"dependencies":list(descriptor.dependencies),
        "metadata":{"implementation_refs":[descriptor.source],"runtime_source":descriptor.source,"runtime_module":descriptor.module,
                    "runtime_qualname":descriptor.qualname,"runtime_fingerprint":descriptor.fingerprint,"projection_targets":["runtime","graph","documentation","json","yaml","schema","validation"]},
    })


def migration_report(registry: Any, migration: RuntimeMigration) -> dict[str, Any]:
    registered = set(registry.ids); migrated = {o.id for o in migration.objects}
    duplicate = sorted({d.identity for d in migration.descriptors if sum(x.identity == d.identity for x in migration.descriptors) > 1})
    missing = lambda field: sorted(o.id for o in migration.objects if not getattr(o, field))
    return {"discovered_source_files":len(migration.source_files),"discovered_runtime_objects":len(migration.objects),
            "classification":dict(sorted(Counter(o.kind for o in migration.objects).items())),
            "unmapped_runtime_sources":sorted(d.source for d in migration.descriptors if d.kind == "instance" and not d.owner),
            "registered_runtime_objects":len(migrated & registered),"unregistered_runtime_objects":sorted(migrated-registered),
            "duplicate_identities":duplicate,"missing_lineage":missing("lineage"),"missing_provenance":missing("provenance"),
            "missing_authority":missing("authority"),"schema_mismatches":[],"relationship_mismatches":[],
            "dependency_inconsistencies":[],"projection_inconsistencies":[],"parse_errors":list(migration.parse_errors),
            "reversible":migration.reversible,"valid":not duplicate and not migration.parse_errors and migrated <= registered}


def convergence_report(registry: Any, migration: RuntimeMigration | None = None) -> dict[str, Any]:
    """Read-only inventory of remaining semantic duplication and projection opportunities."""
    objects=registry.values(); fields=("authority","lineage","provenance","metadata")
    duplicated={}
    for field in fields:
        groups: dict[str,list[str]]={}
        for obj in objects: groups.setdefault(repr(obj.to_primitives()[field]),[]).append(obj.id)
        duplicated[field]=tuple(tuple(sorted(ids)) for ids in groups.values() if len(ids)>1)
    runtime_sources=tuple(sorted(o.id for o in objects if o.metadata.get("runtime_source")))
    projected=tuple(sorted(o.id for o in objects if registry.projection_targets(o.id)))
    return {"duplicated_semantic_storage":duplicated,"duplicated_authority":duplicated["authority"],
            "duplicated_lineage":duplicated["lineage"],"duplicated_provenance":duplicated["provenance"],
            "duplicated_metadata":duplicated["metadata"],"projection_opportunities":tuple(sorted(set(registry.ids)-set(projected))),
            "runtime_convergence_progress":{"registered":len(registry.ids),"projectable":len(projected),"runtime_adapters":len(runtime_sources)},
            "remaining_legacy_systems":runtime_sources,"migration":migration_report(registry,migration) if migration else None}


def convergence_report_markdown(registry: Any, migration: RuntimeMigration | None = None) -> str:
    report=convergence_report(registry,migration); progress=report["runtime_convergence_progress"]
    lines=["# Constitutional Runtime Convergence Report","",f"- Registered objects: {progress['registered']}",
           f"- Projectable objects: {progress['projectable']}",f"- Runtime adapters: {progress['runtime_adapters']}"]
    for name in ("duplicated_authority","duplicated_lineage","duplicated_provenance","duplicated_metadata","projection_opportunities","remaining_legacy_systems"):
        lines.extend(("",f"## {name.replace('_',' ').title()}",""))
        values=report[name]; lines.extend(f"- `{', '.join(v) if isinstance(v,tuple) else v}`" for v in values)
        if not values: lines.append("- None")
    return "\n".join(lines)+"\n"
