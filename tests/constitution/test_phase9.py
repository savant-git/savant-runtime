from dataclasses import dataclass
from pathlib import Path
import unittest

from runtime.constitution import ConstitutionalEventLog, ConstitutionalGraph, ConstitutionalRegistry, bootstrap

ROOT=Path(__file__).resolve().parents[2]


@dataclass(frozen=True,slots=True)
class GraphObject:
    id: str
    lineage: dict
    dependencies: tuple=()
    relationships: tuple=()
    kind: str="concept"


class Phase9RecursiveRealityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=ConstitutionalRegistry.load(ROOT)

    def test_every_object_projects_a_recursive_universe(self):
        reality=self.registry.universe("reality")
        self.assertEqual("reality",reality["object"]["id"])
        self.assertEqual(set(self.registry.ids)-{"reality"},set(reality["descendants"]))
        leaf=self.registry.universe("system:shard",nested=True)
        self.assertIn("contains",leaf); self.assertIn("inheritance",leaf)

    def test_deterministic_inheritance_keeps_dependencies_explicit(self):
        identity="service:authority"; effective=self.registry.inheritance.effective(identity)
        self.assertEqual(effective,self.registry.inheritance.effective(identity))
        self.assertEqual(dict(self.registry.authorities.effective(identity)),effective["authority"])
        self.assertEqual(self.registry.dependencies.direct(identity),effective["dependencies"])
        self.assertTrue(self.registry.inherited_projections(identity)); self.assertTrue(self.registry.inherited_schemas(identity))
        self.assertEqual(tuple(sorted(effective["projection_targets"])),effective["projection_targets"])

    def test_recursive_queries_and_paths(self):
        self.assertIn("reality",self.registry.find_ancestors("system:shard"))
        self.assertIn("system:shard",self.registry.find_descendants("reality"))
        lineage=self.registry.paths.lineage("system:shard","reality")
        self.assertTrue(lineage); self.assertTrue(all(e["type"]=="contains" for e in lineage))
        self.assertEqual(lineage,self.registry.paths.authority("system:shard"))
        dependency=self.registry.paths.dependency("service:authority","faculty:knowledge")
        self.assertTrue(dependency); self.assertTrue(all(e["type"]=="depends_on" for e in dependency))
        self.assertEqual(self.registry.constitutional_path("system:shard","reality"),
                         self.registry.paths.shortest("system:shard","reality"))
        self.assertEqual("doctrine",self.registry.governing_doctrine("system:shard").kind)
        self.assertTrue(self.registry.paths.governance("system:shard"))

    def test_immutable_events_and_temporal_reconstruction(self):
        initial=self.registry.get("system:shard").to_primitives(); log=ConstitutionalEventLog()
        created=log.append("ObjectCreated","temporal:test","2026-01-01T00:00:00Z",{"state":initial},"1.0.0")
        log.append("AuthorityChanged","temporal:test","2026-02-01T00:00:00Z",{"authority":{"source":"future"}},"2.0.0")
        log.append("RelationshipAdded","temporal:test","2026-03-01T00:00:00Z",{"relationship":{"type":"owned_by","target":"reality"}},"3.0.0")
        with self.assertRaises(TypeError): created.evidence["state"]["id"]="changed"
        self.assertTrue(log.verify())
        temporal=self.registry.temporal(log.events())
        self.assertEqual(initial["authority"],temporal.at_version("temporal:test","1.0.0")["state"]["authority"])
        self.assertEqual({"source":"future"},temporal.authority("temporal:test",version="2.0.0"))
        self.assertEqual(1,len(temporal.relationships("temporal:test",occurred_at="2026-03-01T00:00:00Z")))
        self.assertEqual(temporal.at_version("temporal:test","3.0.0"),temporal.at_version("temporal:test","3.0.0"))

    def test_bootstrap_exposes_minimal_recursive_roots(self):
        result=bootstrap(ROOT); ids={o.id for o in result.roots}
        self.assertIn("reality",ids); self.assertTrue(any(i.startswith("domain:") for i in ids))
        self.assertTrue(all(o.id=="reality" or o.lineage.get("parent")=="reality" or o.kind=="doctrine" for o in result.roots))

    def test_deep_tree_is_iterative(self):
        objects=[GraphObject("reality",{"parent":None})]
        objects.extend(GraphObject(f"deep:{i}",{"parent":"reality" if i==0 else f"deep:{i-1}"}) for i in range(5000))
        graph=ConstitutionalGraph(objects)
        self.assertEqual(5000,len(graph.ancestors("deep:4999")))
        self.assertEqual(5000,len(graph.descendants("reality")))

    def test_stress_250000_constitutional_objects(self):
        objects=(GraphObject(f"stress:{i}",{"parent":None}) for i in range(250_000))
        graph=ConstitutionalGraph(objects)
        self.assertEqual(250_000,len(graph.nodes)); self.assertFalse(graph.detect_cycles("contains"))


if __name__=="__main__": unittest.main()
