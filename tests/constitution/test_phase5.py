import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

from runtime.constitution import ConstitutionalRegistry, bootstrap, discover_runtime

ROOT=Path(__file__).resolve().parents[2]

class Phase5ConsolidationTests(unittest.TestCase):
    def test_relative_runtime_dependencies_are_discovered(self):
        authority=ConstitutionalRegistry.load(ROOT)
        migration=discover_runtime(ROOT,authority.values())
        objects={o.id:o for o in migration.objects}
        self.assertIn("runtime:module:runtime.constitution.bootstrap", objects["runtime:module:runtime.constitution.registry"].dependencies)

    def test_post_bootstrap_registration_refreshes_identity(self):
        registry=ConstitutionalRegistry.load(ROOT); original=registry.get("system:shard")
        value=original.to_primitives(); value["id"]="test:extension-object"; value["canonical_name"]="Extension Object"
        from runtime.constitution import ConstitutionalObject
        added=ConstitutionalObject.from_mapping(value); registry.register(added)
        self.assertIs(added,registry.get(added.id))

    def test_bootstrap_succeeds_with_empty_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); shutil.copytree(ROOT/"canon-system"/"authority",root/"canon-system"/"authority")
            (root/"runtime").mkdir()
            result=bootstrap(root)
            self.assertEqual((),result.runtime_migration.objects); self.assertTrue(result.report["valid"])

    def test_complete_external_extension_composes_without_source_changes(self):
        path=Path(__file__).with_name("demo_extension.py")
        spec=importlib.util.spec_from_file_location("phase5_demo_extension",path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        extension=module.build_extension()
        for point in ("kind","schema","doctrine","projection","validator"):
            self.assertEqual(1,len(extension.discover(point)),point)

if __name__ == "__main__": unittest.main()
