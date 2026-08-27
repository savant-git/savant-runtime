from pathlib import Path
import unittest

from runtime.constitution import (ConstitutionalEventLog, ConstitutionalExtensions,
    ConstitutionalRegistry, ConstitutionalVersions, ProjectionContext, SemanticVersion)
from runtime.constitution.projection import ProjectionPluginRegistry

ROOT = Path(__file__).resolve().parents[2]

class Phase3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry = ConstitutionalRegistry.load(ROOT)

    def test_required_projection_targets_and_chaining(self):
        targets = ProjectionPluginRegistry.discover().targets
        for target in ("runtime","graph","documentation","markdown","json","yaml","schema","validation","future_code_generation","future_visualization"):
            self.assertIn(target, targets)
        result = self.registry.project("json", ProjectionContext("json"), ("schema","validation"))
        self.assertEqual(["schema","validation"], [child["target"] for child in result["children"]])
        self.assertTrue(result["authority_chain"]); self.assertEqual(result, self.registry.project("json", ProjectionContext("json"), ("schema","validation")))

    def test_identity_authority_and_queries(self):
        self.assertEqual("system:shard", self.registry.canonical_lookup("system:shard").id)
        self.assertTrue(self.registry.find_authority_chain("system:shard"))
        self.assertEqual("system:shard", self.registry.find_lineage_chain("system:shard")[-1])
        self.assertTrue(self.registry.find_provenance_chain("system:shard"))
        self.assertEqual("service:authority", self.registry.find_dependency_tree("service:authority")["id"])
        self.assertTrue(self.registry.find_relationship_graph("system:shard")["nodes"])
        for query in ("all_systems","all_faculties","all_services","all_exiles","all_doctrines","all_operators"):
            self.assertTrue(getattr(self.registry, query)())

    def test_append_only_events_are_evidence(self):
        log = ConstitutionalEventLog(); event = log.append("object_projected","system:shard","2026-07-21T00:00:00Z",{"target":"json"})
        self.assertEqual(1, event.sequence); self.assertEqual((event,), log.events("system:shard"))
        with self.assertRaises(TypeError): event.evidence["target"] = "yaml"

    def test_compositional_extensions_and_versions(self):
        extensions = ConstitutionalExtensions(); extensions.register_kind("new", {"id":"new"})
        extensions.register_projection("custom", lambda objects, graph: objects)
        self.assertEqual("new", extensions.discover("kind")[0]["id"])
        with self.assertRaises(ValueError): extensions.register_kind("new", {"id":"new"})
        versions = ConstitutionalVersions(*(SemanticVersion.parse("1.0.0") for _ in range(5)))
        self.assertEqual("1.0.0", str(versions.projection))

if __name__ == "__main__": unittest.main()
