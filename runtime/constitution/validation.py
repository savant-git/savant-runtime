from __future__ import annotations

from typing import Any


def _projection_inconsistencies(registry: Any) -> list[str]:
    from .projection import ProjectionPluginRegistry
    failures: list[str] = []
    for target in ProjectionPluginRegistry.discover().targets:
        first, second = registry.project(target), registry.project(target)
        if not first.get("digest") or first != second: failures.append(f"{target} projection is not deterministic")
    return failures


class ConstitutionalValidator:
    """Aggregated read-only integrity validation."""
    def __init__(self, registry: Any): self.registry = registry
    def validate(self) -> dict[str, Any]:
        checks = {"identity":[],"schema":[],"authority":[],"relationships":[],"dependencies":[],"projection":[],"lineage":[],"provenance":[],"recursive":[],"inheritance":[],"orphans":[],"registry":[],"graph":[]}
        ids = set(self.registry.ids)
        for obj in self.registry.values():
            try: self.registry.schemas.validate(obj)
            except Exception as exc: checks["schema"].append({"id":obj.id,"error":str(exc)})
            try: self.registry.authorities.validate(obj.id)
            except Exception as exc: checks["authority"].append({"id":obj.id,"error":str(exc)})
            for r in obj.relationships:
                if r.get("target") not in ids or not self.registry.relationship_types.contains(str(r.get("type"))): checks["relationships"].append({"id":obj.id,"relationship":dict(r)})
            for dep in obj.dependencies:
                if dep not in ids: checks["dependencies"].append({"id":obj.id,"dependency":dep})
            if "parent" not in obj.lineage or (obj.lineage.get("parent") and obj.lineage.get("parent") not in ids): checks["lineage"].append({"id":obj.id,"error":"missing or unknown parent"})
            reconstructed = self.registry.lineage_lookup(obj.id)
            if not {"origin","ancestry","descendants","revision_history","authority_chain"} <= reconstructed.keys(): checks["lineage"].append({"id":obj.id,"error":"incomplete reconstruction"})
            provenance = self.registry.provenance_lookup(obj.id)
            required_provenance = {"creation_authority","creation_source","migration_source","schema_source","parent_source","projection_source"}
            if not obj.provenance or not required_provenance <= provenance.keys(): checks["provenance"].append({"id":obj.id,"error":"incomplete provenance"})
        try: self.registry.graph_model.detect_cycles("contains", True)
        except Exception as exc: checks["recursive"].append(str(exc))
        checks["projection"] = _projection_inconsistencies(self.registry)
        checks["registry"] = [] if len(ids) == len(self.registry.ids) and all(self.registry.kinds.contains(o.kind) for o in self.registry.values()) else ["registry index inconsistency"]
        checks["identity"] = [] if len(ids)==len(self.registry.ids) else ["identity collision"]
        try: self.registry.graph_model.export()
        except Exception as exc: checks["graph"].append(str(exc))
        checks["inheritance"] = list(self.registry.inheritance.validate()) if hasattr(self.registry,"inheritance") else []
        checks["orphans"] = list(self.registry.graph_model.orphans())
        return {"valid":not any(checks.values()),"checks":checks}


class RuntimeMigrationValidator:
    def __init__(self, registry: Any, migration: Any): self.registry = registry; self.migration = migration
    def validate(self) -> dict[str, Any]:
        from .migration import migration_report
        report = migration_report(self.registry, self.migration)
        ids = set(self.registry.ids)
        for obj in self.migration.objects:
            try: self.registry.schemas.validate(obj)
            except Exception as exc: report["schema_mismatches"].append({"id":obj.id,"error":str(exc)})
            if obj.lineage.get("parent") not in ids: report["missing_lineage"].append(obj.id)
            try: self.registry.authorities.validate(obj.id)
            except Exception as exc: report["missing_authority"].append({"id":obj.id,"error":str(exc)})
            for relation in obj.relationships:
                if relation.get("target") not in ids or not self.registry.relationship_types.contains(str(relation.get("type"))): report["relationship_mismatches"].append({"id":obj.id,"relationship":dict(relation)})
            for dependency in obj.dependencies:
                if dependency not in ids: report["dependency_inconsistencies"].append({"id":obj.id,"dependency":dependency})
        report["projection_inconsistencies"] = _projection_inconsistencies(self.registry)
        report["valid"] = not any(report[key] for key in ("unregistered_runtime_objects","duplicate_identities","missing_lineage","missing_provenance","missing_authority","schema_mismatches","relationship_mismatches","dependency_inconsistencies","projection_inconsistencies","parse_errors")) and report["reversible"]
        return report
