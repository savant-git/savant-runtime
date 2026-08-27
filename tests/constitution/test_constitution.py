from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.constitution.registry import (  # noqa: E402
    ConstitutionalRegistry,
    PROJECTION_TARGETS,
    REQUIRED_PRIMITIVES,
    canonical_json,
)


class ConstitutionalOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = ConstitutionalRegistry.load(ROOT)

    def test_reality_enters_recursive_ontology(self) -> None:
        self.assertEqual(self.registry.object("reality")["children"], ["domain:ontology"])
        self.assertEqual(
            set(self.registry.object("domain:ontology")["children"]),
            {f"domain:{name}" for name in ("doctrine","systems","faculties","exiles","services","operators","instances","segues","concept","runtime","project")},
        )

    def test_every_object_exposes_required_metadata(self) -> None:
        exposed = REQUIRED_PRIMITIVES | {"children", "lineage"}
        for object_id in self.registry.ids:
            self.assertFalse(exposed - self.registry.object(object_id).keys(), object_id)

    def test_existing_system_names_are_preserved(self) -> None:
        expected = {f"system:{name}" for name in (
            "shard", "kindred", "extant", "interval", "vigor", "hegemony", "trajectory",
        )}
        self.assertEqual(expected, {i for i in self.registry.ids if i.startswith("system:")})

    def test_exiles_are_adapted_from_existing_authority(self) -> None:
        authority_files = sorted((ROOT / "canon-system/authority/exiles").glob("*.yaml"))
        exile_ids = [i for i in self.registry.ids if i.startswith("exile:")]
        self.assertEqual(len(authority_files), len(exile_ids))
        for object_id in exile_ids:
            self.assertTrue(self.registry.object(object_id)["created_from"][0].endswith(".yaml"))

    def test_every_faculty_projects_through_every_system(self) -> None:
        faculties = [i for i in self.registry.ids if i.startswith("faculty:")]
        systems = [i for i in self.registry.ids if i.startswith("system:")]
        matrix = self.registry.faculty_system_matrix()
        self.assertEqual(len(matrix), len(faculties) * len(systems))
        self.assertEqual(len({(x["faculty"], x["system"]) for x in matrix}), len(matrix))

    def test_services_have_one_faculty_owner_and_an_exile(self) -> None:
        for service_id in (i for i in self.registry.ids if i.startswith("service:")):
            relationships = self.registry.object(service_id)["relationships"]
            owners = [r for r in relationships if r["type"] == "owned_by"]
            exiles = [r for r in relationships if r["type"] == "implemented_through"]
            self.assertEqual(1, len(owners), service_id)
            self.assertTrue(owners[0]["target"].startswith("faculty:"), service_id)
            self.assertGreaterEqual(len(exiles), 1, service_id)
            self.assertTrue(all(r["target"].startswith("exile:") for r in exiles), service_id)

    def test_every_object_is_graph_addressable(self) -> None:
        graph = self.registry.graph()
        node_ids = {node["id"] for node in graph["nodes"]}
        self.assertEqual(set(self.registry.ids), node_ids)
        self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"]))

    def test_all_target_projections_are_deterministic(self) -> None:
        for target in PROJECTION_TARGETS:
            first = self.registry.project(target)
            second = self.registry.project(target)
            self.assertEqual(canonical_json(first), canonical_json(second))
            self.assertEqual(first["digest"], second["digest"])

    def test_catalog_stores_only_universal_authoritative_primitives(self) -> None:
        catalog = json.loads((ROOT / "canon-system/authority/constitution/catalog.json").read_text())
        for item in catalog["objects"]:
            self.assertEqual(REQUIRED_PRIMITIVES, set(item))
            self.assertNotIn("children", item)
            self.assertNotIn("graph", item)


if __name__ == "__main__":
    unittest.main()
