from pathlib import Path
from statistics import median
from time import perf_counter
import json, sys

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from runtime.constitution import ConstitutionalRegistry, RuntimeMigrationValidator, bootstrap, discover_runtime

def measure(fn,repeats=5):
    samples=[]
    for _ in range(repeats): start=perf_counter(); fn(); samples.append((perf_counter()-start)*1000)
    return {"median_ms":round(median(samples),3),"min_ms":round(min(samples),3),"samples":repeats}

def main():
    authority=ConstitutionalRegistry.load(ROOT); migrated=ConstitutionalRegistry.load_migrated(ROOT); boot=bootstrap(ROOT)
    result={"bootstrap":measure(lambda:bootstrap(ROOT),3),"migration":measure(lambda:ConstitutionalRegistry.load_migrated(ROOT),3),
            "discovery":measure(lambda:discover_runtime(ROOT,authority.values()),5),"registry_lookup":measure(lambda:migrated.get("runtime:module:runtime.kinship.graph"),1000),
            "graph_traversal":measure(lambda:migrated.find_descendants("domain:instances"),100),"projection":measure(lambda:migrated.project("json"),3),
            "validation":measure(lambda:RuntimeMigrationValidator(boot.registry,boot.runtime_migration).validate(),3)}
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__ == "__main__": main()
