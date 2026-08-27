from __future__ import annotations

from typing import Any,Iterable,Mapping

from runtime.constitution import ConstitutionalObject
from runtime.fluid_canon import FluidAssertion

CANONICAL_MEMORY_TYPES=("episodic","semantic","procedural","reference","conversation")
MEMORY_TYPES=(*CANONICAL_MEMORY_TYPES,"working")
_ASSERTION_TYPE={"episodic":"Observation","semantic":"Fact","procedural":"Rule","reference":"Source","conversation":"Observation"}

class MemoryAssertion:
    """Factory for canonical memory assertions; working memory is never accepted here."""
    @staticmethod
    def create(*,identity: str,memory_type: str,subject: str,content: Any,asserted_by: str,source: str,
               occurred_at: str,confidence: float=1.0,valid_from: str|None=None,valid_until: str|None=None,
               version: str="1.0.0",supersedes: Iterable[str]=(),evidence: Iterable[str]=(),
               dependencies: Iterable[str]=(),relationships: Iterable[Mapping[str,Any]]=(),
               kindred: Iterable[str]=(),metadata: Mapping[str,Any]|None=None) -> ConstitutionalObject:
        if memory_type not in CANONICAL_MEMORY_TYPES: raise ValueError("working memory is transient; canonical type required")
        if not 0.0<=float(confidence)<=1.0: raise ValueError("memory confidence must be between 0 and 1")
        if valid_from and valid_until and valid_from>valid_until: raise ValueError("memory validity interval is inverted")
        result=FluidAssertion.create(identity=identity,assertion_type=_ASSERTION_TYPE[memory_type],subject=subject,claim=content,
            asserted_by=asserted_by,source=source,occurred_at=occurred_at,version=version,supersedes=supersedes,
            evidence=evidence,dependencies=dependencies,metadata={"memory_type":memory_type,
            "memory_validity":{"from":valid_from or occurred_at,"until":valid_until},"memory_confidence":float(confidence),
            "kindred":sorted({str(v) for v in kindred}),**dict(metadata or {})})
        if relationships:
            primitive=result.to_primitives(); primitive["relationships"].extend(dict(r) for r in relationships)
            result=ConstitutionalObject.from_mapping(primitive)
        return result

def service_assertion(timestamp: str="2026-07-21T00:00:00Z") -> ConstitutionalObject:
    return ConstitutionalObject.from_mapping({
        "id":"service:memory","kind":"service","canonical_name":"memory","display_name":"Memory",
        "description":"Constitutional projections of canon, relationships, lineage, and events.","authority":{},
        "status":"active","version":"1.0.0","created_at":timestamp,"updated_at":timestamp,
        "lineage":{"parent":"domain:services","supersedes":[],"superseded_by":[]},
        "provenance":{"asserted_by":"constitution","sources":["runtime/memory"],"method":"constitutional-extension"},
        "relationships":[],"dependencies":["service:fluid-canon"],
        "metadata":{"engine":"memory","implementation_refs":["runtime/memory"],"projection_targets":["runtime","documentation","json","graph","visualization"]},
    })
