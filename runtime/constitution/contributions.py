from __future__ import annotations

from dataclasses import dataclass
from typing import Any,Iterable,Mapping

from .object import ConstitutionalObject


@dataclass(frozen=True)
class AssertionContribution:
    engine: str
    assertions: tuple[ConstitutionalObject,...]
    registry: Any


class ConstitutionalAssertionAPI:
    """Future engines contribute assertions and receive a new projected registry snapshot."""
    def __init__(self,registry: Any): self.registry=registry
    def contribute(self,engine: str,assertions: Iterable[ConstitutionalObject|Mapping[str,Any]]):
        if not isinstance(engine,str) or not engine.strip(): raise ValueError("engine identity is required")
        raw=tuple(assertions)
        if any(not isinstance(v,(ConstitutionalObject,Mapping)) for v in raw):
            raise TypeError("extensions may contribute constitutional assertion mappings only")
        values=tuple(v if isinstance(v,ConstitutionalObject) else ConstitutionalObject.from_mapping(v) for v in raw)
        if not values: raise ValueError("at least one constitutional assertion is required")
        if len({v.id for v in values})!=len(values): raise ValueError("duplicate contributed identity")
        registry=type(self.registry)(self.registry.root,(*self.registry.values(),*values),self.registry.kinds,self.registry.schemas,self.registry.relationship_types)
        return AssertionContribution(engine,values,registry)
    def reject_runtime_mutation(self,*_args,**_kwargs):
        raise TypeError("engines may contribute constitutional assertions only")
