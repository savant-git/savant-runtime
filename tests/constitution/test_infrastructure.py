from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from runtime.constitution import ConstitutionalObject, ConstitutionalRegistry
from runtime.constitution.bootstrap import bootstrap
from runtime.constitution.graph import ConstitutionalGraph
from runtime.constitution.object import PRIMITIVE_FIELDS
from runtime.constitution.projection import PROJECTION_TARGETS, canonical_json


class ConstitutionalInfrastructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry = ConstitutionalRegistry.load(ROOT)

    def test_object_contains_only_immutable_primitives(self):
        obj = self.registry.get("system:shard")
        self.assertEqual(set(PRIMITIVE_FIELDS), set(obj.to_primitives()))
        with self.assertRaises((AttributeError, TypeError)): obj.id = "changed"
        with self.assertRaises(TypeError): obj.authority["state"] = "changed"

    def test_kinds_are_discovered_and_extensible(self):
        self.assertIn("persona", self.registry.kinds.ids)
        self.assertEqual("Semantic identity definition.", self.registry.kinds.get("kind")["description"])

    def test_schema_discovery_inheritance_and_validation(self):
        self.assertEqual(("constitutional-object", "semantic-object"), self.registry.schemas.ids)
        self.assertEqual("semantic-object", self.registry.schema_lookup("system")["id"])
        bad = self.registry.get("system:shard").to_primitives(); bad.pop("authority")
        with self.assertRaises(ValueError): ConstitutionalObject.from_mapping(bad)

    def test_registry_lookups_and_immutable_ids(self):
        self.assertTrue(self.registry.by_kind("system"))
        self.assertIn("reality", self.registry.lineage_lookup("system:shard")["ancestors"])
        self.assertEqual("1.0.0", self.registry.by_version("1.0.0")[0].version)
        with self.assertRaises(ValueError): self.registry.register(self.registry.get("system:shard"))

    def test_graph_traversal_export_and_cycles(self):
        graph = ConstitutionalGraph(self.registry.values())
        self.assertIn("system:shard", graph.descendants("reality"))
        self.assertIn("reality", graph.ancestors("system:shard"))
        self.assertIn("visualization_hooks", graph.export())
        source = self.registry.get("system:shard").to_primitives()
        source["lineage"]["parent"] = "system:shard"
        with self.assertRaises(ValueError): ConstitutionalGraph([ConstitutionalObject.from_mapping(source)])

    def test_bootstrap_scope_and_relationships(self):
        result = bootstrap(ROOT)
        for kind in ("system", "exile", "faculty", "service", "operator", "doctrine"):
            self.assertTrue(result.by_kind(kind), kind)
        self.assertTrue(result.kinds.ids); self.assertTrue(result.schemas.ids)
        self.assertFalse(result.by_kind("instance"))

    def test_every_projection_is_deterministic_and_disposable(self):
        for target in PROJECTION_TARGETS:
            self.assertEqual(canonical_json(self.registry.project(target)), canonical_json(self.registry.project(target)))


if __name__ == "__main__": unittest.main()
