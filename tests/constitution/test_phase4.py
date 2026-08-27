from pathlib import Path
import tempfile
import unittest

from runtime.constitution import (ConstitutionalExtensions, ConstitutionalRegistry,
    RuntimeDescriptor, RuntimeMigrationPluginRegistry, RuntimeMigrationValidator, bootstrap, discover_runtime)
from runtime.kinship import KinshipGraph
from runtime.lineage import LineageGraph

ROOT = Path(__file__).resolve().parents[2]

class Phase4RuntimeMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = ConstitutionalRegistry.load(ROOT)
        cls.bootstrap = bootstrap(ROOT)
        cls.registry = cls.bootstrap.registry

    def test_bootstrap_discovers_and_validates_runtime(self):
        self.assertGreater(len(self.bootstrap.runtime_migration.source_files), 50)
        self.assertGreater(len(self.bootstrap.runtime_migration.objects), 100)
        report = RuntimeMigrationValidator(self.registry, self.bootstrap.runtime_migration).validate()
        self.assertTrue(report["valid"], report); self.assertTrue(report["reversible"])
        self.assertFalse(report["unregistered_runtime_objects"])

    def test_existing_constitutional_identity_is_unchanged(self):
        for kind in ("system","exile","faculty","service","operator","instance","segue"):
            for original in self.authority.by_kind(kind):
                self.assertEqual(original.to_primitives(), self.registry.get(original.id).to_primitives())

    def test_runtime_compatibility_exports_are_unchanged(self):
        from runtime.kinship import KinshipGraph as after_kinship
        from runtime.lineage import LineageGraph as after_lineage
        self.assertIs(KinshipGraph, after_kinship); self.assertIs(LineageGraph, after_lineage)

    def test_every_source_and_public_definition_is_registered(self):
        migration = self.bootstrap.runtime_migration
        registered_sources = {o.metadata.get("runtime_source") for o in migration.objects}
        self.assertEqual(set(migration.source_files), registered_sources)
        self.assertTrue(all(self.registry.get(d.identity) for d in migration.descriptors))

    def test_projection_and_registry_are_deterministic(self):
        left = ConstitutionalRegistry.load_migrated(ROOT); right = ConstitutionalRegistry.load_migrated(ROOT)
        self.assertEqual(left.ids, right.ids)
        self.assertEqual(left.project("runtime"), right.project("runtime"))
        self.assertEqual(left.graph_model.export(), right.graph_model.export())

    def test_extension_composition_remains_available(self):
        extensions=ConstitutionalExtensions(); extensions.register_operator("phase4", {"id":"phase4"})
        self.assertEqual("phase4", extensions.discover("operator")[0]["id"])
        plugins=RuntimeMigrationPluginRegistry()
        plugins.register("fixture", lambda root, authority: (RuntimeDescriptor("runtime:operator:fixture","operator","fixture","fixture","runtime/fixture",(),"faculty:execution","0"*64),))
        migration=discover_runtime(ROOT,self.authority.values(),plugins)
        self.assertIn("runtime:operator:fixture", {o.id for o in migration.objects})

if __name__ == "__main__": unittest.main()
