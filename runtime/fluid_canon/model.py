from __future__ import annotations

from typing import Any,Iterable,Mapping

from runtime.constitution.object import ConstitutionalObject

ASSERTION_TYPES=("Fact","Observation","Inference","Hypothesis","Constraint","Doctrine","Rule","Exception",
                 "Decision","Supersession","Evidence","Source","Conflict","Resolution")

class FluidAssertion:
    """Factory only: the resulting authority is an ordinary ConstitutionalObject."""
    @staticmethod
    def create(*,identity: str,assertion_type: str,subject: str,claim: Any,asserted_by: str,
               source: str,occurred_at: str,version: str="1.0.0",status: str="active",
               supersedes: Iterable[str]=(),evidence: Iterable[str]=(),conflicts: Iterable[str]=(),
               resolves: Iterable[str]=(),dependencies: Iterable[str]=(),metadata: Mapping[str,Any]|None=None) -> ConstitutionalObject:
        if assertion_type not in ASSERTION_TYPES: raise ValueError(f"unknown Fluid Canon assertion type: {assertion_type}")
        if not all(isinstance(v,str) and v.strip() for v in (identity,subject,asserted_by,source,occurred_at)):
            raise ValueError("identity, subject, asserter, source, and timestamp are required")
        relationships=[]
        relationships.extend({"type":"derived_from","target":target,"role":"evidence"} for target in sorted(set(evidence)))
        relationships.extend({"type":"references","target":target,"role":"conflict"} for target in sorted(set(conflicts)))
        relationships.extend({"type":"references","target":target,"role":"resolves"} for target in sorted(set(resolves)))
        return ConstitutionalObject.from_mapping({
            "id":identity,"kind":"concept","canonical_name":identity,"display_name":identity,
            "description":f"{assertion_type} about {subject}.","authority":{},"status":status,"version":version,
            "created_at":occurred_at,"updated_at":occurred_at,
            "lineage":{"parent":"domain:concept","supersedes":sorted(set(supersedes)),"superseded_by":[]},
            "provenance":{"asserted_by":asserted_by,"sources":[source],"method":"fluid-canon-assertion"},
            "relationships":relationships,"dependencies":sorted(set(dependencies)),
            "metadata":{"engine":"fluid-canon","assertion_type":assertion_type,"subject":subject,"claim":claim,**dict(metadata or {})},
        })

def service_assertion(timestamp: str="2026-07-21T00:00:00Z") -> ConstitutionalObject:
    return ConstitutionalObject.from_mapping({
        "id":"service:fluid-canon","kind":"service","canonical_name":"fluid-canon","display_name":"Fluid Canon",
        "description":"Constitutional engine deriving evolving canon from immutable assertions.","authority":{},
        "status":"active","version":"1.0.0","created_at":timestamp,"updated_at":timestamp,
        "lineage":{"parent":"domain:services","supersedes":[],"superseded_by":[]},
        "provenance":{"asserted_by":"constitution","sources":["runtime/fluid_canon"],"method":"constitutional-extension"},
        "relationships":[],"dependencies":["service:authority"],
        "metadata":{"engine":"fluid-canon","implementation_refs":["runtime/fluid_canon"],"projection_targets":["runtime","documentation","json","graph","visualization"]},
    })
