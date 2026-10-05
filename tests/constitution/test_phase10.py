from pathlib import Path
import unittest

from runtime.constitution import (ConstitutionalObject, ConstitutionalProjectionPipeline,
    ConstitutionalRegistry, PIPELINE_STAGES)

ROOT=Path(__file__).resolve().parents[2]


class Phase10PureProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.registry=ConstitutionalRegistry.load(ROOT)

    def test_authoritative_storage_contains_primitives_only(self):
        from runtime.constitution.object import PRIMITIVE_FIELDS
        for obj in self.registry.values(): self.assertEqual(set(PRIMITIVE_FIELDS),set(obj.to_primitives()))
        self.assertNotIn("graph",self.registry.get("reality").to_primitives())

    def test_pipeline_order_and_independent_stages(self):
        pipeline=ConstitutionalProjectionPipeline(self.registry)
        self.assertEqual(PIPELINE_STAGES,tuple(stage.name for stage in pipeline.stages))
        state=pipeline.run("runtime")
        self.assertEqual(PIPELINE_STAGES,state.completed); self.assertTrue(state.validation["valid"])
        self.assertFalse(state.cache["authoritative"]); self.assertEqual(set(self.registry.ids),set(state.runtime["registry"]))
        self.assertTrue({"indexes","graph","reverse_indexes","dependency_maps","projection_tree","documentation",
                         "reflection_table","visualization","diagnostics","digest"} <= state.runtime.keys())
        self.assertEqual(state.runtime["digest"],pipeline.run("runtime").runtime["digest"])

    def test_constitutional_diff_and_migration_plan(self):
        identity="system:shard"; values=[]
        for obj in self.registry.values():
            if obj.id!=identity: values.append(obj)
            else:
                changed=obj.to_primitives(); changed["version"]="2.0.0"; changed["authority"]={"source":"phase10"}
                changed["relationships"]=[*changed["relationships"],{"type":"owned_by","target":"reality"}]
                changed["dependencies"]=[*changed["dependencies"],"domain:ontology"]
                changed["lineage"]={**changed["lineage"],"parent":"reality"}
                changed["metadata"]={**changed["metadata"],"projection_targets":["runtime","future_ui"]}
                values.append(ConstitutionalObject.from_mapping(changed))
        after=ConstitutionalRegistry(ROOT,values,self.registry.kinds,self.registry.schemas,self.registry.relationship_types)
        diff=self.registry.diff(after)
        for field in ("version","authority","relationships","dependencies","lineage"): self.assertEqual(identity,diff.changed[field][0]["id"])
        self.assertTrue(diff.projections); self.assertEqual(diff.migration_plan,diff.migration_plan)

    def test_self_audit(self):
        report=self.registry.self_audit()
        self.assertTrue(report["valid"],report); self.assertEqual("ConstitutionalRegistry",report["evidence"]["authoritative_store"])
        self.assertEqual(0,report["evidence"]["derived_stores_persisted"])
        self.assertFalse(report["evidence"]["projection_cache_authoritative"])

    def test_assertion_only_extension_returns_new_snapshot(self):
        source=self.registry.get("service:authority").to_primitives(); source.update({
            "id":"service:phase10-fixture","canonical_name":"phase10-fixture","display_name":"Phase 10 Fixture",
            "description":"Assertion-only extension fixture.","relationships":[],"dependencies":[],
            "lineage":{"parent":"domain:services","supersedes":[],"superseded_by":[]},
            "provenance":{"sources":["tests/constitution/test_phase10.py"]},"metadata":{}})
        contribution=self.registry.contribute("engine:fixture",(source,))
        self.assertNotIn("service:phase10-fixture",self.registry.ids)
        self.assertIn("service:phase10-fixture",contribution.registry.ids)
        self.assertEqual("engine:fixture",contribution.engine)
        with self.assertRaises((ValueError,TypeError)): self.registry.contribute("engine:bad",(lambda:None,))


if __name__=="__main__": unittest.main()
