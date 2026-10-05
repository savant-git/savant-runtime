from pathlib import Path
from statistics import median
from time import perf_counter
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from runtime.constitution import ConstitutionalObject, ConstitutionalRegistry, ConstitutionalValidator
from runtime.constitution.graph import ConstitutionalGraph
from runtime.constitution.kinds import KindRegistry
from runtime.constitution.relationships import RelationshipTypeRegistry
from runtime.constitution.schema import ConstitutionalSchemaRegistry

def measure(operation, repeats=5):
    samples=[]
    for _ in range(repeats):
        started=perf_counter(); operation(); samples.append((perf_counter()-started)*1000)
    return {"median_ms":round(median(samples),3),"min_ms":round(min(samples),3),"samples":repeats}

def primitive(i, parent=None):
    return ConstitutionalObject.from_mapping({"id":f"bench:{i}","kind":"concept","canonical_name":str(i),"display_name":str(i),"description":"benchmark","authority":{"source":"benchmark"},"status":"active","version":"1.0.0","created_at":"2026-07-21T00:00:00Z","updated_at":"2026-07-21T00:00:00Z","lineage":{"parent":parent,"supersedes":[],"superseded_by":[]},"provenance":{"sources":["benchmark"]},"relationships":[],"dependencies":[],"metadata":{}})

def main():
    registry=ConstitutionalRegistry.load(ROOT)
    deep=[primitive(0)]+[primitive(i,f"bench:{i-1}") for i in range(1,5000)]
    kinds=KindRegistry([{"id":"concept"}]); schemas=ConstitutionalSchemaRegistry([{"id":"constitutional-object","version":"1.0.0","required":[]}])
    large=ConstitutionalRegistry(ROOT,(primitive(i) for i in range(20000)),kinds,schemas,RelationshipTypeRegistry([]))
    results={"bootstrap":measure(lambda:ConstitutionalRegistry.load(ROOT),3),"registry_lookup":measure(lambda:registry.get("system:shard"),1000),"graph_traversal":measure(lambda:registry.find_descendants("reality"),100),"projection":measure(lambda:registry.project("json"),5),"validation":measure(lambda:ConstitutionalValidator(registry).validate(),3),"deep_recursion":measure(lambda:ConstitutionalGraph(deep).ancestors("bench:4999"),3),"large_ontology":measure(lambda:large.by_kind("concept"),10)}
    print(json.dumps(results,indent=2,sort_keys=True))

if __name__ == "__main__": main()
