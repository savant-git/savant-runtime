from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from runtime.constitution import ConstitutionalObject, ConstitutionalRegistry, ConstitutionalValidator, migration_readiness_report
from runtime.constitution.graph import ConstitutionalGraph
from runtime.constitution.kinds import KindRegistry
from runtime.constitution.projection import PROJECTION_TARGETS, ProjectionPluginRegistry, canonical_json
from runtime.constitution.relationships import RelationshipTypeRegistry
from runtime.constitution.schema import ConstitutionalSchemaRegistry


def primitive(object_id: str, parent: str | None = None, dependencies=()):
    return ConstitutionalObject.from_mapping({
        "id":object_id,"kind":"concept","canonical_name":object_id,"display_name":object_id,"description":object_id,
        "authority":{"source":"test"},"status":"active","version":"1.0.0","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z",
        "lineage":{"parent":parent,"supersedes":[],"superseded_by":[]},"provenance":{"sources":["test"]},
        "relationships":[],"dependencies":list(dependencies),"metadata":{},
    })


class Phase2OntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry = ConstitutionalRegistry.load(ROOT)

    def test_infrastructure_is_self_describing(self):
        for object_id in ("reality","kind:system","schema:constitutional-object","relationship:contains"):
            self.assertIsInstance(self.registry.get(object_id), ConstitutionalObject)

    def test_relationship_types_are_discovered(self):
        for relation in ("contains","implements","depends_on","extends","specializes","instantiates","projects_to","governs","owns","references","derived_from","supersedes","superseded_by"):
            self.assertTrue(self.registry.relationship_types.contains(relation))

    def test_recursive_lineage_and_provenance_reconstruction(self):
        lineage = self.registry.lineage_lookup("system:shard")
        self.assertEqual("reality", lineage["origin"]); self.assertIn("domain:ontology", lineage["ancestry"])
        self.assertIn("authority_chain", lineage); self.assertIn("creation_source", self.registry.provenance_lookup("system:shard"))

    def test_dependency_queries_and_cycles(self):
        self.assertIn("faculty:knowledge", self.registry.dependency_lookup("service:authority", False))
        self.assertIn("service:authority", self.registry.reverse_dependency_lookup("faculty:knowledge"))
        graph = ConstitutionalGraph([primitive("a", dependencies=("b",)), primitive("b", dependencies=("a",))])
        self.assertTrue(graph.detect_cycles("depends_on")); self.assertIn("dependency_cycles", graph.export()["visualization_hooks"])

    def test_query_api(self):
        self.assertEqual("system:shard", self.registry.find_by_id("system:shard").id)
        self.assertTrue(self.registry.find_by_kind("system")); self.assertTrue(self.registry.find_by_authority("constitutional"))
        self.assertTrue(self.registry.find_by_relationship("owned_by")); self.assertTrue(self.registry.projection_lookup("system:shard"))
        self.assertIn("reality", self.registry.find_ancestors("system:shard")); self.assertIn("system:shard", self.registry.find_descendants("reality"))

    def test_projection_plugins_and_determinism(self):
        discovered = ProjectionPluginRegistry.discover()
        for target in ("runtime","json","yaml","markdown","documentation","graph","future_visualization","future_code_generation"):
            self.assertIn(target, discovered.targets)
            self.assertEqual(canonical_json(self.registry.project(target)), canonical_json(self.registry.project(target)))

    def test_schema_evolution_prefers_latest_version(self):
        base = {"id":"constitutional-object","version":"1.0.0","required":[]}
        old = {"id":"semantic-v1","version":"1.0.0","kind":"concept","inherits":"constitutional-object","required":[]}
        new = {"id":"semantic-v2","version":"2.0.0","kind":"concept","inherits":"semantic-v1","required":[]}
        schemas = ConstitutionalSchemaRegistry([base, old, new])
        self.assertEqual("semantic-v2", schemas.schema_for_kind("concept")["id"]); self.assertEqual(1, len(schemas.by_version("2.0.0")))

    def test_deep_recursion_has_no_hardcoded_depth(self):
        objects = [primitive("n0")] + [primitive(f"n{i}", f"n{i-1}") for i in range(1, 5000)]
        graph = ConstitutionalGraph(objects)
        self.assertEqual(4999, len(graph.ancestors("n4999")))

    def test_registry_stress_100000_objects(self):
        kinds = KindRegistry([{"id":"concept"}]); schemas = ConstitutionalSchemaRegistry([{"id":"constitutional-object","version":"1.0.0","required":[]}])
        relationships = RelationshipTypeRegistry([])
        registry = ConstitutionalRegistry(ROOT, (primitive(f"stress:{i}") for i in range(100000)), kinds, schemas, relationships)
        self.assertEqual(100000, len(registry.ids)); self.assertEqual(100000, len(registry.by_kind("concept")))

    def test_validation_and_readiness_are_read_only(self):
        before = canonical_json([o.to_primitives() for o in self.registry.values()])
        self.assertTrue(ConstitutionalValidator(self.registry).validate()["valid"])
        report = migration_readiness_report(self.registry)
        self.assertFalse(report["auto_fixed"]); self.assertEqual(before, canonical_json([o.to_primitives() for o in self.registry.values()]))


if __name__ == "__main__": unittest.main()
