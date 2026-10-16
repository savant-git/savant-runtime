from pathlib import Path
import unittest

from runtime.constitution import ConstitutionalRegistry
from runtime.fluid_canon import ASSERTION_TYPES,FluidAssertion,FluidCanonEngine,FluidCanonValidationError

ROOT=Path(__file__).resolve().parents[2]

def assertion(identity,kind="Fact",subject="world",claim=True,when="2026-01-01T00:00:00Z",**options):
    return FluidAssertion.create(identity=identity,assertion_type=kind,subject=subject,claim=claim,
        asserted_by=options.pop("asserted_by","tester"),source=options.pop("source","tests/fluid_canon"),
        occurred_at=when,**options)

class FluidCanonTests(unittest.TestCase):
    def setUp(self): self.engine=FluidCanonEngine.install(ConstitutionalRegistry.load(ROOT))

    def test_all_assertion_forms_are_constitutional_objects(self):
        values=tuple(assertion(f"canon:type:{i}",kind,subject=f"type:{kind}") for i,kind in enumerate(ASSERTION_TYPES))
        engine=self.engine.contribute(values)
        self.assertEqual(set(ASSERTION_TYPES),{o.metadata["assertion_type"] for o in engine.assertions()})
        self.assertTrue(all(o.kind=="concept" and not o.authority for o in engine.assertions()))
        self.assertTrue(all(engine.registry.inherited_authority(o.id) for o in engine.assertions()))

    def test_truth_evolves_without_mutation(self):
        first=assertion("canon:sky:v1",claim="blue",when="2026-01-01T00:00:00Z",version="1.0.0")
        second=assertion("canon:sky:v2",claim="violet",when="2026-02-01T00:00:00Z",version="2.0.0",supersedes=(first.id,))
        engine=self.engine.contribute((first,second))
        self.assertEqual(("canon:sky:v2",),tuple(o.id for o in engine.current_truth("world")))
        self.assertEqual(("canon:sky:v1",),tuple(o.id for o in engine.historical_truth("world",at="2026-01-31T23:59:59Z")))
        self.assertEqual(("canon:sky:v1",),tuple(o.id for o in engine.historical_truth("world",version="1.0.0")))
        self.assertEqual("blue",engine.registry.get_exact(first.id).metadata["claim"])
        self.assertEqual((second.id,),tuple(o.id for o in engine.who_superseded(first.id)))

    def test_why_evidence_conflict_and_authority_chains(self):
        source=assertion("canon:source",kind="Source",claim="instrument")
        evidence=assertion("canon:evidence",kind="Evidence",claim={"reading":42},evidence=(source.id,))
        fact=assertion("canon:fact",claim=42,evidence=(evidence.id,),asserted_by="observer")
        conflict=assertion("canon:conflict",kind="Conflict",claim="reading disputed",conflicts=(fact.id,))
        resolution=assertion("canon:resolution",kind="Resolution",claim="calibrated",resolves=(conflict.id,))
        engine=self.engine.contribute((source,evidence,fact,conflict,resolution))
        self.assertEqual((evidence.id,source.id),tuple(o.id for o in engine.evidence_chain(fact.id)))
        self.assertEqual({conflict.id,resolution.id},set(o.id for o in engine.conflict_chain(fact.id)))
        why=engine.why(fact.id); self.assertEqual("observer",why["asserted_by"])
        self.assertEqual((evidence.id,source.id),why["evidence"]); self.assertTrue(why["authority_chain"])

    def test_validation_prevents_invalid_canon(self):
        invalid=assertion("canon:invalid",evidence=("service:authority",))
        with self.assertRaises(FluidCanonValidationError): self.engine.contribute((invalid,))
        a=assertion("canon:cycle:a",supersedes=("canon:cycle:b",))
        b=assertion("canon:cycle:b",supersedes=("canon:cycle:a",))
        with self.assertRaises(FluidCanonValidationError): self.engine.contribute((a,b))
        orphan=assertion("canon:orphan").to_primitives(); orphan["lineage"]["parent"]="missing:parent"
        from runtime.constitution import ConstitutionalObject
        with self.assertRaises(ValueError): self.engine.contribute((ConstitutionalObject.from_mapping(orphan),))

    def test_deep_supersession_and_historical_reconstruction(self):
        count=5000; values=[]
        for i in range(count):
            values.append(assertion(f"canon:deep:{i:05d}",claim=i,when=f"2026-01-01T{i:06d}Z",
                version=f"1.0.{i}",supersedes=(() if i==0 else (f"canon:deep:{i-1:05d}",))))
        engine=self.engine.contribute(values)
        self.assertEqual((f"canon:deep:{count-1:05d}",),tuple(o.id for o in engine.current_truth("world")))
        self.assertEqual(("canon:deep:02500",),tuple(o.id for o in engine.historical_truth("world",version="1.0.2500")))
        self.assertEqual(count-1,len(engine.who_superseded("canon:deep:00000")))

    def test_large_evolving_canon_100000_assertions(self):
        values=(assertion(f"canon:scale:{i:06d}",kind=ASSERTION_TYPES[i%len(ASSERTION_TYPES)],
                          subject=f"subject:{i:06d}",claim=i) for i in range(100_000))
        engine=self.engine.contribute(values)
        self.assertEqual(100_000,len(engine.assertions()))
        self.assertEqual(1,len(engine.current_truth("subject:099999")))
        self.assertTrue(engine.validate()["valid"])

if __name__=="__main__": unittest.main()
