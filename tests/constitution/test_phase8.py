from pathlib import Path
import unittest

from runtime.constitution import ConstitutionalRegistry, ConstitutionalValidator
from runtime.constitution.migration import convergence_report, convergence_report_markdown

ROOT=Path(__file__).resolve().parents[2]


class Phase8ConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=ConstitutionalRegistry.load(ROOT)

    def test_universal_resolver(self):
        self.assertEqual("system:shard",self.registry.lookup(id="system:shard").id)
        self.assertTrue(self.registry.lookup(kind="system")); self.assertTrue(self.registry.lookup(authority="constitutional"))
        self.assertTrue(self.registry.lookup(parent="reality")); self.assertTrue(self.registry.lookup(children="reality"))
        self.assertTrue(self.registry.lookup(relationship="owned_by")); self.assertTrue(self.registry.lookup(dependency="faculty:knowledge"))
        self.assertEqual("constitutional-object",self.registry.lookup(schema="constitutional-object")["id"]); self.assertTrue(self.registry.lookup(version="1.0.0"))
        self.assertTrue(self.registry.lookup(status="active")); self.assertTrue(self.registry.lookup(domain="ontology"))

    def test_registration_is_single_and_immutable(self):
        record=self.registry.registration("system:shard")
        self.assertEqual("system:shard",record["id"]); self.assertIn("schema",record); self.assertIn("projection_targets",record)
        with self.assertRaises(ValueError): self.registry.register(self.registry.get("system:shard"))

    def test_reflection_answers_all_questions(self):
        reflection=self.registry.reflect("system:shard")
        required={"identity","purpose","declared_at","governed_by","created_by","schema","dependents","dependencies",
                  "superseded_by","supersedes","runtime_components","documentation","graph_nodes","projection_targets"}
        self.assertFalse(required-set(reflection)); self.assertEqual(reflection,self.registry.reflect("system:shard"))

    def test_derived_engines(self):
        self.assertEqual("reality",self.registry.lineage.origin("system:shard"))
        self.assertIn("domain:ontology",self.registry.lineage.ancestors("system:shard"))
        self.assertTrue(self.registry.lineage.visualize("system:shard")["nodes"])
        self.assertFalse(self.registry.provenance.validate("system:shard"))
        self.assertIn("faculty:knowledge",self.registry.dependencies.direct("service:authority"))
        self.assertIn("service:authority",self.registry.dependencies.reverse("faculty:knowledge"))
        self.assertTrue(self.registry.dependencies.closure(("service:authority",)))

    def test_projection_cache_and_targets(self):
        first=self.registry.project("json"); self.assertGreater(self.registry.projection_cache.size,0)
        second=self.registry.project("json"); self.assertEqual(first,second)
        self.registry.invalidate_projections("schema"); self.assertEqual(0,self.registry.projection_cache.size)
        for target in ("runtime","documentation","markdown","json","graph","visualization","future_ui","future_api","future_ide","future_tooling"):
            self.assertEqual(target,self.registry.project(target)["target"])

    def test_validation_and_migration_reporting(self):
        validation=ConstitutionalValidator(self.registry).validate()
        self.assertTrue(validation["valid"]); self.assertTrue({"identity","authority","graph"} <= validation["checks"].keys())
        report=convergence_report(self.registry); markdown=convergence_report_markdown(self.registry)
        self.assertIn("runtime_convergence_progress",report); self.assertIn("# Constitutional Runtime Convergence Report",markdown)


if __name__ == "__main__": unittest.main()
