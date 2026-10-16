from pathlib import Path
from statistics import median
from time import perf_counter
import json,sys
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from runtime.constitution import ConstitutionalPlatform

def measure(fn,repeats=3):
    values=[]
    for _ in range(repeats): start=perf_counter(); fn(); values.append((perf_counter()-start)*1000)
    return {"median_ms":round(median(values),3),"min_ms":round(min(values),3),"samples":repeats}
def main():
    platform=ConstitutionalPlatform.start(ROOT)
    print(json.dumps({"platform_start":measure(lambda:ConstitutionalPlatform.start(ROOT),3),
        "capability_query":measure(lambda:platform.capability("service:voice"),1000),
        "dependency_traversal":measure(lambda:platform.traverse_dependencies("service:voice"),100),
        "health_projection":measure(lambda:platform.health("service:voice"),1000),
        "projection":measure(lambda:platform.project("json","service:voice"),3)},indent=2,sort_keys=True))
if __name__=="__main__": main()
