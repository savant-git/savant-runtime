from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .kinds import KindRegistry
from .object import ConstitutionalObject
from .schema import ConstitutionalSchemaRegistry
from .relationships import RelationshipTypeRegistry
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .registry import ConstitutionalRegistry
    from .migration import RuntimeMigration


BOOTSTRAP_KINDS = {"system", "exile", "faculty", "service", "operator", "doctrine", "kind", "schema"}
BOOTSTRAP_TIMESTAMP = "2026-07-21T04:20:39Z"


@dataclass(frozen=True)
class ConstitutionalBootstrap:
    objects: tuple[ConstitutionalObject, ...]
    kinds: KindRegistry
    schemas: ConstitutionalSchemaRegistry
    relationships: RelationshipTypeRegistry
    registry: "ConstitutionalRegistry | None" = None
    runtime_migration: "RuntimeMigration | None" = None
    report: dict[str, Any] | None = None
    roots: tuple[ConstitutionalObject, ...] = ()

    def by_kind(self, kind: str) -> tuple[ConstitutionalObject, ...]:
        return tuple(obj for obj in self.objects if obj.kind == kind)


def _modernize(item: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    source = {**deepcopy(defaults), **deepcopy(item)}
    kind = source.pop("constitutional_kind", source.pop("kind", "concept"))
    parent = source.pop("parent", None)
    created_from = source.pop("created_from", [])
    supersedes = source.pop("supersedes", [])
    superseded_by = source.pop("superseded_by", [])
    implementation_refs = source.pop("implementation_refs", [])
    projection_targets = source.pop("projection_targets", [])
    return {
        "id": source["id"], "kind": kind, "canonical_name": source["canonical_name"],
        "display_name": source.get("display_name", source["canonical_name"]),
        "description": source["description"], "authority": source["authority"],
        "status": source["status"], "version": str(source["version"]),
        "created_at": source.get("created_at", BOOTSTRAP_TIMESTAMP),
        "updated_at": source.get("updated_at", BOOTSTRAP_TIMESTAMP),
        "lineage": source.get("lineage", {"parent": parent, "supersedes": supersedes, "superseded_by": superseded_by}),
        "provenance": {**source["provenance"], "sources": source["provenance"].get("sources", created_from)},
        "relationships": source["relationships"], "dependencies": source["dependencies"],
        "metadata": source.get("metadata", {"implementation_refs": implementation_refs, "projection_targets": projection_targets}),
    }


def load_authority(root: Path) -> tuple[list[ConstitutionalObject], KindRegistry, ConstitutionalSchemaRegistry, RelationshipTypeRegistry]:
    kinds = KindRegistry.discover(root)
    schemas = ConstitutionalSchemaRegistry.discover(root)
    relationships = RelationshipTypeRegistry.discover(root)
    payload = json.loads((root / "canon-system/authority/constitution/catalog.json").read_text(encoding="utf-8"))
    objects = [_modernize(item, payload.get("defaults", {})) for item in payload["objects"]]
    doctrine_path = root / "canon-system/authority/constitution/doctrines.json"
    if doctrine_path.exists():
        objects.extend(json.loads(doctrine_path.read_text(encoding="utf-8"))["objects"])
    self_path = root / "canon-system/authority/constitution/self-descriptions.json"
    if self_path.exists():
        objects.extend(json.loads(self_path.read_text(encoding="utf-8"))["objects"])
    import yaml
    for path in sorted((root / "canon-system/authority/exiles").glob("*.yaml")):
        source = yaml.safe_load(path.read_text(encoding="utf-8")); lineage = source.get("lineage", {})
        objects.append({
            "id": source["id"], "kind": "exile", "canonical_name": source.get("title", path.stem).title(),
            "display_name": source.get("title", path.stem).title(), "description": "; ".join(source.get("purpose", {}).get("current", [])),
            "authority": source.get("authority", {}), "status": source.get("status", "provisional"), "version": str(source.get("version", "1")),
            "created_at": BOOTSTRAP_TIMESTAMP, "updated_at": BOOTSTRAP_TIMESTAMP,
            "lineage": {"parent": "domain:exiles", "supersedes": lineage.get("supersedes", []), "superseded_by": lineage.get("superseded_by", [])},
            "provenance": {**source.get("provenance", {}), "sources": [str(path.relative_to(root))]},
            "relationships": source.get("relationships", []), "dependencies": source.get("dependencies", []), "metadata": {},
        })
    result = [ConstitutionalObject.from_mapping(o) for o in objects]
    for obj in result:
        if not kinds.contains(obj.kind): raise ValueError(f"unregistered kind: {obj.kind}")
        schemas.validate(obj)
    return result, kinds, schemas, relationships


def bootstrap(root: Path) -> ConstitutionalBootstrap:
    objects, kinds, schemas, relationships = load_authority(root)
    selected = tuple(obj for obj in objects if obj.kind in BOOTSTRAP_KINDS)
    roots = tuple(obj for obj in objects if obj.id=="reality" or obj.lineage.get("parent")=="reality" or obj.kind=="doctrine")
    from .registry import ConstitutionalRegistry
    from .migration import discover_runtime, migration_report
    migration = discover_runtime(root, objects)
    registry = ConstitutionalRegistry(root, (*objects, *migration.objects), kinds, schemas, relationships)
    report = migration_report(registry, migration)
    return ConstitutionalBootstrap(selected, kinds, schemas, relationships, registry, migration, report, roots)
